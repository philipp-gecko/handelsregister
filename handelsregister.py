#!/usr/bin/env python3
"""
bundesAPI/handelsregister is the command-line interface for the shared register of companies portal for the German federal states.
You can query, download, automate and much more, without using a web browser.
"""

import argparse
import tempfile
import mechanize
import re
import pathlib
import sys
from bs4 import BeautifulSoup
import urllib.parse
import xml.etree.ElementTree as ET

# Dictionaries to map arguments to values
schlagwortOptionen = {
    "all": 1,
    "min": 2,
    "exact": 3
}

# XJustiz namespace
NS = {'tns': 'http://www.xjustiz.de'}

# Role code to label mapping (from xjustiz codeliste:gds.rollenbezeichnung)
ROLE_CODES = {
    '086': 'Geschäftsführer(in)',
    '087': 'Vorstand',
    '285': 'Prokurist(in)',
    '287': 'Rechtsträger(in)',
    '288': 'Registergericht',
    '215': 'Einreicher(in)',
    '061': 'Gesellschafter(in)',
    '062': 'Kommanditist(in)',
    '063': 'Persönlich haftende(r) Gesellschafter(in)',
    '089': 'Liquidator(in)',
    '297': 'Inhaber(in)',
}

class HandelsRegister:
    def __init__(self, args):
        self.args = args
        self.browser = mechanize.Browser()

        self.browser.set_debug_http(args.debug)
        self.browser.set_debug_responses(args.debug)
        # self.browser.set_debug_redirects(True)

        self.browser.set_handle_robots(False)
        self.browser.set_handle_equiv(True)
        self.browser.set_handle_gzip(True)
        self.browser.set_handle_refresh(False)
        self.browser.set_handle_redirect(True)
        self.browser.set_handle_referer(True)

        self.browser.addheaders = [
            (
                "User-Agent",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15",
            ),
            (   "Accept-Language", "en-GB,en;q=0.9"   ),
            (   "Accept-Encoding", "gzip, deflate, br"    ),
            (
                "Accept",
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            ),
            (   "Connection", "keep-alive"    ),
        ]

        self.cachedir = pathlib.Path(tempfile.gettempdir()) / "handelsregister_cache"
        self.cachedir.mkdir(parents=True, exist_ok=True)

    def open_startpage(self):
        self.browser.open("https://www.handelsregister.de", timeout=10)

    def companyname2cachename(self, companyname):
        return self.cachedir / companyname

    def search_company(self):
        cachename = self.companyname2cachename(self.args.schlagwoerter)
        if self.args.force==False and cachename.exists():
            with open(cachename, "r") as f:
                html = f.read()
                if not self.args.json:
                    print("return cached content for %s" % self.args.schlagwoerter)
        else:
            # TODO implement token bucket to abide by rate limit
            # Use an atomic counter: https://gist.github.com/benhoyt/8c8a8d62debe8e5aa5340373f9c509c7
            self.browser.select_form(name="naviForm")
            self.browser.form.new_control('hidden', 'naviForm:erweiterteSucheLink', {'value': 'naviForm:erweiterteSucheLink'})
            self.browser.form.new_control('hidden', 'target', {'value': 'erweiterteSucheLink'})
            response_search = self.browser.submit()

            if self.args.debug == True:
                print(self.browser.title())

            self.browser.select_form(name="form")

            self.browser["form:schlagwoerter"] = self.args.schlagwoerter
            so_id = schlagwortOptionen.get(self.args.schlagwortOptionen)

            self.browser["form:schlagwortOptionen"] = [str(so_id)]

            response_result = self.browser.submit()

            if self.args.debug == True:
                print(self.browser.title())

            html = response_result.read().decode("utf-8")
            with open(cachename, "w") as f:
                f.write(html)

            # TODO catch the situation if there's more than one company?
            # TODO get all documents attached to the exact company
            # TODO parse useful information out of the PDFs
        self._last_search_html = html
        return get_companies_in_searchresults(html)

    def fetch_company_detail(self, result_index=0):
        """Fetch the SI (Strukturierter Registerinhalt) document for a search result.

        Must be called after search_company(). Uses the cached search HTML to find
        the SI link's PrimeFaces submit params, then submits the form to fetch the
        XML document.

        Returns a dict of parsed company detail fields, or None if SI is unavailable.
        """
        html = self._last_search_html
        soup = BeautifulSoup(html, 'html.parser')

        # Find the SI link for the given result index
        si_link = None
        for a in soup.find_all('a'):
            link_id = a.get('id', '')
            # Match pattern: ergebnissForm:selectedSuchErgebnisFormTable:{index}:...:fade_
            if ':{}:'.format(result_index) in link_id:
                span = a.find('span')
                if span and span.text.strip() == 'SI':
                    si_link = a
                    break

        if not si_link:
            return None

        onclick = si_link.get('onclick', '')
        if not onclick:
            return None

        # Parse PrimeFaces.addSubmitParam params from onclick
        pairs = re.findall(r"'([^']+)':'([^']*)'", onclick)
        if not pairs:
            return None

        # Select the ergebnissForm and inject hidden params
        self.browser.select_form(name='ergebnissForm')
        for key, value in pairs:
            self.browser.form.new_control('hidden', key, {'value': value})
        self.browser.form.fixup()

        response_si = self.browser.submit()
        si_xml = response_si.read().decode('utf-8')

        # Cache the SI XML
        cachename = self.companyname2cachename(self.args.schlagwoerter + '_SI')
        with open(cachename, 'w') as f:
            f.write(si_xml)

        return parse_si_detail(si_xml)


