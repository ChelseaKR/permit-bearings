"""Permit Pathways demo server (stdlib only).

    PYTHONPATH=src python3 demo/app.py

Routes:
    /            structured intake form (?lang=es for Spanish)
    /screen      POST target: pathway results with citations
    /trust       jurisdiction trust dashboard; ?changed=66321 rehearses a
                 legislative amendment to Gov. Code § 66321
"""

import html
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from permit_pathways.harness import verify_rules  # noqa: E402
from permit_pathways.screening import load_rules, screen  # noqa: E402

RULES_PATH = ROOT / "data" / "rules"
GOLDEN_PATH = ROOT / "data" / "golden" / "example.json"

STRINGS = {
    "en": {
        "title": "Permit Pathways — demo",
        "tagline": "Every answer cites its source. Every source is watched for change.",
        "project_type": "What are you proposing?",
        "types": [
            ("adu", "Accessory dwelling unit (backyard cottage, garage conversion)"),
            ("jadu", "Junior ADU (small unit inside my house)"),
            ("two_unit", "Two homes on my single-family lot (SB 9)"),
            ("lot_split", "Split my lot into two parcels (SB 9)"),
        ],
        "jurisdiction": "Where is the property?",
        "jurisdictions": [
            ("davis", "City of Davis"),
            ("woodland", "City of Woodland"),
            ("example-city", "Another California city"),
        ],
        "has_primary": "There is (or will be) a home on the lot",
        "sfr": "My house is a single-family residence",
        "urbanized": "The property is in a city / urbanized area",
        "sf_zone": "The property is zoned single-family residential",
        "screens": "None of these apply: demolishing rent-restricted or "
                   "affordable housing · a tenant lived there in the last 3 "
                   "years · historic district · wetlands or other protected "
                   "site · parcel was already created by an SB 9 lot split",
        "submit": "Find my pathway",
        "disclaimer": "Decision support only — not legal advice and not a "
                      "substitute for your jurisdiction's review.",
        "results": "Candidate pathways",
        "none": "No state pathway matched your answers. This does not mean "
                "your project is impossible — it means it needs staff "
                "review. Contact your jurisdiction's planning counter.",
        "docs": "Typical documents",
        "source": "Source",
        "verified": "verified",
        "back": "Start over",
        "dashboard": "Trust dashboard",
    },
    "es": {
        "title": "Permit Pathways — demostración",
        "tagline": "Cada respuesta cita su fuente. Cada fuente se vigila por cambios.",
        "project_type": "¿Qué propone construir?",
        "types": [
            ("adu", "Vivienda accesoria (casita de patio, conversión de garaje)"),
            ("jadu", "ADU júnior (unidad pequeña dentro de mi casa)"),
            ("two_unit", "Dos viviendas en mi lote unifamiliar (SB 9)"),
            ("lot_split", "Dividir mi lote en dos parcelas (SB 9)"),
        ],
        "jurisdiction": "¿Dónde está la propiedad?",
        "jurisdictions": [
            ("davis", "Ciudad de Davis"),
            ("woodland", "Ciudad de Woodland"),
            ("example-city", "Otra ciudad de California"),
        ],
        "has_primary": "Hay (o habrá) una vivienda en el lote",
        "sfr": "Mi casa es una residencia unifamiliar",
        "urbanized": "La propiedad está en una ciudad / área urbanizada",
        "sf_zone": "La propiedad tiene zonificación residencial unifamiliar",
        "screens": "Ninguno de estos aplica: demoler vivienda de renta "
                   "restringida o asequible · un inquilino vivió allí en los "
                   "últimos 3 años · distrito histórico · humedales u otro "
                   "sitio protegido · la parcela ya fue creada por una "
                   "división SB 9",
        "submit": "Encontrar mi trámite",
        "disclaimer": "Solo apoyo a la decisión — no es asesoría legal ni "
                      "sustituye la revisión de su jurisdicción.",
        "results": "Trámites posibles",
        "none": "Ninguna vía estatal coincidió con sus respuestas. Esto no "
                "significa que su proyecto sea imposible — significa que "
                "necesita revisión del personal. Contacte a su departamento "
                "de planificación.",
        "docs": "Documentos típicos",
        "source": "Fuente",
        "verified": "verificado",
        "back": "Empezar de nuevo",
        "dashboard": "Panel de confianza",
    },
}

