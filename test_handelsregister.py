import pytest
from handelsregister import get_companies_in_searchresults,HandelsRegister,parse_si_detail
import argparse

def test_parse_search_result():
    html = '<html><body>%s</body></html>' % """<table role="grid"><thead></thead><tbody id="ergebnissForm:selectedSuchErgebnisFormTable_data" class="ui-datatable-data ui-widget-content"><tr data-ri="0" class="ui-widget-content ui-datatable-even" role="row"><td role="gridcell" colspan="9" class="borderBottom3"><table id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt147" class="ui-panelgrid ui-widget" role="grid"><tbody><tr class="ui-widget-content ui-panelgrid-even borderBottom1" role="row"><td role="gridcell" class="ui-panelgrid-cell fontTableNameSize" colspan="5">Berlin  <span class="fontWeightBold"> District court Berlin (Charlottenburg) HRB 44343  </span></td></tr><tr class="ui-widget-content ui-panelgrid-odd" role="row"><td role="gridcell" class="ui-panelgrid-cell paddingBottom20Px" colspan="5"><span class="marginLeft20">GASAG AG</span></td><td role="gridcell" class="ui-panelgrid-cell sitzSuchErgebnisse"><span class="verticalText ">Berlin</span></td><td role="gridcell" class="ui-panelgrid-cell" style="text-align: center;padding-bottom: 20px;"><span class="verticalText">currently registered</span></td><td role="gridcell" class="ui-panelgrid-cell textAlignLeft paddingBottom20Px" colspan="2"><div id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt160" class="ui-outputpanel ui-widget linksPanel"><script type="text/javascript" src="/rp_web/javax.faces.resource/jsf.js.xhtml?ln=javax.faces"></script><a id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:0:fade" href="#" class="dokumentList" aria-describedby="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:0:toolTipFade"><span id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:0:popupLink" class="underlinedText">AD</span></a><a id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:1:fade" href="#" class="dokumentList" aria-describedby="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:1:toolTipFade"><span id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:1:popupLink" class="underlinedText">CD</span></a><a id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:2:fade" href="#" class="dokumentList" aria-describedby="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:2:toolTipFade"><span id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:2:popupLink" class="underlinedText">HD</span></a><a id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:3:fade" href="#" class="dokumentList" aria-describedby="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:3:toolTipFade"><span id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:3:popupLink" class="underlinedText">DK</span></a><a id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:4:fade" href="#" class="dokumentList" aria-describedby="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:4:toolTipFade"><span id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:4:popupLink" class="underlinedText">UT</span></a><a id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:5:fade" href="#" class="dokumentList" aria-describedby="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:5:toolTipFade"><span id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:5:popupLink" class="underlinedText">VÖ</span></a><a id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:6:fade" href="#" class="dokumentList" aria-describedby="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:6:toolTipFade"><span id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt161:6:popupLink" class="underlinedText">SI</span></a></div></td></tr><tr class="ui-widget-content ui-panelgrid-even" role="row"><td role="gridcell" class="ui-panelgrid-cell" colspan="7"><table id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt172" class="ui-panelgrid ui-widget marginLeft20" role="grid"><tbody><tr class="ui-widget-content ui-panelgrid-even borderBottom1 RegPortErg_Klein" role="row"><td role="gridcell" class="ui-panelgrid-cell padding0Px">History</td></tr></tbody></table><table id="ergebnissForm:selectedSuchErgebnisFormTable:0:j_idt176" class="ui-panelgrid ui-widget" role="grid"><tbody><tr class="ui-widget-content" role="row"><td role="gridcell" class="ui-panelgrid-cell RegPortErg_HistorieZn marginLeft20 padding0Px" colspan="5"><span class="marginLeft20 fontSize85">1.) Gasag Berliner Gaswerke Aktiengesellschaft</span></td><td role="gridcell" class="ui-panelgrid-cell RegPortErg_SitzStatus "><span class="fontSize85">1.) Berlin</span></td><td role="gridcell" class="ui-panelgrid-cell textAlignCenter"></td></tr></tbody></table></td></tr></tbody></table></td></tr></tbody></table>"""
    res = get_companies_in_searchresults(html)
    assert res == [{
            'court':'Berlin   District court Berlin (Charlottenburg) HRB 44343',
            'register_num': 'HRB 44343 B',
            'name':'GASAG AG',
            'state':'Berlin',
            'status':'currently registered',  # Original value for backward compatibility
            'statusCurrent':'CURRENTLY_REGISTERED',  # Transformed value
            'documents': 'ADCDHDDKUTVÖSI',
            'history':[('1.) Gasag Berliner Gaswerke Aktiengesellschaft', '1.) Berlin')]
            },]