def _build_comment_map(xml_str):
    """Build a map from XML element code values to their preceding comments.

    XJustiz uses XML comments to provide human-readable labels for coded values, e.g.:
      <!--Gesellschaft mit beschränkter Haftung (GmbH)--><code>221110</code>
    ElementTree drops comments during parsing, so we extract them from the raw string.
    """
    comment_map = {}
    for match in re.finditer(r'<!--(.+?)-->\s*<code>([^<]+)</code>', xml_str):
        comment_map[match.group(2)] = match.group(1)
    return comment_map


def parse_si_detail(xml_str):
    """Parse the SI (Strukturierter Registerinhalt) XJustiz XML into a dict.

    The SI document is an XJustiz XML file containing structured register content:
    company name, address, legal form, capital, directors, prokura holders, etc.
    """
    root = ET.fromstring(xml_str)
    comment_map = _build_comment_map(xml_str)
    detail = {}

    # Build a role-number-to-person/org mapping from beteiligung entries
    roles = {}  # rollennummer -> {role_code, role_label, person_data}
    for beteiligung in root.findall('.//tns:beteiligung', NS):
        rolle_elems = beteiligung.findall('tns:rolle', NS)
        beteiligter = beteiligung.find('tns:beteiligter', NS)
        if beteiligter is None:
            continue

        for rolle in rolle_elems:
            rollennummer = _text(rolle, 'tns:rollennummer')
            role_code_elem = rolle.find('tns:rollenbezeichnung', NS)
            role_code = _text(role_code_elem, 'code') if role_code_elem is not None else None
            role_label = ROLE_CODES.get(role_code, comment_map.get(role_code, role_code))

            person_data = _parse_beteiligter(beteiligter, comment_map)
            if rollennummer:
                roles[rollennummer] = {
                    'role_code': role_code,
                    'role_label': role_label,
                    **person_data
                }

    # Company info from the Rechtsträger (role code 287)
    for rnum, rdata in roles.items():
        if rdata.get('role_code') == '287':
            detail['name'] = rdata.get('name')
            detail['legal_form'] = rdata.get('legal_form')
            detail['legal_form_code'] = rdata.get('legal_form_code')
            detail['seat'] = rdata.get('seat')
            if rdata.get('address'):
                detail['address'] = rdata['address']
            break

    # basisdatenRegister
    basisdaten = root.find('.//tns:basisdatenRegister', NS)
    if basisdaten is not None:
        # Satzungsdatum
        satzung = basisdaten.find('.//tns:aktuellesSatzungsdatum', NS)
        if satzung is not None and satzung.text:
            detail['articles_of_association_date'] = satzung.text

        # Gegenstand (business purpose)
        gegenstand = basisdaten.find('.//tns:gegenstand', NS)
        if gegenstand is not None and gegenstand.text:
            detail['business_purpose'] = gegenstand.text.strip()

        # Vertretungsregelung (representation rules)
        allg_vertretung = basisdaten.find('.//tns:allgemeineVertretungsregelung', NS)
        if allg_vertretung is not None:
            vb = allg_vertretung.find('.//tns:vertretungsbefugnis', NS)
            if vb is not None:
                vb_code = _text(vb, 'code')
                if vb_code and vb_code in comment_map:
                    detail['representation_rules'] = comment_map[vb_code]

        # Representatives with their specific rules
        for vb_elem in basisdaten.findall('.//tns:vertretungsberechtigte', NS):
            ref = _text(vb_elem, 'tns:ref.rollennummer')
            if ref and ref in roles:
                rep = roles[ref]
                besondere = vb_elem.find('tns:besondereVertretungsregelung', NS)
                if besondere is not None:
                    freitext = besondere.find('.//tns:vertretungsbefugnisFreitext', NS)
                    if freitext is not None and freitext.text:
                        rep['representation'] = freitext.text.strip().rstrip(';')
                    else:
                        vb_code_elem = besondere.find('.//tns:vertretungsbefugnis', NS)
                        if vb_code_elem is not None:
                            code_val = _text(vb_code_elem, 'code')
                            if code_val and code_val in comment_map:
                                rep['representation'] = comment_map[code_val]

                    befreiung = besondere.find('.//tns:befreiungVon181BGB', NS)
                    if befreiung is not None:
                        rep['exempt_181_bgb'] = True

    # Collect managing directors and prokura holders
    directors = []
    prokura = []
    for rnum, rdata in roles.items():
        if rdata.get('role_code') == '086':  # Geschäftsführer
            directors.append(rdata)
        elif rdata.get('role_code') == '087':  # Vorstand
            directors.append(rdata)
        elif rdata.get('role_code') == '285':  # Prokurist
            prokura.append(rdata)

    if directors:
        detail['directors'] = directors
    if prokura:
        detail['prokura'] = prokura

    # Capital (Stammkapital / Grundkapital)
    stammkapital = root.find('.//tns:stammkapital', NS)
    if stammkapital is None:
        stammkapital = root.find('.//tns:grundkapital', NS)
    if stammkapital is not None:
        zahl = _text(stammkapital, 'tns:zahl')
        waehrung_elem = stammkapital.find('.//tns:waehrung', NS)
        waehrung_code = _text(waehrung_elem, 'code') if waehrung_elem is not None else None
        if zahl:
            detail['capital'] = {
                'amount': zahl,
                'currency': waehrung_code or 'EUR'
            }

    # Register info
    aktenzeichen = root.find('.//tns:aktenzeichen.strukturiert', NS)
    if aktenzeichen is not None:
        register = aktenzeichen.find('tns:register', NS)
        nummer = _text(aktenzeichen, 'tns:laufendeNummer')
        if register is not None and nummer:
            reg_code = _text(register, 'code')
            detail['register_type'] = reg_code
            detail['register_number'] = nummer

    # Auszug metadata
    auszug = root.find('.//tns:auszug', NS)
    if auszug is not None:
        detail['retrieval_date'] = _text(auszug, 'tns:abrufdatum')
        detail['last_entry_date'] = _text(auszug, 'tns:letzteEintragung')
        detail['num_entries'] = _text(auszug, 'tns:anzahlEintragungen')

    # Eintragungstexte (register entry texts)
    entries = []
    for et_elem in root.findall('.//tns:eintragungstext', NS):
        entry = {}
        entry['column'] = _text(et_elem, 'tns:spalte')
        entry['position'] = _text(et_elem, 'tns:position')
        entry['number'] = _text(et_elem, 'tns:laufendeNummer')
        entry['text'] = _text(et_elem, 'tns:text')
        art_elem = et_elem.find('tns:eintragungsart', NS)
        if art_elem is not None:
            art_code = _text(art_elem, 'code')
            if art_code and art_code in comment_map:
                entry['type'] = comment_map[art_code]
        entries.append(entry)
    if entries:
        detail['register_entries'] = entries

    return detail


