#!/usr/bin/env python3
"""Minimal web UI for the Handelsregister CLI. No extra dependencies — uses stdlib only."""

import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from handelsregister import HandelsRegister, parse_si_detail

PORT = 8000

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Handelsregister Search</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: #f5f5f5; color: #222; padding: 2rem; max-width: 900px; margin: 0 auto; }
  h1 { margin-bottom: 1.5rem; font-size: 1.4rem; }
  form { background: #fff; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1);
         display: flex; flex-wrap: wrap; gap: 1rem; align-items: end; margin-bottom: 2rem; }
  label { display: flex; flex-direction: column; gap: .3rem; font-size: .85rem; font-weight: 600; }
  input[type=text] { padding: .5rem .7rem; border: 1px solid #ccc; border-radius: 4px; font-size: .95rem; width: 280px; }
  select { padding: .5rem; border: 1px solid #ccc; border-radius: 4px; font-size: .95rem; }
  button { padding: .55rem 1.2rem; background: #0066cc; color: #fff; border: none; border-radius: 4px;
           font-size: .95rem; cursor: pointer; }
  button:hover { background: #0052a3; }
  button:disabled { background: #999; cursor: wait; }
  .cb { display: flex; align-items: center; gap: .4rem; font-weight: 600; font-size: .85rem; }
  .cb input { width: auto; }
  #status { font-size: .85rem; color: #666; margin-bottom: 1rem; min-height: 1.2em; }
  #results { display: flex; flex-direction: column; gap: 1.5rem; }
  .card { background: #fff; padding: 1.2rem 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  .card h2 { font-size: 1.1rem; margin-bottom: .6rem; color: #0066cc; }
  .field { margin-bottom: .35rem; font-size: .9rem; }
  .field b { display: inline-block; min-width: 160px; color: #555; }
  .section { margin-top: .8rem; padding-top: .6rem; border-top: 1px solid #eee; }
  .section h3 { font-size: .95rem; margin-bottom: .4rem; color: #333; }
  .person { margin-left: 1rem; margin-bottom: .2rem; font-size: .9rem; }
  .entry { margin-left: 1rem; margin-bottom: .3rem; font-size: .85rem; color: #444; }
  .entry-type { font-weight: 600; color: #666; }
  .error { color: #c00; font-weight: 600; }
</style>
</head>
<body>
<h1>Handelsregister Search</h1>
<form id="searchForm">
  <label>Company name
    <input type="text" name="q" placeholder="e.g. Gecko Two GmbH" required>
  </label>
  <label>Match
    <select name="so">
      <option value="all">All keywords</option>
      <option value="min">At least one</option>
      <option value="exact" selected>Exact name</option>
    </select>
  </label>
  <label class="cb"><input type="checkbox" name="detail" checked> Fetch detail (SI)</label>
  <button type="submit" id="btn">Search</button>
</form>
<div id="status"></div>
<div id="results"></div>

<script>
const form = document.getElementById('searchForm');
const btn = document.getElementById('btn');
const status = document.getElementById('status');
const results = document.getElementById('results');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fd = new FormData(form);
  const params = new URLSearchParams();
  params.set('q', fd.get('q'));
  params.set('so', fd.get('so'));
  params.set('detail', fd.has('detail') ? '1' : '0');

  btn.disabled = true;
  status.textContent = 'Searching...';
  results.innerHTML = '';

  try {
    const resp = await fetch('/api/search?' + params.toString());
    const data = await resp.json();
    if (data.error) { status.innerHTML = '<span class="error">' + esc(data.error) + '</span>'; return; }
    status.textContent = data.companies.length + ' result(s)';
    results.innerHTML = data.companies.map(renderCompany).join('');
  } catch (err) {
    status.innerHTML = '<span class="error">Request failed: ' + esc(err.message) + '</span>';
  } finally {
    btn.disabled = false;
  }
});

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function renderCompany(c) {
  let html = '<div class="card">';
  html += '<h2>' + esc(c.name) + '</h2>';
  html += field('Court', c.court);
  html += field('Register', c.register_num);
  html += field('State', c.state);
  html += field('Status', c.statusCurrent);

  if (c.history && c.history.length) {
    html += '<div class="section"><h3>History</h3>';
    c.history.forEach(h => { html += '<div class="person">' + esc(h[0]) + ' &mdash; ' + esc(h[1]) + '</div>'; });
    html += '</div>';
  }

  const d = c.detail;
  if (d) {
    html += '<div class="section"><h3>Detail (SI)</h3>';
    html += field('Legal Form', d.legal_form);
    html += field('Seat', d.seat);
    if (d.address) {
      const a = d.address;
      const parts = [a.street, [a.postal_code, a.city].filter(Boolean).join(' ')].filter(Boolean);
      html += field('Address', parts.join(', '));
    }
    if (d.capital) html += field('Capital', d.capital.amount + ' ' + d.capital.currency);
    html += field('Business Purpose', d.business_purpose);
    html += field('Representation', d.representation_rules);
    html += field('Articles Date', d.articles_of_association_date);
    html += field('Last Entry', d.last_entry_date);

    if (d.directors && d.directors.length) {
      html += '<div class="section"><h3>Directors</h3>';
      d.directors.forEach(p => {
        let s = esc(p.name || '?');
        if (p.representation) s += ' (' + esc(p.representation) + ')';
        html += '<div class="person">' + s + '</div>';
      });
      html += '</div>';
    }
    if (d.prokura && d.prokura.length) {
      html += '<div class="section"><h3>Prokura</h3>';
      d.prokura.forEach(p => {
        let s = esc(p.name || '?');
        if (p.representation) s += ' (' + esc(p.representation) + ')';
        html += '<div class="person">' + s + '</div>';
      });
      html += '</div>';
    }
    if (d.register_entries && d.register_entries.length) {
      html += '<div class="section"><h3>Register Entries</h3>';
      d.register_entries.forEach(e => {
        html += '<div class="entry"><span class="entry-type">[' + esc(e.type || '') + ']</span> ' + esc(e.text || '') + '</div>';
      });
      html += '</div>';
    }
    html += '</div>';
  }
  html += '</div>';
  return html;
}

function field(label, val) {
  if (!val) return '';
  return '<div class="field"><b>' + esc(label) + '</b> ' + esc(val) + '</div>';
}
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path.startswith('/api/search'):
            self.handle_search()
        else:
            self.send_error(404)

    def handle_search(self):
        qs = parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
        query = qs.get('q', [''])[0].strip()
        so = qs.get('so', ['exact'])[0]
        detail = qs.get('detail', ['0'])[0] == '1'

        if not query:
            self.json_response({'error': 'No search query provided'})
            return

        try:
            args = argparse.Namespace(
                debug=False, force=True, schlagwoerter=query,
                schlagwortOptionen=so, json=True, detail=detail
            )
            h = HandelsRegister(args)
            h.open_startpage()
            companies = h.search_company()

            if detail and companies:
                d = h.fetch_company_detail(result_index=0)
                if d:
                    companies[0]['detail'] = d

            self.json_response({'companies': companies})
        except Exception as e:
            self.json_response({'error': str(e)})

    def json_response(self, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print('[%s] %s' % (self.log_date_time_string(), fmt % args))


if __name__ == '__main__':
    print('Handelsregister Web UI running at http://localhost:%d' % PORT)
    HTTPServer(('', PORT), Handler).serve_forever()