def test_parse_si_detail():
    """Test parsing of SI (Strukturierter Registerinhalt) XJustiz XML."""
    si_xml = """<?xml version="1.0"?><tns:nachricht.reg.0400003 xmlns:tns="http://www.xjustiz.de" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><tns:nachrichtenkopf xjustizVersion="3.5.1"><tns:aktenzeichen.absender/><tns:aktenzeichen.empfaenger>unbekannt</tns:aktenzeichen.empfaenger><tns:erstellungszeitpunkt>2026-02-25T11:21:36Z</tns:erstellungszeitpunkt><tns:auswahl_absender><tns:absender.gericht listVersionID="3.5" listURI="urn:xoev-de:xjustiz:codeliste:gds.gerichte"><!--Amtsgericht Leipzig--><code>U1308</code></tns:absender.gericht></tns:auswahl_absender><tns:auswahl_empfaenger><tns:empfaenger.sonstige/></tns:auswahl_empfaenger><tns:eigeneNachrichtenID>test-id</tns:eigeneNachrichtenID><tns:ereignis listVersionID="1.5" listURI="urn:xoev-de:xjustiz:codeliste:gds.ereignis"><!--HR-Auszug--><code>002</code></tns:ereignis><tns:herstellerinformation><tns:nameDesProdukts>RegisSTAR</tns:nameDesProdukts><tns:herstellerDesProdukts>Test</tns:herstellerDesProdukts><tns:version>1.0</tns:version></tns:herstellerinformation></tns:nachrichtenkopf><tns:grunddaten><tns:verfahrensdaten><tns:instanzdaten><tns:instanznummer>0</tns:instanznummer><tns:auswahl_instanzbehoerde><tns:gericht listVersionID="3.5" listURI="urn:xoev-de:xjustiz:codeliste:gds.gerichte"><!--Amtsgericht Leipzig--><code>U1308</code></tns:gericht></tns:auswahl_instanzbehoerde><tns:aktenzeichen><tns:auswahl_aktenzeichen><tns:aktenzeichen.strukturiert><tns:register listVersionID="3.4" listURI="urn:xoev-de:xjustiz:codeliste:gds.registerzeichen"><!--HRB--><code>HRB</code></tns:register><tns:laufendeNummer>32007</tns:laufendeNummer><tns:jahr/></tns:aktenzeichen.strukturiert></tns:auswahl_aktenzeichen></tns:aktenzeichen><tns:verfahrensgegenstand><tns:gegenstand>Strukturierter Registerinhalt</tns:gegenstand></tns:verfahrensgegenstand></tns:instanzdaten><tns:beteiligung><tns:rolle><tns:rollennummer>1</tns:rollennummer><tns:rollenID><tns:id>145365283</tns:id><tns:ref.instanznummer>0</tns:ref.instanznummer></tns:rollenID><tns:rollenbezeichnung listVersionID="3.3" listURI="urn:xoev-de:xjustiz:codeliste:gds.rollenbezeichnung"><!--Rechtsträger(in)--><code>287</code></tns:rollenbezeichnung></tns:rolle><tns:beteiligter><tns:beteiligtennummer>1</tns:beteiligtennummer><tns:auswahl_beteiligter><tns:organisation><tns:bezeichnung><tns:bezeichnung.aktuell>Test Company GmbH</tns:bezeichnung.aktuell></tns:bezeichnung><tns:angabenZurRechtsform><tns:rechtsform listVersionID="2.2" listURI="urn:xoev-de:xunternehmen:codeliste:rechtsformen"><!--Gesellschaft mit beschränkter Haftung (GmbH)--><code>221110</code></tns:rechtsform></tns:angabenZurRechtsform><tns:sitz><tns:ort>Leipzig</tns:ort></tns:sitz><tns:anschrift><tns:anschriftstyp listVersionID="3.0" listURI="urn:xoev-de:xjustiz:codeliste:gds.anschriftstyp"><!--Dienst-/Geschäftsanschrift--><code>003</code></tns:anschriftstyp><tns:strasse>Teststraße</tns:strasse><tns:hausnummer>42</tns:hausnummer><tns:postleitzahl>04109</tns:postleitzahl><tns:ort>Leipzig</tns:ort><tns:staat listVersionID="6.1" listURI="urn:xoev-de:bund:bfj:codeliste:bfj.staat"><!--Deutschland--><code>000</code></tns:staat></tns:anschrift></tns:organisation></tns:auswahl_beteiligter></tns:beteiligter></tns:beteiligung><tns:beteiligung><tns:rolle><tns:rollennummer>4</tns:rollennummer><tns:rollenID><tns:id>145332515</tns:id><tns:ref.instanznummer>0</tns:ref.instanznummer></tns:rollenID><tns:rollenbezeichnung listVersionID="3.3" listURI="urn:xoev-de:xjustiz:codeliste:gds.rollenbezeichnung"><!--Geschäftsführer(in)--><code>086</code></tns:rollenbezeichnung></tns:rolle><tns:beteiligter><tns:beteiligtennummer>4</tns:beteiligtennummer><tns:auswahl_beteiligter><tns:natuerlichePerson><tns:vollerName><tns:vorname>Max</tns:vorname><tns:nachname>Mustermann</tns:nachname></tns:vollerName><tns:geburt><tns:geburtsdatum>1984-06-25</tns:geburtsdatum></tns:geburt><tns:anschrift><tns:anschriftstyp listVersionID="3.0" listURI="urn:xoev-de:xjustiz:codeliste:gds.anschriftstyp"><!--Privatanschrift--><code>017</code></tns:anschriftstyp><tns:ort>Leipzig</tns:ort></tns:anschrift></tns:natuerlichePerson></tns:auswahl_beteiligter></tns:beteiligter></tns:beteiligung><tns:beteiligung><tns:rolle><tns:rollennummer>5</tns:rollennummer><tns:rollenID><tns:id>145435568</tns:id><tns:ref.instanznummer>0</tns:ref.instanznummer></tns:rollenID><tns:rollenbezeichnung listVersionID="3.3" listURI="urn:xoev-de:xjustiz:codeliste:gds.rollenbezeichnung"><!--Prokurist(in)--><code>285</code></tns:rollenbezeichnung></tns:rolle><tns:beteiligter><tns:beteiligtennummer>5</tns:beteiligtennummer><tns:auswahl_beteiligter><tns:natuerlichePerson><tns:vollerName><tns:vorname>Erika</tns:vorname><tns:nachname>Musterfrau</tns:nachname></tns:vollerName><tns:geburt><tns:geburtsdatum>1990-01-15</tns:geburtsdatum></tns:geburt><tns:anschrift><tns:anschriftstyp listVersionID="3.0" listURI="urn:xoev-de:xjustiz:codeliste:gds.anschriftstyp"><!--Privatanschrift--><code>017</code></tns:anschriftstyp><tns:ort>Berlin</tns:ort></tns:anschrift></tns:natuerlichePerson></tns:auswahl_beteiligter></tns:beteiligter></tns:beteiligung></tns:verfahrensdaten></tns:grunddaten><tns:schriftgutobjekte/><tns:fachdatenRegister fachdatenRegisterVersion="3.4"><tns:mitteilungsart listVersionID="1.5" listURI="urn:xoev-de:xjustiz:codeliste:gds.ereignis"><!--HR-Auszug--><code>002</code></tns:mitteilungsart><tns:betroffenerRechtstraeger><tns:ref.rollennummer>1</tns:ref.rollennummer></tns:betroffenerRechtstraeger><tns:auszug><tns:eintragungstext><tns:spalte>6</tns:spalte><tns:position>1</tns:position><tns:laufendeNummer>2</tns:laufendeNummer><tns:eintragungsart listVersionID="1.1" listURI="urn:xoev-de:xjustiz:codeliste:reg.eintragungstyp"><!--Satzung--><code>009</code></tns:eintragungsart><tns:text>Gesellschaftsvertrag vom 18.06.2015.</tns:text></tns:eintragungstext><tns:abrufuhrzeit>11:21:36</tns:abrufuhrzeit><tns:abrufdatum>2026-02-25</tns:abrufdatum><tns:letzteEintragung>2025-06-02</tns:letzteEintragung><tns:anzahlEintragungen>7</tns:anzahlEintragungen><tns:letzteAenderung><tns:aenderungsdatum>2025-05-22</tns:aenderungsdatum></tns:letzteAenderung></tns:auszug><tns:basisdatenRegister><tns:satzungsdatum><tns:aktuellesSatzungsdatum>2015-06-18</tns:aktuellesSatzungsdatum></tns:satzungsdatum><tns:rechtstraeger><tns:bezeichnung><tns:bezeichnung.aktuell>Test Company GmbH</tns:bezeichnung.aktuell></tns:bezeichnung><tns:angabenZurRechtsform><tns:rechtsform listVersionID="2.2" listURI="urn:xoev-de:xunternehmen:codeliste:rechtsformen"><!--Gesellschaft mit beschränkter Haftung (GmbH)--><code>221110</code></tns:rechtsform></tns:angabenZurRechtsform><tns:sitz><tns:ort>Leipzig</tns:ort></tns:sitz><tns:anschrift><tns:anschriftstyp listVersionID="3.0" listURI="urn:xoev-de:xjustiz:codeliste:gds.anschriftstyp"><!--Dienst-/Geschäftsanschrift--><code>003</code></tns:anschriftstyp><tns:strasse>Teststraße</tns:strasse><tns:hausnummer>42</tns:hausnummer><tns:postleitzahl>04109</tns:postleitzahl><tns:ort>Leipzig</tns:ort><tns:staat listVersionID="6.1" listURI="urn:xoev-de:bund:bfj:codeliste:bfj.staat"><!--Deutschland--><code>000</code></tns:staat></tns:anschrift></tns:rechtstraeger><tns:vertretung><tns:allgemeineVertretungsregelung><tns:auswahl_vertretungsbefugnis><tns:vertretungsbefugnis listVersionID="2.3" listURI="urn:xoev-de:xjustiz:codeliste:reg.allgemeine-vertretungsregelung"><!--Ist nur ein Geschäftsführer bestellt, so vertritt er die Gesellschaft allein.--><code>066</code></tns:vertretungsbefugnis></tns:auswahl_vertretungsbefugnis></tns:allgemeineVertretungsregelung><tns:vertretungsberechtigte><tns:ref.rollennummer>4</tns:ref.rollennummer><tns:besondereVertretungsregelung><tns:auswahl_vertretungsbefugnis><tns:vertretungsbefugnisFreitext>einzelvertretungsberechtigt;</tns:vertretungsbefugnisFreitext></tns:auswahl_vertretungsbefugnis><tns:auswahl_befreiungVon181BGB><tns:befreiungVon181BGB listVersionID="2.0" listURI="urn:xoev-de:xjustiz:codeliste:reg.besondere-befreiung"><!--mit der Befugnis Rechtsgeschäfte abzuschließen--><code>011</code></tns:befreiungVon181BGB></tns:auswahl_befreiungVon181BGB></tns:besondereVertretungsregelung></tns:vertretungsberechtigte><tns:vertretungsberechtigte><tns:ref.rollennummer>5</tns:ref.rollennummer><tns:besondereVertretungsregelung><tns:auswahl_vertretungsbefugnis><tns:vertretungsbefugnis listVersionID="2.3" listURI="urn:xoev-de:xjustiz:codeliste:reg.besondere-vertretungsregelung"><!--Einzelprokura--><code>002</code></tns:vertretungsbefugnis></tns:auswahl_vertretungsbefugnis></tns:besondereVertretungsregelung></tns:vertretungsberechtigte></tns:vertretung><tns:gegenstand>Softwareentwicklung und IT-Beratung.</tns:gegenstand><tns:geschaeftszweck/></tns:basisdatenRegister><tns:auswahl_zusatzangaben><tns:kapitalgesellschaft><tns:zusatzGmbH><tns:stammkapital><tns:zahl>25000.00</tns:zahl><tns:auswahl_waehrung><tns:waehrung listVersionID="1.0" listURI="urn:xoev-de:bund:kba:codeliste:waehrung"><!--Euro--><code>EUR</code></tns:waehrung></tns:auswahl_waehrung></tns:stammkapital></tns:zusatzGmbH></tns:kapitalgesellschaft></tns:auswahl_zusatzangaben></tns:fachdatenRegister></tns:nachricht.reg.0400003>"""

    detail = parse_si_detail(si_xml)

    # Company info
    assert detail['name'] == 'Test Company GmbH'
    assert 'GmbH' in detail['legal_form']
    assert detail['seat'] == 'Leipzig'

    # Address
    assert detail['address']['street'] == 'Teststraße 42'
    assert detail['address']['postal_code'] == '04109'
    assert detail['address']['city'] == 'Leipzig'

    # Business purpose
    assert 'Softwareentwicklung' in detail['business_purpose']

    # Capital
    assert detail['capital']['amount'] == '25000.00'
    assert detail['capital']['currency'] == 'EUR'

    # Directors
    assert len(detail['directors']) == 1
    assert detail['directors'][0]['name'] == 'Max Mustermann'
    assert detail['directors'][0]['date_of_birth'] == '1984-06-25'

    # Prokura
    assert len(detail['prokura']) == 1
    assert detail['prokura'][0]['name'] == 'Erika Musterfrau'

    # Register info
    assert detail['register_type'] == 'HRB'
    assert detail['register_number'] == '32007'
    assert detail['retrieval_date'] == '2026-02-25'
    assert detail['last_entry_date'] == '2025-06-02'

    # Articles of association
    assert detail['articles_of_association_date'] == '2015-06-18'

    # Register entries
    assert len(detail['register_entries']) >= 1
    assert 'Gesellschaftsvertrag' in detail['register_entries'][0]['text']