def _text(parent, path):
    """Extract text from an XML element, or None."""
    if parent is None:
        return None
    elem = parent.find(path, NS)
    if elem is not None and elem.text:
        return elem.text.strip()
    return None


def _parse_beteiligter(beteiligter, comment_map):
    """Parse a beteiligter element into a person/org dict."""
    data = {}

    # Natural person
    person = beteiligter.find('.//tns:natuerlichePerson', NS)
    if person is not None:
        vorname = _text(person, './/tns:vorname')
        nachname = _text(person, './/tns:nachname')
        if vorname and nachname:
            data['name'] = '%s %s' % (vorname, nachname)
        elif nachname:
            data['name'] = nachname

        geburtsdatum = _text(person, './/tns:geburtsdatum')
        if geburtsdatum:
            data['date_of_birth'] = geburtsdatum

        anschrift = person.find('tns:anschrift', NS)
        if anschrift is not None:
            data['city'] = _text(anschrift, 'tns:ort')

        return data

    # Organisation
    org = beteiligter.find('.//tns:organisation', NS)
    if org is not None:
        data['name'] = _text(org, './/tns:bezeichnung.aktuell')

        rechtsform = org.find('.//tns:rechtsform', NS)
        if rechtsform is not None:
            rf_code = _text(rechtsform, 'code')
            if rf_code:
                data['legal_form'] = comment_map.get(rf_code, rf_code)
                data['legal_form_code'] = rf_code

        sitz = org.find('tns:sitz', NS)
        if sitz is not None:
            data['seat'] = _text(sitz, 'tns:ort')

        anschrift = org.find('tns:anschrift', NS)
        if anschrift is not None:
            addr = {}
            street = _text(anschrift, 'tns:strasse')
            hausnummer = _text(anschrift, 'tns:hausnummer')
            if street:
                addr['street'] = street + (' ' + hausnummer if hausnummer else '')
            plz = _text(anschrift, 'tns:postleitzahl')
            if plz:
                addr['postal_code'] = plz
            ort = _text(anschrift, 'tns:ort')
            if ort:
                addr['city'] = ort
            if addr:
                data['address'] = addr

    return data


