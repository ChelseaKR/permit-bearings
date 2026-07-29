"""Permit Bearings demo server (stdlib only).

    PYTHONPATH=src python3 demo/app.py

Routes:
    /            structured intake form (?lang=es for Spanish)
    /screen      POST target: pathway results with citations
    /trust       jurisdiction trust dashboard; ?changed=ca-gov-66321
                 rehearses a legislative amendment to Gov. Code § 66321
    /index.html  static landing page
    /check.html  applicant project guide
    /review.html ordinance review aid
    /evidence.html
                 public evidence and source-status page
    /showcase    compatibility alias for /check.html
    /assets/...  public static styles and browser application code
    /data/...    repository-local data used by the static tools
"""

import html
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from permit_pathways.explanations import load_explanations  # noqa: E402
from permit_pathways.harness import verify_rules  # noqa: E402
from permit_pathways.dates import utc_today  # noqa: E402
from permit_pathways.screening import load_rules, screen  # noqa: E402

RULES_PATH = ROOT / "data" / "rules"
EXPLANATIONS_PATH = ROOT / "data" / "explanations" / "plain-language.json"
GOLDEN_PATH = ROOT / "data" / "golden" / "example.json"
DATA_ROOT = (ROOT / "data").resolve()
ASSETS_ROOT = (ROOT / "assets").resolve()
MAX_BODY_BYTES = 64 * 1024
SB9_BASE_FIELDS = (
    "in_urbanized_area",
    "sf_zone",
    "demolishes_protected_housing",
    "tenant_occupied_last_3_years",
    "ellis_withdrawal_last_15_years",
    "on_protected_site",
)
SB9_TWO_UNIT_FIELDS = (
    "two_unit_contributing_historic_location",
    "two_unit_individually_listed_historic_property",
)
SB9_LOT_SPLIT_FIELDS = (
    "lot_split_on_historic_landmark_site",
    "lot_split_alters_historic_district_resource",
    "parcel_created_by_sb9_split",
    "adjacent_sb9_split_same_actor",
    "proposed_lot_ratio_compliant",
    "proposed_lot_size_compliant",
)
PROJECT_FIELDS = {
    "adu": (
        "primary_dwelling_status",
        "adu_project_form",
        "unpermitted_existing",
    ),
    "jadu": ("primary_dwelling_status", "unpermitted_existing"),
    "two_unit": SB9_BASE_FIELDS + SB9_TWO_UNIT_FIELDS,
    "lot_split": SB9_BASE_FIELDS + SB9_LOT_SPLIT_FIELDS,
}
FIELD_VALUES = {
    "primary_dwelling_status": {
        "existing_single_family",
        "existing_multifamily",
        "proposed_single_family",
        "proposed_multifamily",
        "none",
        "unknown",
    },
    "adu_project_form": {
        "new_detached",
        "new_attached",
        "conversion",
        "same_footprint_rebuild",
        "unknown",
    },
}
FIELD_VALUES.update(
    {
        field: {"yes", "no", "unknown"}
        for field in SB9_BASE_FIELDS
        + SB9_TWO_UNIT_FIELDS
        + SB9_LOT_SPLIT_FIELDS
        + ("unpermitted_existing",)
    }
)