def test_fetch_detail():
    """Integration test: search for a known company and fetch its SI data."""
    args = argparse.Namespace(debug=False, force=True, schlagwoerter='Gecko Two GmbH',
                              schlagwortOptionen='exact', json=False, detail=True)
    h = HandelsRegister(args)
    h.open_startpage()
    companies = h.search_company()
    assert companies is not None
    assert len(companies) > 0

    detail = h.fetch_company_detail(result_index=0)
    assert detail is not None

    # Basic fields that should always be present
    assert detail.get('name') is not None
    assert 'Gecko' in detail['name']
    assert detail.get('seat') is not None
    assert detail.get('address') is not None
    assert detail.get('capital') is not None
    assert detail.get('directors') is not None
    assert len(detail['directors']) > 0


@pytest.mark.parametrize("company, state_id", [
    ("Hafen Hamburg", "Hamburg"),
    ("Bayerische Motoren Werke", "Bayern"),
    ("Daimler Truck", "Baden-Württemberg"),
    ("Volkswagen", "Niedersachsen"),
    ("RWE", "Nordrhein-Westfalen"),
    ("Fraport", "Hessen"),
    ("Saarstahl", "Saarland"),
    ("Mainz", "Rheinland-Pfalz"),
    ("Nordex", "Mecklenburg-Vorpommern"),
    ("Jenoptik", "Thüringen"),
    ("Vattenfall", "Berlin"),
    ("Bremen", "Bremen"),
    ("Sachsen", "Sachsen"),
    ("Magdeburg", "Sachsen-Anhalt"),
    ("Kiel", "Schleswig-Holstein"),
    ("Potsdam", "Brandenburg")
])
def test_search_by_state_company(company, state_id):

    args = argparse.Namespace(debug=False, force=True, schlagwoerter=company, schlagwortOptionen='all', json=False, detail=False)
    h = HandelsRegister(args)
    h.open_startpage()
    companies = h.search_company()
    assert companies is not None
    assert len(companies) > 0

def test_haus_anker_b_suffix():
    args = argparse.Namespace(debug=False, force=True, schlagwoerter='Haus-Anker Verwaltungs GmbH', schlagwortOptionen='exact', json=False, detail=False)
    h = HandelsRegister(args)
    h.open_startpage()
    companies = h.search_company()
    assert companies is not None

    target_company = next((c for c in companies if '138434' in c['register_num']), None)

    assert target_company is not None, "Haus-Anker Verwaltungs GmbH with expected number not found"
    assert target_company['register_num'] == 'HRB 138434 B'