def parse_result(result):
    cells = []
    for cellnum, cell in enumerate(result.find_all('td')):
        cells.append(cell.text.strip())
    d = {}
    d['court'] = cells[1]

    # Extract register number: HRB, HRA, VR, GnR followed by numbers (e.g. HRB 12345, VR 6789)
    # Also capture suffix letter if present (e.g. HRB 12345 B), but avoid matching start of words (e.g. " Formerly")
    reg_match = re.search(r'(HRA|HRB|GnR|VR|PR)\s*\d+(\s+[A-Z])?(?!\w)', d['court'])
    d['register_num'] = reg_match.group(0) if reg_match else None

    d['name'] = cells[2]
    d['state'] = cells[3]
    d['status'] = cells[4].strip()  # Original value for backward compatibility
    d['statusCurrent'] = cells[4].strip().upper().replace(' ', '_')  # Transformed value

    # Ensure consistent register number suffixes (e.g. ' B' for Berlin HRB, ' HB' for Bremen) which might be implicit
    if d['register_num']:
        suffix_map = {
            'Berlin': {'HRB': ' B'},
            'Bremen': {'HRA': ' HB', 'HRB': ' HB', 'GnR': ' HB', 'VR': ' HB', 'PR': ' HB'}
        }
        reg_type = d['register_num'].split()[0]
        suffix = suffix_map.get(d['state'], {}).get(reg_type)
        if suffix and not d['register_num'].endswith(suffix):
            d['register_num'] += suffix
    d['documents'] = cells[5] # todo: get the document links
    d['history'] = []
    hist_start = 8

    for i in range(hist_start, len(cells), 3):
        if i + 1 >= len(cells):
            break
        if "Branches" in cells[i] or "Niederlassungen" in cells[i]:
            break
        d['history'].append((cells[i], cells[i+1])) # (name, location)

    return d