STRINGS = {
    "en": {
        "title": "Permit Bearings | demo",
        "tagline": "Find a candidate route. See the sources behind it. "
                   "Take open questions to staff.",
        "scope": "The language choice applies to the applicant form and results. "
                 "The trust dashboard remains in English.",
        "project_type": "What are you proposing?",
        "types": [
            ("adu", "Accessory dwelling unit (backyard cottage, garage conversion)"),
            ("jadu", "Junior ADU (small unit inside my house)"),
            ("two_unit", "Two homes on my single-family lot (SB 9)"),
            ("lot_split", "Split my lot into two parcels (SB 9)"),
        ],
        "tri": [("yes", "Yes"), ("no", "No"), ("unknown", "I'm not sure")],
        "primary_question": "What dwelling exists on the lot now, or is proposed?",
        "primary_help": "Choose what exists now separately from what is only "
                        "proposed. Some review clocks depend on that difference.",
        "primary_options": [
            ("existing_single_family", "An existing single-family home"),
            ("existing_multifamily", "An existing multifamily building"),
            ("proposed_single_family",
             "A single-family home is proposed; none exists now"),
            ("proposed_multifamily",
             "A multifamily building is proposed; none exists now"),
            ("none", "No primary dwelling exists or is proposed"),
            ("unknown", "I'm not sure"),
        ],
        "adu_form_question": "What kind of ADU work are you planning?",
        "adu_form_options": [
            ("new_detached", "Build a new detached ADU"),
            ("new_attached", "Build a new attached ADU"),
            ("conversion", "Convert space in an existing structure"),
            ("same_footprint_rebuild",
             "Replace a structure in the same location and dimensions"),
            ("unknown", "I'm not sure"),
        ],
        "question_intro": "Choose “I'm not sure” when you do not know. "
                          "Uncertain material facts go to staff instead of "
                          "being assumed in favor of a path.",
        "unpermitted_questions": {
            "adu": "Are you trying to legalize an ADU built without permits "
                   "before January 1, 2020?",
            "jadu": "Are you trying to legalize a junior ADU built without "
                    "permits before January 1, 2020?",
        },
        "questions": {
            "in_urbanized_area": "Is the property inside an incorporated city "
                                 "or another SB 9-qualifying urban area?",
            "sf_zone": "Is the property zoned for single-family residential use?",
            "demolishes_protected_housing": "Would the project demolish or alter "
                                            "rent-restricted, price-controlled, "
                                            "or deed-restricted affordable housing?",
            "tenant_occupied_last_3_years": "Has a tenant lived in housing the "
                                            "project would demolish or alter "
                                            "during the last three years?",
            "ellis_withdrawal_last_15_years": "Was housing on the property "
                                              "withdrawn from rental use under "
                                              "the Ellis Act during the last "
                                              "15 years?",
            "two_unit_contributing_historic_location":
                "Would the two-home project be located in a contributing "
                "structure in a state-listed historic district, or in a "
                "historic property or district protected by a city or county "
                "ordinance?",
            "two_unit_individually_listed_historic_property":
                "Is the parcel individually listed in the State Historic "
                "Resources Inventory, or is the property individually "
                "designated or listed as a city or county landmark?",
            "lot_split_on_historic_landmark_site":
                "Is the parcel within a historical landmark property in the "
                "State Historic Resources Inventory, or on a site designated "
                "or listed as a city or county landmark?",
            "lot_split_alters_historic_district_resource":
                "Would the lot split require demolition or alteration of a "
                "contributing structure or an existing exterior structural "
                "wall in a historic district listed by California or "
                "designated by a city or county?",
            "on_protected_site": "Does the property have a wetland, hazardous-"
                                 "land, conservation, habitat, or other "
                                 "protected-site condition named in SB 9?",
            "parcel_created_by_sb9_split": "Was this parcel already created by "
                                            "an SB 9 lot split?",
            "adjacent_sb9_split_same_actor": "Has the same owner, or someone "
                                              "working with that owner, used SB 9 "
                                              "to split an adjacent parcel?",
            "proposed_lot_ratio_compliant": "Would each proposed parcel contain "
                                            "at least 40% of the original lot area?",
            "proposed_lot_size_compliant": "Would both new lots be at least "
                                           "1,200 square feet, or meet a smaller "
                                           "minimum verified in a current local "
                                           "ordinance?",
        },
        "jurisdiction": "Where is the property?",
        "jurisdictions": [
            ("davis", "City of Davis"),
            ("woodland", "City of Woodland"),
            ("example-city", "Another California city"),
        ],
        "submit": "Check candidate pathways",
        "disclaimer": "Decision support only. This is not legal advice or a "
                      "substitute for your jurisdiction's review.",
        "results": "Possible permit paths and rules",
        "result_intro": "We compared your answers with the limited set of rules "
                        "in this prototype. We did not verify the property facts, "
                        "decide eligibility, or approve the project.",
        "none": "The included rules do not identify a possible path from these "
                "answers. This does not mean the project is impossible. Ask the "
                "local planning counter to review it.",
        "supporting_only": "Supporting local information is shown below, but "
                           "it is not a candidate permit path.",
        "unknown_heading": "Staff review is needed before showing a possible path",
        "unknown_intro": "You chose “I'm not sure” for a fact that can change the "
                         "result. Confirm these items with the local planning counter:",
        "explanation_banner": "About these explanations: the text shown is an "
                              "AI-assisted draft and has not been reviewed by a "
                              "person. The cited source stays separate in each card.",
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
        "title": "Permit Bearings | demostración",
        "tagline": "Encuentre una posible ruta. Vea las fuentes que la respaldan. "
                   "Consulte las preguntas pendientes con el personal de la agencia.",
        "scope": "El idioma elegido se aplica al formulario y a los resultados "
                 "para solicitantes. El panel de confianza permanece en inglés.",
        "project_type": "¿Qué propone construir?",
        "types": [
            ("adu", "Vivienda accesoria (casita de patio, conversión de garaje)"),
            ("jadu", "ADU júnior (unidad pequeña dentro de mi casa)"),
            ("two_unit", "Dos viviendas en mi lote unifamiliar (SB 9)"),
            ("lot_split", "Dividir mi lote en dos parcelas (SB 9)"),
        ],
        "tri": [("yes", "Sí"), ("no", "No"), ("unknown", "No lo sé")],
        "primary_question": "¿Qué vivienda existe ahora en el lote o está propuesta?",
        "primary_help": "Distinga lo que ya existe de lo que solo está propuesto. "
                        "Algunos plazos dependen de esa diferencia.",
        "primary_options": [
            ("existing_single_family", "Ya existe una vivienda unifamiliar"),
            ("existing_multifamily", "Ya existe un edificio multifamiliar"),
            ("proposed_single_family",
             "Se propone una vivienda unifamiliar; aún no existe"),
            ("proposed_multifamily",
             "Se propone un edificio multifamiliar; aún no existe"),
            ("none", "No existe ni se propone una vivienda principal"),
            ("unknown", "No lo sé"),
        ],
        "adu_form_question": "¿Qué tipo de trabajo de ADU propone?",
        "adu_form_options": [
            ("new_detached", "Construir una ADU nueva y separada"),
            ("new_attached", "Construir una ADU nueva y adosada"),
            ("conversion", "Convertir espacio dentro de una estructura existente"),
            ("same_footprint_rebuild",
             "Reemplazar una estructura en el mismo lugar y con las mismas dimensiones"),
            ("unknown", "No lo sé"),
        ],
        "question_intro": "Elija “No lo sé” si no conoce la respuesta. Los datos "
                          "materiales inciertos se envían al personal en lugar de "
                          "suponer que favorecen una vía.",
        "unpermitted_questions": {
            "adu": "¿Quiere legalizar una ADU construida sin permisos antes "
                   "del 1 de enero de 2020?",
            "jadu": "¿Quiere legalizar una ADU júnior construida sin permisos "
                    "antes del 1 de enero de 2020?",
        },
        "questions": {
            "in_urbanized_area": "¿Está la propiedad dentro de una ciudad "
                                 "incorporada u otra área urbana que califique "
                                 "para la SB 9?",
            "sf_zone": "¿Tiene la propiedad zonificación residencial unifamiliar?",
            "demolishes_protected_housing": "¿El proyecto demolería o alteraría "
                                            "vivienda con renta o precio controlado, "
                                            "o vivienda asequible restringida por escritura?",
            "tenant_occupied_last_3_years": "¿Un inquilino vivió durante los "
                                            "últimos tres años en una vivienda "
                                            "que el proyecto demolería o alteraría?",
            "ellis_withdrawal_last_15_years": "¿Se retiró del mercado de alquiler "
                                              "alguna vivienda de la propiedad "
                                              "conforme a la Ley Ellis durante "
                                              "los últimos 15 años?",
            "two_unit_contributing_historic_location":
                "¿Estaría el proyecto de dos viviendas en una estructura que "
                "contribuye al valor de un distrito histórico incluido por el "
                "estado, o en una propiedad o distrito histórico protegido "
                "por una ordenanza local?",
            "two_unit_individually_listed_historic_property":
                "¿Está la parcela incluida individualmente en el inventario "
                "estatal de recursos históricos, o está la propiedad designada "
                "individualmente como monumento histórico por la ciudad o el "
                "condado?",
            "lot_split_on_historic_landmark_site":
                "¿Está la parcela dentro de una propiedad incluida en el "
                "inventario estatal de recursos históricos, o en un sitio "
                "designado como monumento histórico por la ciudad o el condado?",
            "lot_split_alters_historic_district_resource":
                "¿La división del lote exigiría demoler o alterar una "
                "estructura que contribuye a un distrito histórico, o un muro "
                "estructural exterior existente, dentro de un distrito "
                "histórico incluido por el estado o designado localmente?",
            "on_protected_site": "¿Tiene la propiedad humedales, suelo peligroso, "
                                 "terreno de conservación, hábitat u otra condición "
                                 "de sitio protegido indicada en la SB 9?",
            "parcel_created_by_sb9_split": "¿Esta parcela ya fue creada mediante "
                                            "una división de lote SB 9?",
            "adjacent_sb9_split_same_actor": "¿El mismo propietario, o alguien que "
                                              "actúe con ese propietario, usó la "
                                              "SB 9 para dividir una parcela adyacente?",
            "proposed_lot_ratio_compliant": "¿Cada parcela propuesta tendría al "
                                            "menos el 40% del área del lote original?",
            "proposed_lot_size_compliant": "¿Tendrían ambos lotes nuevos al "
                                           "menos 1,200 pies cuadrados, o "
                                           "cumplirían un mínimo menor verificado "
                                           "en una ordenanza local vigente?",
        },
        "jurisdiction": "¿Dónde está la propiedad?",
        "jurisdictions": [
            ("davis", "Ciudad de Davis"),
            ("woodland", "Ciudad de Woodland"),
            ("example-city", "Otra ciudad de California"),
        ],
        "submit": "Revisar posibles vías",
        "disclaimer": "Solo apoyo a la decisión. No es asesoría legal ni "
                      "sustituye la revisión de su jurisdicción.",
        "results": "Posibles vías de permiso y reglas",
        "result_intro": "Comparamos sus respuestas con el conjunto limitado de "
                        "reglas de este prototipo. No verificamos los datos de "
                        "la propiedad, decidimos la elegibilidad ni aprobamos "
                        "el proyecto.",
        "none": "Las reglas incluidas no identifican una posible vía con estas "
                "respuestas. Esto no significa que el proyecto sea imposible. "
                "Pida una revisión en el departamento local de planificación.",
        "supporting_only": "Abajo se muestra información local de apoyo, pero "
                           "no es una posible vía de permiso.",
        "unknown_heading": "Se necesita revisión del personal antes de mostrar "
                           "una posible vía",
        "unknown_intro": "Eligió “No lo sé” para un dato que puede cambiar el "
                         "resultado. Confirme estos puntos con el departamento "
                         "local de planificación:",
        "explanation_banner": "Sobre estas explicaciones: el texto mostrado es "
                              "un borrador creado con ayuda de IA y no ha sido "
                              "revisado por una persona. El texto en español es "
                              "una traducción automática sin revisión de exactitud. "
                              "La fuente citada se mantiene separada en cada tarjeta.",
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
*{box-sizing:border-box}
body{font-family:system-ui,sans-serif;margin:0;line-height:1.55;
     color:#1a1a2e;background:#fafafa}
main{max-width:44rem;margin:0 auto;padding:1.5rem 1rem 3rem}
h1{font-size:1.4rem} .tag{color:#555}
nav{display:flex;flex-wrap:wrap;align-items:center;gap:.2rem .6rem}
nav a{display:inline-flex;align-items:center;min-height:44px;padding:0 .2rem}
.skip-link{position:absolute;left:.75rem;top:.5rem;transform:translateY(-180%);
           background:#fff;padding:.6rem;z-index:2}.skip-link:focus{transform:none}
:focus-visible{outline:3px solid #1a4a8a;outline-offset:2px}
fieldset{border:1px solid #ccd;border-radius:8px;margin:1rem 0;padding:1rem;
         min-width:0}
legend{font-weight:650}
label{display:flex;align-items:flex-start;gap:.55rem;min-height:44px;
      padding:.3rem 0}
label>input[type=radio],label>input[type=checkbox]{width:1.25rem;height:1.25rem;
      flex:none;margin-top:.15rem}
select{width:100%;min-height:44px;border:2px solid #6f6f70;border-radius:6px;
       background:#fff;color:#1a1a2e;font-size:1rem;padding:.45rem}
button{background:#1a4a8a;color:#fff;border:0;border-radius:6px;
       min-height:44px;padding:.6rem 1.2rem;font-size:1rem;cursor:pointer}
.choice-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
             gap:.2rem .8rem}.conditional[hidden]{display:none}
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
.visually-hidden{position:absolute!important;width:1px;height:1px;padding:0;
                 margin:-1px;overflow:hidden;clip:rect(0,0,0,0);
                 white-space:nowrap;border:0}
@media(max-width:30rem){.choice-grid{grid-template-columns:1fr}}
"""


def _ui_text(value):
    """Normalize editorial dash punctuation without changing stored evidence."""

    text = str(value)
    dash = chr(0x2014)
    return text.replace(f" {dash} ", " ").replace(dash, " ")


def _ui_escape(value, *, quote=True):
    return html.escape(_ui_text(value), quote=quote)


def page(title, body, lang="en"):
    other = "es" if lang == "en" else "en"
    other_label = (
        "Empezar de nuevo en español"
        if lang == "en"
        else "Start over in English"
    )
    skip_label = "Saltar al contenido" if lang == "es" else "Skip to content"
    nav_label = "Navegación" if lang == "es" else "Navigation"
    return f"""<!doctype html><html lang="{lang}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body>
<a class="skip-link" href="#main">{skip_label}</a>
<main id="main">
<nav aria-label="{nav_label}">
<a href="/?lang={lang}">Permit Bearings</a>
<a href="/trust?lang=en" lang="en">Trust dashboard (English)</a>
<a href="/?lang={other}" lang="{other}">{html.escape(other_label)}</a>
</nav>
{body}
<p class="small">{html.escape(STRINGS[lang]['scope'])}</p>
<p class="small">{html.escape(STRINGS[lang]['disclaimer'])}</p>
</main></body></html>"""


def _radio_question(name, legend, options, *, projects, help_text=None):
    labels = "".join(
        f'<label><input type="radio" name="{html.escape(name)}" '
        f'value="{html.escape(value)}" required> {html.escape(label)}</label>'
        for value, label in options
    )
    help_markup = (
        f'<p class="small" id="{html.escape(name)}-help">'
        f"{html.escape(help_text)}</p>"
        if help_text
        else ""
    )
    described_by = (
        f' aria-describedby="{html.escape(name)}-help"' if help_text else ""
    )
    return (
        f'<fieldset class="conditional" data-projects="{projects}"'
        f"{described_by}>"
        f"<legend>{html.escape(legend)}</legend>{help_markup}"
        f'<div class="choice-grid">{labels}</div></fieldset>'
    )


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
    tri = s["tri"]
    conditional = [
        _radio_question(
            "primary_dwelling_status",
            s["primary_question"],
            s["primary_options"],
            projects="adu,jadu",
            help_text=s["primary_help"],
        ),
        _radio_question(
            "adu_project_form",
            s["adu_form_question"],
            s["adu_form_options"],
            projects="adu",
        ),
        _radio_question(
            "unpermitted_existing",
            s["unpermitted_questions"]["adu"],
            tri,
            projects="adu",
        ),
        _radio_question(
            "unpermitted_existing",
            s["unpermitted_questions"]["jadu"],
            tri,
            projects="jadu",
        ),
    ]
    conditional.extend(
        _radio_question(
            field,
            s["questions"][field],
            tri,
            projects="two_unit,lot_split",
        )
        for field in SB9_BASE_FIELDS
    )
    conditional.extend(
        _radio_question(
            field,
            s["questions"][field],
            tri,
            projects="two_unit",
        )
        for field in SB9_TWO_UNIT_FIELDS
    )
    conditional.extend(
        _radio_question(
            field,
            s["questions"][field],
            tri,
            projects="lot_split",
        )
        for field in SB9_LOT_SPLIT_FIELDS
    )
    conditional_markup = "".join(conditional)
    return page(s["title"], f"""
<h1>{html.escape(s['title'])}</h1>
<p class="tag">{html.escape(s['tagline'])}</p>
<form method="post" action="/screen?lang={lang}">
<fieldset><legend>{html.escape(s['jurisdiction'])}</legend>
<select name="jurisdiction" required>
<option value="" selected disabled>Seleccione</option>{juris}</select></fieldset>
<fieldset><legend>{html.escape(s['project_type'])}</legend>
<div class="choice-grid">{radios}</div></fieldset>
<p class="small">{html.escape(s['question_intro'])}</p>
<div id="project-questions">{conditional_markup}</div>
<button type="submit">{html.escape(s['submit'])}</button>
</form>
<script>
(() => {{
  const projectControls = document.querySelectorAll(
    'input[name="project_type"]'
  );
  const conditionalQuestions = document.querySelectorAll(
    "#project-questions [data-projects]"
  );
  const updateQuestions = () => {{
    const selected = document.querySelector(
      'input[name="project_type"]:checked'
    )?.value;
    conditionalQuestions.forEach(question => {{
      const active = Boolean(selected)
        && question.dataset.projects.split(",").includes(selected);
      question.hidden = !active;
      question.querySelectorAll("input").forEach(control => {{
        control.disabled = !active;
      }});
    }});
  }};
  projectControls.forEach(control =>
    control.addEventListener("change", updateQuestions)
  );
  updateQuestions();
}})();
</script>""", lang)


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


def _result_badge(result, strings, *, today=None):
    citation = result.rule.citation
    status = "unverified"
    if result.verified:
        status = (
            "stale"
            if citation.is_stale(180, today or utc_today())
            else "verified"
        )
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


def _safe_external_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return None
    return value


def render_result_card(
    result,
    explanation,
    lang,
    *,
    suppress_pending_review=False,
    today=None,
):
    """Render one decision record without affecting the underlying match."""

    s = STRINGS[lang]
    rule = result.rule
    citation = rule.citation
    status, badge = _result_badge(result, s, today=today)
    safe_rule_id = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in rule.rule_id
    )
    card_id = f"result-title-{safe_rule_id}"
    source_url = _safe_external_url(citation.url)
    source_record = (
        f"<a lang='en' href='{html.escape(source_url, quote=True)}' "
        f"rel='noopener'>{_ui_escape(citation.source)}</a>"
        if source_url
        else f"<span lang='en'>{_ui_escape(citation.source)}</span>"
    )
    source = (
        f"<p class='source-basis'><b>{html.escape(s['source'])}:</b> "
        f"{source_record}</p>"
    )
    docs = "".join(
        f"<li>{_ui_escape(document)}</li>"
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
  {f'<p class="small" lang="en">{_ui_escape(rule.notes)}</p>' if status == "verified" and rule.notes else ''}
  {f'<blockquote lang="en">{html.escape(citation.excerpt)}</blockquote>' if citation.excerpt else ''}
  {f'<p class="small" lang="{lang}">{s["evidence_unavailable"]}</p>' if status != "verified" and not citation.excerpt else ''}
  {docs_html if status == "verified" else ""}
</details>"""

    display_title = rule.pathway
    display_title_lang = "en"
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
        display_title = localized.title
        display_title_lang = copy_lang
        next_steps = "".join(
            f"<li>{_ui_escape(step)}</li>" for step in localized.next_steps
        )
        confirmations = "".join(
            f"<li>{_ui_escape(item)}</li>"
            for item in localized.confirm_with_staff
        )
        highlights = ""
        if localized.highlights is not None:
            highlight_items = "".join(
                f"<li><strong>{_ui_escape(item.label)}:</strong> "
                f"{_ui_escape(item.text)}</li>"
                for item in localized.highlights.items
            )
            highlights = f"""
  <div class="key-points">
    <h4 lang="{copy_lang}">{_ui_escape(localized.highlights.title)}</h4>
    <ul lang="{copy_lang}">{highlight_items}</ul>
  </div>"""
        plain_language = f"""
<div class="plain-layer">
  <h4 lang="{lang}">{s['means']}</h4>
  <p lang="{copy_lang}">{_ui_escape(localized.summary)}</p>
  {highlights}
  <h4 lang="{lang}">{s['next']}</h4>
  <p class="small" lang="{lang}">{s['next_scope']}</p>
  <ol lang="{copy_lang}">{next_steps}</ol>
  <div class="confirmation">
    <h4 lang="{lang}">{s['confirm']}</h4>
    <ul lang="{copy_lang}">{confirmations}</ul>
  </div>
</div>"""
        pending_only = (
            explanation.review.status == "prototype_review_pending"
            and (
                lang != "es"
                or (
                    copy_lang == "es"
                    and localized.translation_status == "machine_draft"
                )
            )
        )
        review_note = (
            ""
            if suppress_pending_review and pending_only
            else "".join(
                f"<p class='review-note' lang='{lang}'>"
                f"{_ui_escape(label)}</p>"
                for label in _review_labels(explanation, lang, copy_lang)
            )
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
  <h3 id="{card_id}" lang="{display_title_lang}">{_ui_escape(display_title)}</h3>
{badge}
</div>
{review_note}
{plain_language}
{source}
{evidence}
</article>"""


def _form_value(form, name):
    values = form.get(name, [])
    if not isinstance(values, (list, tuple)) or len(values) != 1:
        return None
    value = values[0]
    return value if isinstance(value, str) else None


def _question_label(field, lang, project_type=None):
    s = STRINGS[lang]
    if field == "primary_dwelling_status":
        return s["primary_question"]
    if field == "adu_project_form":
        return s["adu_form_question"]
    if field == "unpermitted_existing":
        return s["unpermitted_questions"].get(
            project_type, s["unpermitted_questions"]["adu"]
        )
    return s["questions"].get(field, field)


def result_page(form, lang):
    s = STRINGS[lang]
    project_type = _form_value(form, "project_type")
    jurisdiction = _form_value(form, "jurisdiction")
    allowed_jurisdictions = {
        value for value, _label in s["jurisdictions"]
    }
    if project_type not in PROJECT_FIELDS or jurisdiction not in allowed_jurisdictions:
        body = (
            f"<h1>{html.escape(s['unknown_heading'])}</h1>"
            f"<div class='notice'>{html.escape(s['unknown_intro'])}</div>"
            f"<p><a href='/?lang={lang}'>{html.escape(s['back'])}</a></p>"
        )
        return page(s["results"], body, lang)

    intake = {
        "project_type": project_type,
        "jurisdiction": jurisdiction,
    }
    unresolved = []
    for field in PROJECT_FIELDS[project_type]:
        value = _form_value(form, field)
        if value not in FIELD_VALUES[field] or value == "unknown":
            unresolved.append(field)
        elif value is not None:
            intake[field] = value

    if unresolved:
        questions = "".join(
            f"<li>{html.escape(_question_label(field, lang, project_type))}</li>"
            for field in unresolved
        )
        body = (
            f"<h1>{html.escape(s['unknown_heading'])}</h1>"
            f"<div class='notice'><p>{html.escape(s['unknown_intro'])}</p>"
            f"<ul>{questions}</ul></div>"
            f"<p><a href='/?lang={lang}'>{html.escape(s['back'])}</a></p>"
        )
        return page(s["results"], body, lang)

    as_of = utc_today()
    rules = load_rules(RULES_PATH, today=as_of)
    results = screen(intake, rules)
    try:
        explanations = load_explanations(
            EXPLANATIONS_PATH, rules, strict=False, today=as_of
        )
    except (OSError, ValueError):
        # Screening remains available and evidence remains visible if display
        # copy is missing, malformed, or drifts from the rule source date.
        explanations = {}
    if not results:
        body = (
            f"<h1>{html.escape(s['results'])}</h1>"
            f"<div class='notice'>{html.escape(s['none'])}</div>"
        )
    else:
        has_route = any(
            result.rule.display_group == "route" for result in results
        )
        grouped = {key: [] for key in ("route", "standard", "local_process", "other")}
        shown = []
        for result in results:
            status, _badge = _result_badge(result, s, today=as_of)
            explanation = explanations.get(result.rule.rule_id)
            if status == "verified" and explanation is not None:
                localized = explanation.localized(lang)
                copy_lang = explanation.localized_language(lang)
                shown.append((explanation, localized, copy_lang))
        shared_draft = bool(shown) and all(
            explanation.review.status == "prototype_review_pending"
            and (
                lang != "es"
                or (
                    copy_lang == "es"
                    and localized.translation_status == "machine_draft"
                )
            )
            for explanation, localized, copy_lang in shown
        )
        for r in results:
            explanation = explanations.get(r.rule.rule_id)
            group = (
                r.rule.display_group
                if r.rule.display_group in grouped
                else "other"
            )
            grouped[group].append(
                render_result_card(
                    r,
                    explanation,
                    lang,
                    suppress_pending_review=shared_draft,
                    today=as_of,
                )
            )
        sections = "".join(
            f"<section class='result-group' aria-labelledby='group-{group}'>"
            f"<h2 id='group-{group}' lang='{lang}'>{s['groups'][group]}</h2>"
            f"{''.join(cards)}</section>"
            for group, cards in grouped.items()
            if cards
        )
        draft_banner = (
            f"<div class='notice small' lang='{lang}'>"
            f"{html.escape(s['explanation_banner'])}</div>"
            if shared_draft
            else ""
        )
        no_route_notice = (
            ""
            if has_route
            else (
                f"<div class='notice' lang='{lang}'>"
                f"<p>{html.escape(s['none'])}</p>"
                f"<p>{html.escape(s['supporting_only'])}</p></div>"
            )
        )
        body = (
            f"<h1>{html.escape(s['results'])}</h1>"
            f"<p class='small' lang='{lang}'>"
            f"{html.escape(s['result_intro'])}</p>"
            f"{no_route_notice}{draft_banner}{sections}"
        )
    body += (
        f"<p><a href='/?lang={lang}'>{html.escape(s['back'])}</a></p>"
    )
    return page(s["results"], body, lang)


def trust_page(query, lang):
    changed = query.get("changed", [])
    report = verify_rules(RULES_PATH, GOLDEN_PATH, today=utc_today(),
                          changed_source_ids=changed)
    total = len(report.verified) + len(report.stale) + len(report.unverified)
    pct = round(100 * len(report.verified) / total) if total else 0
    rows = "".join(
        f"<tr><td>{rid}</td><td><span class='badge'>within review window</span></td></tr>"
        for rid in report.verified
    ) + "".join(
        f"<tr><td>{rid}</td><td><span class='badge stale'>STALE: re-verify</span></td></tr>"
        for rid in report.stale
    ) + "".join(
        f"<tr><td>{rid}</td><td><span class='badge warn'>no dated source record</span></td></tr>"
        for rid in report.unverified
    )
    changed_label = (
        "Gov. Code § 66321"
        if changed and changed[0] == "ca-gov-66321"
        else f"source {changed[0]}" if changed else ""
    )
    sim = ("<p class='notice'>Rehearsing an amendment to "
           f"{html.escape(changed_label)}: dependent guidance is stale until staff "
           f"re-verify it. <a href='/trust?lang={lang}'>Reset</a></p>" if changed else
           f"<p class='small'>Rehearse a legislative change: "
           f"<a href='/trust?lang={lang}&changed=ca-gov-66321'>amend § 66321 "
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
    page_paths = {
        "/index.html": "index.html",
        "/check.html": "check.html",
        "/review.html": "review.html",
        "/evidence.html": "evidence.html",
        "/showcase": "check.html",
    }
    if decoded in page_paths:
        return ROOT / page_paths[decoded]

    allowed_root = (
        DATA_ROOT if decoded.startswith("/data/")
        else ASSETS_ROOT if decoded.startswith("/assets/")
        else None
    )
    if allowed_root is None:
        return None
    candidate = (ROOT / decoded.lstrip("/")).resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


class Handler(BaseHTTPRequestHandler):
    def _security_headers(self):
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; base-uri 'none'; form-action 'self'; "
            "frame-ancestors 'none'",
        )
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )

    def _send(self, html_text, code=200, *, extra_headers=None):
        data = html_text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path):
        data = path.read_bytes()
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self._security_headers()
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
            self._send(trust_page(query, "en"))
        else:
            self._send(page("404", "<h1>404</h1>"), 404)

    def do_POST(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        lang = self._lang(query)
        if url.path != "/screen":
            self._send(
                page("405", "<h1>Method not allowed</h1>", lang),
                405,
                extra_headers={"Allow": "GET"},
            )
            return
        content_type = self.headers.get("Content-Type", "")
        if content_type.split(";", 1)[0].strip().lower() != (
            "application/x-www-form-urlencoded"
        ):
            self._send(
                page("415", "<h1>Unsupported media type</h1>", lang),
                415,
            )
            return
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            self._send(page("411", "<h1>Content length required</h1>", lang), 411)
            return
        try:
            length = int(raw_length)
        except ValueError:
            self._send(page("400", "<h1>Invalid content length</h1>", lang), 400)
            return
        if length < 0:
            self._send(page("400", "<h1>Invalid content length</h1>", lang), 400)
            return
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            self._send(
                page("413", "<h1>Request is too large</h1>", lang),
                413,
            )
            return
        try:
            raw_body = self.rfile.read(length)
            if len(raw_body) != length:
                raise ValueError("incomplete request body")
            form = parse_qs(
                raw_body.decode("utf-8"),
                keep_blank_values=True,
                max_num_fields=64,
            )
        except (UnicodeDecodeError, ValueError):
            self._send(page("400", "<h1>Invalid form data</h1>", lang), 400)
            return
        self._send(result_page(form, lang))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Permit Bearings demo → http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
