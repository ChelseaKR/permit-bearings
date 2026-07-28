"""Permit Pathways demo server (stdlib only).

    PYTHONPATH=src python3 demo/app.py

Routes:
    /            structured intake form (?lang=es for Spanish)
    /screen      POST target: pathway results with citations
    /trust       jurisdiction trust dashboard; ?changed=66321 rehearses a
                 legislative amendment to Gov. Code § 66321
    /index.html  full static showcase (also available at /showcase)
    /data/...    repository-local data used by the static showcase
"""

import html
import mimetypes
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from permit_pathways.explanations import load_explanations  # noqa: E402
from permit_pathways.harness import verify_rules  # noqa: E402
from permit_pathways.screening import load_rules, screen  # noqa: E402

RULES_PATH = ROOT / "data" / "rules"
EXPLANATIONS_PATH = ROOT / "data" / "explanations" / "plain-language.json"
GOLDEN_PATH = ROOT / "data" / "golden" / "example.json"
DATA_ROOT = (ROOT / "data").resolve()

STRINGS = {
    "en": {
        "title": "Permit Pathways — demo",
        "tagline": "Every candidate answer cites a source. Selected statewide "
                   "sources are watched for change.",
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
        "dwelling": "What kind of home is on the lot?",
        "dwellings": [("single_family", "Single-family house"),
                      ("multifamily", "Multifamily building"),
                      ("other", "Other / no home yet")],
        "has_primary": "There is (or will be) a home on the lot",
        "unpermitted": "The unit already exists but was built without permits (before 2020)",
        "urbanized": "The property is in a city / urbanized area",
        "sf_zone": "The property is zoned single-family residential",
        "screens": "None of these apply: demolishing rent-restricted or "
                   "affordable housing · a tenant lived there in the last 3 "
                   "years · historic district · wetlands or other protected "
                   "site · parcel was already created by an SB 9 lot split",
        "submit": "Check candidate pathways",
        "disclaimer": "Decision support only — not legal advice and not a "
                      "substitute for your jurisdiction's review.",
        "results": "Possible permit paths and rules",
        "result_intro": "This prototype deterministically matched your answers "
                        "against its bounded encoded rule set. It did not verify "
                        "parcel facts, eligibility, or approval. Plain-language "
                        "explanations are AI-assisted drafts; cited source records "
                        "remain separate below.",
        "none": "No pathway in this prototype's encoded state rule set matched "
                "your answers. This does not mean your project is impossible — "
                "it means it needs staff review. Contact your jurisdiction's "
                "planning counter.",
        "groups": {
            "route": "Possible permit paths",
            "standard": "Rules that may apply",
            "local_process": "Local process information",
            "other": "Other matching rules",
        },
        "means": "What this result means",
        "next": "What you can do next",
        "confirm": "Questions to ask staff",
        "docs": "Typical document hints",
        "source": "Source",
        "evidence": "Why we're saying this",
        "evidence_unavailable": "No supporting excerpt is recorded for this "
                                "non-current source record.",
        "copy_record": "Explanation details",
        "ai_draft": "Draft explanation · made with AI · not reviewed by a person",
        "translation_draft": "Spanish draft · made with AI · not reviewed for accuracy",
        "unavailable": "This explanation is not available. The matching rule "
                       "and source are still shown.",
        "withheld_unverified": "We are not showing next steps because this "
                               "source has no date on file. Ask staff to confirm "
                               "the source before you rely on it.",
        "withheld_stale": "We are not showing next steps because the source "
                          "needs a new check. Confirm it before you rely on it.",
        "next_scope": "These are starting points, not a complete checklist. "
                      "Ask local staff what your project needs.",
        "english_only": "English explanation shown because no valid Spanish draft "
                        "is available.",
        "verified": "source date on file",
        "stale": "SOURCE NEEDS A NEW CHECK",
        "unverified": "NO SOURCE DATE ON FILE",
        "back": "Start over",
        "dashboard": "Trust dashboard",
    },
    "es": {
        "title": "Permit Pathways — demostración",
        "tagline": "Cada respuesta posible cita una fuente. Se monitorean "
                   "fuentes estatales seleccionadas.",
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
        "dwelling": "¿Qué tipo de vivienda hay en el lote?",
        "dwellings": [("single_family", "Casa unifamiliar"),
                      ("multifamily", "Edificio multifamiliar"),
                      ("other", "Otro / aún no hay vivienda")],
        "has_primary": "Hay (o habrá) una vivienda en el lote",
        "unpermitted": "La unidad ya existe pero se construyó sin permisos (antes de 2020)",
        "urbanized": "La propiedad está en una ciudad / área urbanizada",
        "sf_zone": "La propiedad tiene zonificación residencial unifamiliar",
        "screens": "Ninguno de estos aplica: demoler vivienda de renta "
                   "restringida o asequible · un inquilino vivió allí en los "
                   "últimos 3 años · distrito histórico · humedales u otro "
                   "sitio protegido · la parcela ya fue creada por una "
                   "división SB 9",
        "submit": "Revisar posibles vías",
        "disclaimer": "Solo apoyo a la decisión — no es asesoría legal ni "
                      "sustituye la revisión de su jurisdicción.",
        "results": "Posibles vías de permiso y reglas",
        "result_intro": "Este prototipo comparó sus respuestas de forma "
                        "determinista con su conjunto limitado de reglas "
                        "codificadas. No verificó los datos de la parcela, la "
                        "elegibilidad ni la aprobación. Las explicaciones en "
                        "lenguaje sencillo son borradores asistidos por IA; los "
                        "registros de las fuentes citadas se muestran por separado.",
        "none": "Ninguna vía del conjunto de reglas estatales codificadas de "
                "este prototipo coincidió con sus respuestas. Esto no significa "
                "que su proyecto sea imposible — significa que necesita "
                "revisión del personal. Contacte a su departamento de "
                "planificación.",
        "groups": {
            "route": "Posibles vías de permiso",
            "standard": "Reglas que podrían aplicarse",
            "local_process": "Información del proceso local",
            "other": "Otras reglas coincidentes",
        },
        "means": "Qué significa este resultado",
        "next": "Qué puede hacer ahora",
        "confirm": "Preguntas para el personal",
        "docs": "Sugerencias de documentos típicos",
        "source": "Fuente",
        "evidence": "Por qué decimos esto",
        "evidence_unavailable": "No hay un extracto de respaldo registrado "
                                "para este registro de fuente no vigente.",
        "copy_record": "Detalles de la explicación",
        "ai_draft": "Borrador de explicación · creado con IA · no revisado por una persona",
        "translation_draft": "Borrador en español · creado con IA · no revisado "
                             "para comprobar su exactitud",
        "unavailable": "Esta explicación no está disponible. Aun así se muestran "
                       "la regla coincidente y la fuente.",
        "withheld_unverified": "No mostramos los próximos pasos porque esta fuente "
                               "no tiene una fecha registrada. Pida al personal que "
                               "confirme la fuente antes de usarla.",
        "withheld_stale": "No mostramos los próximos pasos porque la fuente necesita "
                          "una nueva comprobación. Confírmela antes de usarla.",
        "next_scope": "Estos son puntos de partida, no una lista completa. "
                      "Pregunte al personal local qué necesita su proyecto.",
        "english_only": "Se muestra la explicación en inglés porque no hay un "
                        "borrador válido en español.",
        "verified": "fecha de la fuente registrada",
        "stale": "LA FUENTE NECESITA UNA NUEVA COMPROBACIÓN",
        "unverified": "SIN FECHA DE LA FUENTE",
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
.result-card{border-left-color:#ccd}.result-card.unverified{border-left-color:#d80}
.result-group{margin:1.5rem 0}.result-group>h2{font-size:1.08rem}
.result-card h3{margin:.15rem 0 .4rem}.result-card h4{font-size:.92rem;
      margin:1rem 0 .25rem}.result-card ol,.result-card ul{margin-top:.3rem}
.result-head{display:flex;align-items:flex-start;justify-content:space-between;
      gap:.75rem;flex-wrap:wrap}.review-note{font-size:.82rem;font-weight:600;
      color:#555}.confirmation{background:#f5f7fb;border-radius:6px;
      padding:.15rem .75rem;margin-top:.8rem}.source-basis{font-size:.88rem}
.key-points{border-left:4px solid #ccd;padding:.05rem .75rem .15rem;
      margin:.8rem 0}.key-points strong{display:inline}
details{border-top:1px solid #dde;margin-top:1rem;padding-top:.35rem}
summary{color:#1a4a8a;cursor:pointer;font-weight:600;min-height:44px;
      display:list-item;padding:.55rem 0}
.badge{font-size:.8rem;padding:.15rem .5rem;border-radius:999px;
       background:#e6f6ee;color:#166534}
.badge.info{background:#fff;color:#555;border:1px solid #ccd}
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
    other_label = (
        "Empezar de nuevo en español"
        if lang == "en"
        else "Start over in English"
    )
    return f"""<!doctype html><html lang="{lang}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body>
<p class="small"><a href="/?lang={lang}">Permit Pathways</a> ·
<a href="/trust?lang={lang}">{STRINGS[lang]['dashboard']}</a> ·
<a href="/?lang={other}" lang="{other}">{other_label}</a></p>
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
<fieldset><legend>{s['dwelling']}</legend>
<select name="dwelling_type">{"".join(f'<option value="{v}">{html.escape(t)}</option>' for v, t in s['dwellings'])}</select>
</fieldset>
<fieldset>
<label><input type="checkbox" name="has_primary_dwelling" checked> {s['has_primary']}</label>
<label><input type="checkbox" name="in_urbanized_area" checked> {s['urbanized']}</label>
<label><input type="checkbox" name="sf_zone" checked> {s['sf_zone']}</label>
<label><input type="checkbox" name="unpermitted_existing"> {s['unpermitted']}</label>
<label><input type="checkbox" name="no_exclusions" checked> {s['screens']}</label>
</fieldset>
<button type="submit">{s['submit']}</button>
</form>""", lang)


def _base_review_label(explanation, lang):
    review = explanation.review
    if review.status == "prototype_review_pending":
        return STRINGS[lang]["ai_draft"]
    if review.status == "jurisdiction_approved":
        if lang == "es":
            return (
                f"Explicación aprobada por la jurisdicción · "
                f"{review.reviewer} · {review.reviewed_on} · "
                f"v{review.reviewed_version}"
            )
        return (
            f"Jurisdiction-approved explanation · "
            f"{review.reviewer} · {review.reviewed_on} · "
            f"v{review.reviewed_version}"
        )
    if lang == "es":
        return (
            f"Explicación revisada por una persona · {review.reviewer} · "
            f"{review.reviewed_on} · v{review.reviewed_version}"
        )
    return (
        f"Human-reviewed explanation · {review.reviewer} · "
        f"{review.reviewed_on} · v{review.reviewed_version}"
    )


def _review_labels(explanation, lang, copy_lang):
    labels = [_base_review_label(explanation, lang)]
    if lang != "es":
        return labels
    if copy_lang != "es":
        labels.append(STRINGS[lang]["english_only"])
        return labels
    localized = explanation.es
    if localized.translation_status == "machine_draft":
        labels.append(STRINGS[lang]["translation_draft"])
    elif localized.translation_status == "jurisdiction_approved":
        labels.append(
            f"Traducción aprobada por la jurisdicción · "
            f"{localized.reviewer} · {localized.reviewed_on} · "
            f"v{localized.reviewed_version}"
        )
    else:
        labels.append(
            f"Traducción revisada por una persona · "
            f"{localized.reviewer} · {localized.reviewed_on} · "
            f"v{localized.reviewed_version}"
        )
    return labels


def _result_badge(result, strings):
    citation = result.rule.citation
    status = "unverified"
    if result.verified:
        status = "stale" if citation.is_stale(180, date.today()) else "verified"
    if status == "verified":
        markup = (
            f"<span class='badge info'>{strings['verified']} "
            f"{html.escape(citation.verified_on or '')}</span>"
        )
    elif status == "stale":
        markup = f"<span class='badge stale'>{strings['stale']}</span>"
    else:
        markup = f"<span class='badge warn'>{strings['unverified']}</span>"
    return status, markup


def render_result_card(result, explanation, lang):
    """Render one decision record without affecting the underlying match."""

    s = STRINGS[lang]
    rule = result.rule
    citation = rule.citation
    status, badge = _result_badge(result, s)
    safe_rule_id = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in rule.rule_id
    )
    card_id = f"result-title-{safe_rule_id}"
    source = (
        f"<p class='source-basis'><b>{s['source']}:</b> "
        f"<a lang='en' href='{html.escape(citation.url)}' rel='noopener'>"
        f"{html.escape(citation.source)}</a></p>"
    )
    docs = "".join(
        f"<li>{html.escape(document)}</li>"
        for document in rule.required_documents
    )
    docs_html = (
        f"<h4 lang='{lang}'>{s['docs']}</h4>"
        f"<ul class='small' lang='en'>{docs}</ul>"
        if docs
        else ""
    )
    evidence = f"""
<details>
  <summary lang="{lang}">{s['evidence']}</summary>
  {f'<p class="small" lang="en">{html.escape(rule.notes)}</p>' if status == "verified" and rule.notes else ''}
  {f'<blockquote lang="en">{html.escape(citation.excerpt)}</blockquote>' if citation.excerpt else ''}
  {f'<p class="small" lang="{lang}">{s["evidence_unavailable"]}</p>' if status != "verified" and not citation.excerpt else ''}
  {docs_html if status == "verified" else ""}
</details>"""

    if status != "verified":
        message = (
            s["withheld_unverified"]
            if status == "unverified"
            else s["withheld_stale"]
        )
        plain_language = (
            f"<div class='notice small' lang='{lang}'>{message}</div>"
        )
        review_note = ""
    elif explanation is None:
        plain_language = (
            f"<div class='notice small' lang='{lang}'>{s['unavailable']}</div>"
        )
        review_note = ""
    else:
        localized = explanation.localized(lang)
        copy_lang = explanation.localized_language(lang)
        next_steps = "".join(
            f"<li>{html.escape(step)}</li>" for step in localized.next_steps
        )
        confirmations = "".join(
            f"<li>{html.escape(item)}</li>"
            for item in localized.confirm_with_staff
        )
        highlights = ""
        if localized.highlights is not None:
            highlight_items = "".join(
                f"<li><strong>{html.escape(item.label)}:</strong> "
                f"{html.escape(item.text)}</li>"
                for item in localized.highlights.items
            )
            highlights = f"""
  <div class="key-points">
    <h4 lang="{copy_lang}">{html.escape(localized.highlights.title)}</h4>
    <ul lang="{copy_lang}">{highlight_items}</ul>
  </div>"""
        plain_language = f"""
<div class="plain-layer">
  <h4 lang="{lang}">{s['means']}</h4>
  <p lang="{copy_lang}">{html.escape(localized.summary)}</p>
  {highlights}
  <h4 lang="{lang}">{s['next']}</h4>
  <p class="small" lang="{lang}">{s['next_scope']}</p>
  <ol lang="{copy_lang}">{next_steps}</ol>
  <div class="confirmation">
    <h4 lang="{lang}">{s['confirm']}</h4>
    <ul lang="{copy_lang}">{confirmations}</ul>
  </div>
</div>"""
        review_note = "".join(
            f"<p class='review-note' lang='{lang}'>"
            f"{html.escape(label)}</p>"
            for label in _review_labels(explanation, lang, copy_lang)
        )
        evidence = evidence.replace(
            "</details>",
            f"<p class='small'><span lang='{lang}'>{s['copy_record']}:</span> "
            f"<span lang='en'>{html.escape(explanation.source_rule_id)} "
            f"v{html.escape(explanation.version)}, "
            f"{html.escape(explanation.updated_on)}</span></p></details>",
        )

    return f"""<article class="card result-card{'' if status == 'verified' else ' unverified'}"
  data-rule-id="{html.escape(rule.rule_id)}" aria-labelledby="{card_id}">
<div class="result-head">
  <h3 id="{card_id}" lang="en">{html.escape(rule.pathway)}</h3>
{badge}
</div>
{review_note}
{plain_language}
{source}
{evidence}
</article>"""


def result_page(form, lang):
    s = STRINGS[lang]
    no_excl = "no_exclusions" in form
    intake = {
        "project_type": form.get("project_type", [""])[0],
        "has_primary_dwelling": "has_primary_dwelling" in form,
        "dwelling_type": form.get("dwelling_type", ["other"])[0],
        "unpermitted_existing": "unpermitted_existing" in form,
        "in_urbanized_area": "in_urbanized_area" in form,
        "zone_class": "single_family_residential" if "sf_zone" in form else "other",
        "demolishes_protected_housing": not no_excl,
        "tenant_occupied_last_3_years": not no_excl,
        "in_historic_district": not no_excl,
        "on_protected_site": not no_excl,
        "parcel_created_by_sb9_split": not no_excl,
        "jurisdiction": form.get("jurisdiction", ["example-city"])[0],
    }
    rules = load_rules(RULES_PATH)
    results = screen(intake, rules)
    try:
        explanations = load_explanations(
            EXPLANATIONS_PATH, rules, strict=False
        )
    except (OSError, ValueError):
        # Screening remains available and evidence remains visible if display
        # copy is missing, malformed, or drifts from the rule source date.
        explanations = {}
    if not results:
        body = f"<h1>{s['results']}</h1><div class='notice'>{s['none']}</div>"
    else:
        grouped = {key: [] for key in ("route", "standard", "local_process", "other")}
        for r in results:
            explanation = explanations.get(r.rule.rule_id)
            group = explanation.display_group if explanation else "other"
            grouped[group].append(render_result_card(r, explanation, lang))
        sections = "".join(
            f"<section class='result-group' aria-labelledby='group-{group}'>"
            f"<h2 id='group-{group}' lang='{lang}'>{s['groups'][group]}</h2>"
            f"{''.join(cards)}</section>"
            for group, cards in grouped.items()
            if cards
        )
        body = (
            f"<h1>{s['results']}</h1>"
            f"<p class='small' lang='{lang}'>{s['result_intro']}</p>"
            f"{sections}"
        )
    body += f"<p><a href='/?lang={lang}'>{s['back']}</a></p>"
    return page(s["results"], body, lang)


def trust_page(query, lang):
    changed = query.get("changed", [])
    report = verify_rules(RULES_PATH, GOLDEN_PATH, today=date.today(),
                          changed_sources=changed)
    total = len(report.verified) + len(report.stale) + len(report.unverified)
    pct = round(100 * len(report.verified) / total) if total else 0
    rows = "".join(
        f"<tr><td>{rid}</td><td><span class='badge'>within review window</span></td></tr>"
        for rid in report.verified
    ) + "".join(
        f"<tr><td>{rid}</td><td><span class='badge stale'>STALE — re-verify</span></td></tr>"
        for rid in report.stale
    ) + "".join(
        f"<tr><td>{rid}</td><td><span class='badge warn'>no dated source record</span></td></tr>"
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
<p><b>{pct}%</b> of rule records have dated source evidence within the
180-day review window · {golden} · checked {report.checked_on}</p>
<div class="bar"><div style="width:{pct}%"></div><div class="stale" style="width:{100 - pct}%"></div></div>
{sim}
<table><tr><th>Rule</th><th>Status</th></tr>{rows}</table>"""
    return page(STRINGS[lang]["dashboard"], body, lang)


def static_path(url_path):
    """Resolve a public static-demo path without allowing path traversal."""

    decoded = unquote(url_path)
    if decoded in {"/index.html", "/showcase"}:
        return ROOT / "index.html"
    if not decoded.startswith("/data/"):
        return None

    candidate = (ROOT / decoded.lstrip("/")).resolve()
    try:
        candidate.relative_to(DATA_ROOT)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


class Handler(BaseHTTPRequestHandler):
    def _send(self, html_text, code=200):
        data = html_text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path):
        data = path.read_bytes()
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _lang(self, query):
        lang = query.get("lang", ["en"])[0]
        return lang if lang in STRINGS else "en"

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        lang = self._lang(query)
        public_file = static_path(url.path)
        if public_file:
            self._send_file(public_file)
        elif url.path == "/":
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