def pr_company_info(c):
    for tag in ('name', 'court', 'register_num', 'district', 'state', 'statusCurrent'):
        print('%s: %s' % (tag, c.get(tag, '-')))
    print('history:')
    for name, loc in c.get('history'):
        print(name, loc)

def pr_company_detail(detail):
    """Print the SI detail fields in human-readable format."""
    if not detail:
        print('  (no detail data available)')
        return

    print()
    print('--- Detail (SI) ---')
    for key in ('name', 'legal_form', 'seat', 'business_purpose',
                'articles_of_association_date', 'representation_rules'):
        if key in detail:
            label = key.replace('_', ' ').title()
            print('%s: %s' % (label, detail[key]))

    if 'address' in detail:
        addr = detail['address']
        parts = []
        if 'street' in addr:
            parts.append(addr['street'])
        if 'postal_code' in addr and 'city' in addr:
            parts.append('%s %s' % (addr['postal_code'], addr['city']))
        elif 'city' in addr:
            parts.append(addr['city'])
        print('Address: %s' % ', '.join(parts))

    if 'capital' in detail:
        cap = detail['capital']
        print('Capital: %s %s' % (cap['amount'], cap['currency']))

    if 'directors' in detail:
        print('Directors:')
        for d in detail['directors']:
            extra = ''
            if d.get('representation'):
                extra = ' (%s)' % d['representation']
            print('  %s%s' % (d.get('name', '?'), extra))

    if 'prokura' in detail:
        print('Prokura:')
        for p in detail['prokura']:
            extra = ''
            if p.get('representation'):
                extra = ' (%s)' % p['representation']
            print('  %s%s' % (p.get('name', '?'), extra))

    if 'register_entries' in detail:
        print('Register Entries:')
        for entry in detail['register_entries']:
            etype = entry.get('type', '')
            text = entry.get('text', '')
            print('  [%s] %s' % (etype, text))

    print('Last Entry: %s' % detail.get('last_entry_date', '-'))
    print('Retrieval Date: %s' % detail.get('retrieval_date', '-'))

def get_companies_in_searchresults(html):
    soup = BeautifulSoup(html, 'html.parser')
    grid = soup.find('table', role='grid')

    results = []
    for result in grid.find_all('tr'):
        a = result.get('data-ri')
        if a is not None:
            index = int(a)

            d = parse_result(result)
            results.append(d)
    return results

def parse_args():
    parser = argparse.ArgumentParser(description='A handelsregister CLI')
    parser.add_argument(
                          "-d",
                          "--debug",
                          help="Enable debug mode and activate logging",
                          action="store_true"
                        )
    parser.add_argument(
                          "-f",
                          "--force",
                          help="Force a fresh pull and skip the cache",
                          action="store_true"
                        )
    parser.add_argument(
                          "-s",
                          "--schlagwoerter",
                          help="Search for the provided keywords",
                          required=True,
                          default="Gasag AG" # TODO replace default with a generic search term
                        )
    parser.add_argument(
                          "-so",
                          "--schlagwortOptionen",
                          help="Keyword options: all=contain all keywords; min=contain at least one keyword; exact=contain the exact company name.",
                          choices=["all", "min", "exact"],
                          default="all"
                        )
    parser.add_argument(
                          "-j",
                          "--json",
                          help="Return response as JSON",
                          action="store_true"
                        )
    parser.add_argument(
                          "-det",
                          "--detail",
                          help="Fetch SI (structured register content) detail for the first search result",
                          action="store_true"
                        )
    args = parser.parse_args()


    # Enable debugging if wanted
    if args.debug == True:
        import logging
        logger = logging.getLogger("mechanize")
        logger.addHandler(logging.StreamHandler(sys.stdout))
        logger.setLevel(logging.DEBUG)

    return args

if __name__ == "__main__":
    import json
    args = parse_args()
    h = HandelsRegister(args)
    h.open_startpage()
    companies = h.search_company()
    if companies is not None:
        detail = None
        if args.detail and len(companies) > 0:
            detail = h.fetch_company_detail(result_index=0)

        if args.json:
            output = companies
            if detail:
                output[0]['detail'] = detail
            print(json.dumps(output))
        else:
            for c in companies:
                pr_company_info(c)
            if detail:
                pr_company_detail(detail)