CSS = """
body{font-family:system-ui,sans-serif;max-width:44rem;margin:2rem auto;
     padding:0 1rem;line-height:1.5;color:#1a1a2e}
h1{font-size:1.4rem} .tag{color:#555}
fieldset{border:1px solid #ccd;border-radius:8px;margin:1rem 0;padding:1rem}
label{display:block;margin:.4rem 0}
button{background:#1a4a8a;color:#fff;border:0;border-radius:6px;
       padding:.6rem 1.2rem;font-size:1rem;cursor:pointer}
.card{border:1px solid #ccd;border-left:6px solid #2a7;border-radius:8px;
      padding:1rem;margin:1rem 0}
.card.unverified{border-left-color:#d80}
.badge{font-size:.8rem;padding:.15rem .5rem;border-radius:999px;
       background:#e6f6ee;color:#166534}
.badge.warn{background:#fef3e2;color:#92400e}
.badge.stale{background:#fee2e2;color:#991b1b}
blockquote{font-size:.85rem;color:#444;border-left:3px solid #ddd;
           margin:0.5rem 0;padding-left:.8rem}
.small{font-size:.85rem;color:#555} a{color:#1a4a8a}
.bar{height:1rem;border-radius:6px;background:#eee;overflow:hidden;margin:.3rem 0}
.bar>div{height:100%;background:#2a7;float:left}
.bar>div.stale{background:#d33}
table{border-collapse:collapse;width:100%} td,th{border-bottom:1px solid #eee;
      padding:.4rem;text-align:left;font-size:.9rem}
.notice{background:#f5f7fb;border-radius:8px;padding:.8rem;font-size:.85rem}
"""


def page(title, body, lang="en"):
    other = "es" if lang == "en" else "en"
    other_label = "Español" if lang == "en" else "English"
    return f"""<!doctype html><html lang="{lang}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body>
<p class="small"><a href="/?lang={lang}">Permit Pathways</a> ·
<a href="/trust?lang={lang}">{STRINGS[lang]['dashboard']}</a> ·
<a href="/?lang={other}">{other_label}</a></p>
{body}
<p class="small">{STRINGS[lang]['disclaimer']}</p>
</body></html>"""


def intake_form(lang):
    s = STRINGS[lang]
    radios = "".join(
        f'<label><input type="radio" name="project_type" value="{v}" required> {html.escape(t)}</label>'
        for v, t in s["types"]
    )
    juris = "".join(
        f'<option value="{v}">{html.escape(t)}</option>'
        for v, t in s["jurisdictions"]
    )
    return page(s["title"], f"""
<h1>{s['title']}</h1><p class="tag">{s['tagline']}</p>
<form method="post" action="/screen?lang={lang}">
<fieldset><legend>{s['jurisdiction']}</legend>
<select name="jurisdiction">{juris}</select></fieldset>
<fieldset><legend>{s['project_type']}</legend>{radios}</fieldset>
<fieldset>
<label><input type="checkbox" name="has_primary_dwelling" checked> {s['has_primary']}</label>
<label><input type="checkbox" name="sfr" checked> {s['sfr']}</label>
<label><input type="checkbox" name="in_urbanized_area" checked> {s['urbanized']}</label>
<label><input type="checkbox" name="sf_zone" checked> {s['sf_zone']}</label>
<label><input type="checkbox" name="no_exclusions" checked> {s['screens']}</label>
</fieldset>
<button type="submit">{s['submit']}</button>
</form>""", lang)


def result_page(form, lang):
    s = STRINGS[lang]
    no_excl = "no_exclusions" in form
    intake = {
        "project_type": form.get("project_type", [""])[0],
        "has_primary_dwelling": "has_primary_dwelling" in form,
        "dwelling_type": "single_family" if "sfr" in form else "other",
        "in_urbanized_area": "in_urbanized_area" in form,
        "zone_class": "single_family_residential" if "sf_zone" in form else "other",
        "demolishes_protected_housing": not no_excl,
        "tenant_occupied_last_3_years": not no_excl,
        "in_historic_district": not no_excl,
        "on_protected_site": not no_excl,
        "parcel_created_by_sb9_split": not no_excl,
        "jurisdiction": form.get("jurisdiction", ["example-city"])[0],
    }
    results = screen(intake, load_rules(RULES_PATH))
    if not results:
        body = f"<h1>{s['results']}</h1><div class='notice'>{s['none']}</div>"
    else:
        cards = []
        for r in results:
            c = r.rule.citation
            badge = (f"<span class='badge'>{s['verified']} {c.verified_on}</span>"
                     if r.verified else "<span class='badge warn'>UNVERIFIED</span>")
            docs = "".join(f"<li>{html.escape(d)}</li>" for d in r.rule.required_documents)
            docs_html = f"<p class='small'><b>{s['docs']}:</b></p><ul class='small'>{docs}</ul>" if docs else ""
            cards.append(f"""<div class="card{'' if r.verified else ' unverified'}">
<h2>{html.escape(r.rule.pathway)} {badge}</h2>
<p class="small">{html.escape(r.rule.notes)}</p>
<blockquote>{html.escape(c.excerpt or '')}</blockquote>
<p class="small">{s['source']}: <a href="{html.escape(c.url)}">{html.escape(c.source)}</a></p>
{docs_html}</div>""")
        body = f"<h1>{s['results']}</h1>" + "".join(cards)
    body += f"<p><a href='/?lang={lang}'>{s['back']}</a></p>"
    return page(s["results"], body, lang)


def trust_page(query, lang):
    changed = query.get("changed", [])
    report = verify_rules(RULES_PATH, GOLDEN_PATH, today=date.today(),
                          changed_sources=changed)
    total = len(report.verified) + len(report.stale) + len(report.unverified)
    pct = round(100 * len(report.verified) / total) if total else 0
    rows = "".join(
        f"<tr><td>{rid}</td><td><span class='badge'>current</span></td></tr>"
        for rid in report.verified
    ) + "".join(
        f"<tr><td>{rid}</td><td><span class='badge stale'>STALE — re-verify</span></td></tr>"
        for rid in report.stale
    ) + "".join(
        f"<tr><td>{rid}</td><td><span class='badge warn'>never verified</span></td></tr>"
        for rid in report.unverified
    )
    sim = ("<p class='notice'>Rehearsing an amendment to Gov. Code § "
           f"{html.escape(changed[0])}: dependent guidance is stale until staff "
           f"re-verify it. <a href='/trust?lang={lang}'>Reset</a></p>" if changed else
           f"<p class='small'>Rehearse a legislative change: "
           f"<a href='/trust?lang={lang}&changed=66321'>amend § 66321 "
           f"(ADU size/setback/height standards)</a></p>")
    golden = (f"{len(report.golden_passed)}/"
              f"{len(report.golden_passed) + len(report.golden_failed)} golden cases passing")
    body = f"""<h1>{STRINGS[lang]['dashboard']}</h1>
<p><b>{pct}%</b> of guidance verified-current · {golden} · checked {report.checked_on}</p>
<div class="bar"><div style="width:{pct}%"></div><div class="stale" style="width:{100 - pct}%"></div></div>
{sim}
<table><tr><th>Rule</th><th>Status</th></tr>{rows}</table>"""
    return page(STRINGS[lang]["dashboard"], body, lang)


class Handler(BaseHTTPRequestHandler):
    def _send(self, html_text, code=200):
        data = html_text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _lang(self, query):
        lang = query.get("lang", ["en"])[0]
        return lang if lang in STRINGS else "en"

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        lang = self._lang(query)
        if url.path == "/":
            self._send(intake_form(lang))
        elif url.path == "/trust":
            self._send(trust_page(query, lang))
        else:
            self._send(page("404", "<h1>404</h1>"), 404)

    def do_POST(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode())
        self._send(result_page(form, self._lang(query)))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Permit Pathways demo → http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
