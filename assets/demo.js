"use strict";

function detectActivePage() {
  const declared = document.body && document.body.dataset.page;
  if (["project", "readiness", "review", "evidence"].includes(declared))
    return declared;

  const present = [
    ["project", "intake"],
    ["readiness", "readinessOutput"],
    ["review", "scanBtn"],
    ["evidence", "ruleTable"],
  ].filter(([, id]) => document.getElementById(id));
  if (present.length > 1) return "all";
  return present.length === 1 ? present[0][0] : "none";
}

const ACTIVE_PAGE = detectActivePage();
const pageIs = page => ACTIVE_PAGE === "all" || ACTIVE_PAGE === page;

const STRINGS = {
  en: {
    tagline: "Find a candidate route. See the sources behind it. Take open questions to staff.",
    screenHeading: "About your project",
    translationScope: "The language choice applies to the applicant form and pathway results. The deadline tool and source records remain in English.",
    sampleLink: "Open a hypothetical detached ADU example",
    sampleSummary: "Made-up project facts run through the same screening logic as any other answers.",
    sampleLabel: "Example project.",
    sampleNotice: "These made-up Woodland ADU facts were screened with the same rules as your answers. They do not describe a real property.",
    sampleClear: "Clear the example and check another project",
    sampleEditedLabel: "Example changed.",
    sampleEditedNotice: "These answers no longer match the made-up Woodland example. The old results were cleared. Choose Check candidate pathways to calculate results from your answers.",
    sampleEditedClear: "Start over with a blank project check",
    resultCleared: "Your answers changed. The previous result was cleared. Choose Check candidate pathways to calculate a new result.",
    sampleUnavailableLabel: "Example unavailable.",
    sampleUnavailableNotice: "The example could not be loaded from its canonical test case. Continue with a blank form.",
    sampleUnavailableClear: "Continue with a blank project check",
    packetSampleTitle: "Continue with the made-up Woodland packet",
    packetSampleText: "See the same example compared with Woodland’s source-bound preapproved ADU checklist.",
    packetSampleLink: "Review the packet sample",
    juris: "Where is the property?",
    jurisPlaceholder: "Type any California city or county…",
    jurisHelp: "Choose a suggestion, or enter the exact city or county name.",
    statusLocal: "Confirm its source status in Evidence & updates.",
    statusBaseline: "The statewide candidate-rule set is available. No local requirements layer is encoded",
    statusUnknown: "Choose a recognized California city or county; screening will not run until it resolves.",
    jurisRequired: "Select a recognized California city or county before screening.",
    localCoverage: (count, total) => `${count} of ${total} have a jurisdiction-scoped record.`,
    hcdHistory: "Known HCD accountability letter",
    localMetadata: "Local source record available",
    scanned: "screened",
    scanRecord: (date, count) => `Ordinance screened ${date}: ${count} provision${count === 1 ? "" : "s"} flagged for review`,
    viewScan: "view scan findings (JSON)",
    letterCount: count => `${count} letter${count === 1 ? "" : "s"} on record.`,
    moreLetters: count => `and ${count} more`,
    project: "What are you proposing?",
    types: [["adu","Accessory dwelling unit (backyard cottage, garage conversion)"],
            ["jadu","Junior ADU (small unit inside my house)"],
            ["two_unit","Two homes on my single-family lot (SB 9)"],
            ["lot_split","Split my lot into two parcels (SB 9)"]],
    tri: [["yes","Yes"],["no","No"],["unknown","I'm not sure"]],
    primaryQuestion: "What dwelling exists on the lot now, or is proposed?",
    primaryHelp: "Choose what exists now separately from what is only proposed. Some review clocks depend on that difference.",
    questionIntro: "Choose “I'm not sure” when you do not know. The prototype will send uncertain material facts to staff instead of assuming they favor a path.",
    primaryOptions: [
      ["existing_single_family","An existing single-family home"],
      ["existing_multifamily","An existing multifamily building"],
      ["proposed_single_family","A single-family home is proposed; none exists now"],
      ["proposed_multifamily","A multifamily building is proposed; none exists now"],
      ["none","No primary dwelling exists or is proposed"],
      ["unknown","I'm not sure"],
    ],
    aduFormQuestion: "What kind of ADU work are you planning?",
    aduFormOptions: [
      ["new_detached","Build a new detached ADU"],
      ["new_attached","Build a new attached ADU"],
      ["conversion","Convert space in an existing structure"],
      ["same_footprint_rebuild","Replace a structure in the same location and dimensions"],
      ["unknown","I'm not sure"],
    ],
    unpermittedQuestions: {
      adu: "Are you trying to legalize an ADU built without permits before January 1, 2020?",
      jadu: "Are you trying to legalize a junior ADU built without permits before January 1, 2020?",
    },
    questions: {
      in_urbanized_area: "Is the property inside an incorporated city or another SB 9-qualifying urban area?",
      sf_zone: "Is the property zoned for single-family residential use?",
      demolishes_protected_housing: "Would the project demolish or alter rent-restricted, price-controlled, or deed-restricted affordable housing?",
      tenant_occupied_last_3_years: "Has a tenant lived in housing the project would demolish or alter during the last three years?",
      ellis_withdrawal_last_15_years: "Was housing on the property withdrawn from rental use under the Ellis Act during the last 15 years?",
      two_unit_contributing_historic_location: "Would the two-home project be located in a contributing structure in a state-listed historic district, or in a historic property or district protected by a city or county ordinance?",
      two_unit_individually_listed_historic_property: "Is the parcel individually listed in the State Historic Resources Inventory, or is the property individually designated or listed as a city or county landmark?",
      lot_split_on_historic_landmark_site: "Is the parcel within a historical landmark property in the State Historic Resources Inventory, or on a site designated or listed as a city or county landmark?",
      lot_split_alters_historic_district_resource: "Would the lot split require demolition or alteration of a contributing structure or an existing exterior structural wall in a historic district listed by California or designated by a city or county?",
      on_protected_site: "Does the property have a wetland, hazardous-land, conservation, habitat, or other protected-site condition named in SB 9?",
      parcel_created_by_sb9_split: "Was this parcel already created by an SB 9 lot split?",
      adjacent_sb9_split_same_actor: "Has the same owner, or someone working with that owner, used SB 9 to split an adjacent parcel?",
      proposed_lot_ratio_compliant: "Would each proposed parcel contain at least 40% of the original lot area?",
      proposed_lot_size_compliant: "Would both new lots be at least 1,200 square feet, or meet a smaller minimum verified in a current local ordinance?",
    },
    submit: "Check candidate pathways",
    results: "Your result",
    resultIntro: "This is not a complete list of requirements or a decision that the project qualifies. We did not verify the property facts or approve the project.",
    routeOrientation: "The open path is shown first for orientation. The prototype did not rank or recommend it.",
    resultCount: count => count === 1 ? "1 result found." : `${count} results found.`,
    answersHeading: "Answers used for this result",
    sampleAnswersHeading: "Sample answers used for this result",
    answersIntro: "We used these answers to compare the project with the limited rules in this prototype. We did not check them against parcel, zoning, or agency records.",
    sampleAnswersIntro: "These answers are made up and do not describe a real property.",
    jurisdictionFact: "Jurisdiction selected",
    projectFact: "Project",
    editAnswers: "Edit these answers",
    resultSummary: parts => `Based on these answers, this prototype shows ${parts}.`,
    groupCounts: {
      route: count => `${count} possible permit path${count === 1 ? "" : "s"}`,
      standard: count => `${count} other rule${count === 1 ? "" : "s"} that may apply`,
      local_process: count => `${count} local information record${count === 1 ? "" : "s"}`,
      other: count => `${count} other matching record${count === 1 ? "" : "s"}`,
    },
    resultNavLabel: "Result sections",
    onThisPage: "In this result",
    localBoundary: "This is supporting local information. It is not a complete local code, application checklist, or eligibility decision.",
    none: "The included rules do not identify a possible path from these answers. This does not mean the project is impossible. Ask the local planning counter to review it.",
    supportingOnly: "Supporting local information is shown below, but it is not a candidate permit path.",
    unknownHeading: "Staff review is needed before showing a possible path",
    unknownIntro: "You chose “I'm not sure” for a fact that can change the result. Confirm these items with the local planning counter:",
    explanationBanner: "The explanation text is an AI-assisted draft and has not been reviewed by a person. A source date only tells you when evidence was recorded. It does not mean a person, counsel, or jurisdiction approved the explanation.",
    dataLoadError: "The demo data did not load. Keep the data and assets folders beside these HTML pages, or serve the repository over HTTP. Pathway and ordinance controls stay disabled until the data is available.",
    groups: {
      route: "Possible permit paths",
      standard: "Rules that may apply",
      local_process: "Local information",
      other: "Other matching rules",
    },
    means: "What this result means",
    next: "What you can do next",
    confirm: "Questions to ask staff",
    docs: "Typical document hints",
    source: "Source",
    evidence: "Why we're saying this",
    evidenceUnavailable: "No supporting excerpt is recorded for this non-current source record.",
    copyRecord: "Explanation details",
    aiDraft: "Draft explanation · made with AI · not reviewed by a person",
    translationDraft: "Spanish draft · made with AI · not reviewed for accuracy",
    unavailable: "This explanation is not available. The matching rule and source are still shown.",
    withheldUnverified: "We are not showing next steps because this source has no date on file. Ask staff to confirm the source before you rely on it.",
    withheldStale: "We are not showing next steps because the source needs a new check. Confirm it before you rely on it.",
    nextScope: "These are starting points, not a complete checklist. Ask local staff what your project needs.",
    englishOnly: "English explanation shown because no valid Spanish draft is available.",
    showDetails: "Show explanation, next steps, and evidence",
    hideDetails: "Hide explanation, next steps, and evidence",
    showEvidence: "Show source evidence",
    hideEvidence: "Hide source evidence",
    checkDates: "Check ADU review dates",
    simulationApplied: count => `${count} guidance record${count === 1 ? " was" : "s were"} marked stale by the source-change rehearsal.`,
    simulationReset: count => `The source-change rehearsal was reset. ${count} guidance record${count === 1 ? "" : "s"} again show${count === 1 ? "s" : ""} the recorded source status.`,
    verifiedOn: date => `Source evidence on file: ${date}`,
    stale: "Source evidence needs a new check",
    unverified: "No source evidence date on file",
    langBtn: "Español",
  },
  es: {
    tagline: "Encuentre una posible ruta. Vea las fuentes que la respaldan. Consulte las preguntas pendientes con el personal de la agencia.",
    screenHeading: "Acerca de su proyecto",
    translationScope: "El idioma elegido se aplica al formulario y a los resultados para solicitantes. La herramienta de plazos y los registros de fuentes permanecen en inglés.",
    sampleLink: "Abrir un ejemplo hipotético de una ADU separada",
    sampleSummary: "Los datos inventados del proyecto pasan por la misma lógica de evaluación que cualquier otra respuesta.",
    sampleLabel: "Proyecto de ejemplo.",
    sampleNotice: "Estos datos inventados para una ADU en Woodland se evaluaron con las mismas reglas que sus respuestas. No describen una propiedad real.",
    sampleClear: "Borrar el ejemplo y revisar otro proyecto",
    sampleEditedLabel: "El ejemplo cambió.",
    sampleEditedNotice: "Estas respuestas ya no coinciden con el ejemplo inventado de Woodland. Se borraron los resultados anteriores. Elija Revisar posibles vías para calcular resultados con sus respuestas.",
    sampleEditedClear: "Empezar de nuevo con un formulario en blanco",
    resultCleared: "Sus respuestas cambiaron. Se borró el resultado anterior. Elija Revisar posibles vías para calcular un resultado nuevo.",
    sampleUnavailableLabel: "El ejemplo no está disponible.",
    sampleUnavailableNotice: "No se pudo cargar el ejemplo desde su caso de prueba canónico. Continúe con un formulario en blanco.",
    sampleUnavailableClear: "Continuar con un formulario en blanco",
    packetSampleTitle: "Continúe con el paquete ficticio de Woodland",
    packetSampleText: "Vea el mismo ejemplo comparado con la lista de verificación de ADU preaprobada de Woodland.",
    packetSampleLink: "Revisar la muestra del paquete en inglés",
    juris: "¿Dónde está la propiedad?",
    jurisPlaceholder: "Escriba cualquier ciudad o condado de California…",
    jurisHelp: "Elija una sugerencia o escriba el nombre exacto de la ciudad o el condado.",
    statusLocal: "Confirme el estado de su fuente en Evidencia y actualizaciones.",
    statusBaseline: "El conjunto estatal de reglas posibles está disponible. Aún no se codifican los requisitos locales",
    statusUnknown: "Elija una ciudad o condado reconocido de California; no se ejecutará la evaluación hasta resolverlo.",
    jurisRequired: "Seleccione una ciudad o condado reconocido de California antes de continuar.",
    localCoverage: (count, total) => `${count} de ${total} tienen un registro específico de la jurisdicción.`,
    hcdHistory: "Carta de responsabilidad de HCD conocida",
    localMetadata: "Registro de fuente local disponible",
    scanned: "evaluada",
    scanRecord: (date, count) => `Ordenanza evaluada el ${date}: ${count} disposición${count === 1 ? "" : "es"} señalada${count === 1 ? "" : "s"} para revisión`,
    viewScan: "ver los resultados de la evaluación (JSON)",
    letterCount: count => `${count} carta${count === 1 ? "" : "s"} registrada${count === 1 ? "" : "s"}.`,
    moreLetters: count => `y ${count} más`,
    project: "¿Qué propone construir?",
    types: [["adu","Vivienda accesoria (casita de patio, conversión de garaje)"],
            ["jadu","ADU júnior (unidad pequeña dentro de mi casa)"],
            ["two_unit","Dos viviendas en mi lote unifamiliar (SB 9)"],
            ["lot_split","Dividir mi lote en dos parcelas (SB 9)"]],
    tri: [["yes","Sí"],["no","No"],["unknown","No lo sé"]],
    primaryQuestion: "¿Qué vivienda existe ahora en el lote o está propuesta?",
    primaryHelp: "Distinga lo que ya existe de lo que solo está propuesto. Algunos plazos dependen de esa diferencia.",
    questionIntro: "Elija “No lo sé” si no conoce la respuesta. El prototipo enviará los datos materiales inciertos al personal en lugar de suponer que favorecen una vía.",
    primaryOptions: [
      ["existing_single_family","Ya existe una vivienda unifamiliar"],
      ["existing_multifamily","Ya existe un edificio multifamiliar"],
      ["proposed_single_family","Se propone una vivienda unifamiliar; aún no existe"],
      ["proposed_multifamily","Se propone un edificio multifamiliar; aún no existe"],
      ["none","No existe ni se propone una vivienda principal"],
      ["unknown","No lo sé"],
    ],
    aduFormQuestion: "¿Qué tipo de trabajo de ADU propone?",
    aduFormOptions: [
      ["new_detached","Construir una ADU nueva y separada"],
      ["new_attached","Construir una ADU nueva y adosada"],
      ["conversion","Convertir espacio dentro de una estructura existente"],
      ["same_footprint_rebuild","Reemplazar una estructura en el mismo lugar y con las mismas dimensiones"],
      ["unknown","No lo sé"],
    ],
    unpermittedQuestions: {
      adu: "¿Quiere legalizar una ADU construida sin permisos antes del 1 de enero de 2020?",
      jadu: "¿Quiere legalizar una ADU júnior construida sin permisos antes del 1 de enero de 2020?",
    },
    questions: {
      in_urbanized_area: "¿Está la propiedad dentro de una ciudad incorporada u otra área urbana que califique para la SB 9?",
      sf_zone: "¿Tiene la propiedad zonificación residencial unifamiliar?",
      demolishes_protected_housing: "¿El proyecto demolería o alteraría vivienda con renta o precio controlado, o vivienda asequible restringida por escritura?",
      tenant_occupied_last_3_years: "¿Un inquilino vivió durante los últimos tres años en una vivienda que el proyecto demolería o alteraría?",
      ellis_withdrawal_last_15_years: "¿Se retiró del mercado de alquiler alguna vivienda de la propiedad conforme a la Ley Ellis durante los últimos 15 años?",
      two_unit_contributing_historic_location: "¿Estaría el proyecto de dos viviendas en una estructura que contribuye al valor de un distrito histórico incluido por el estado, o en una propiedad o distrito histórico protegido por una ordenanza local?",
      two_unit_individually_listed_historic_property: "¿Está la parcela incluida individualmente en el inventario estatal de recursos históricos, o está la propiedad designada individualmente como monumento histórico por la ciudad o el condado?",
      lot_split_on_historic_landmark_site: "¿Está la parcela dentro de una propiedad incluida en el inventario estatal de recursos históricos, o en un sitio designado como monumento histórico por la ciudad o el condado?",
      lot_split_alters_historic_district_resource: "¿La división del lote exigiría demoler o alterar una estructura que contribuye a un distrito histórico, o un muro estructural exterior existente, dentro de un distrito histórico incluido por el estado o designado localmente?",
      on_protected_site: "¿Tiene la propiedad humedales, suelo peligroso, terreno de conservación, hábitat u otra condición de sitio protegido indicada en la SB 9?",
      parcel_created_by_sb9_split: "¿Esta parcela ya fue creada mediante una división de lote SB 9?",
      adjacent_sb9_split_same_actor: "¿El mismo propietario, o alguien que actúe con ese propietario, usó la SB 9 para dividir una parcela adyacente?",
      proposed_lot_ratio_compliant: "¿Cada parcela propuesta tendría al menos el 40% del área del lote original?",
      proposed_lot_size_compliant: "¿Tendrían ambos lotes nuevos al menos 1,200 pies cuadrados, o cumplirían un mínimo menor verificado en una ordenanza local vigente?",
    },
    submit: "Revisar posibles vías",
    results: "Su resultado",
    resultIntro: "Esta no es una lista completa de requisitos ni una decisión de que el proyecto cumple los requisitos. No verificamos los datos de la propiedad ni aprobamos el proyecto.",
    routeOrientation: "La vía abierta aparece primero para orientar. El prototipo no la clasificó ni la recomendó.",
    resultCount: count => count === 1 ? "Se encontró 1 resultado." : `Se encontraron ${count} resultados.`,
    answersHeading: "Respuestas usadas para este resultado",
    sampleAnswersHeading: "Respuestas de ejemplo usadas para este resultado",
    answersIntro: "Usamos estas respuestas para comparar el proyecto con las reglas limitadas de este prototipo. No las verificamos con registros de parcelas, zonificación o de la agencia.",
    sampleAnswersIntro: "Estas respuestas son inventadas y no describen una propiedad real.",
    jurisdictionFact: "Jurisdicción seleccionada",
    projectFact: "Proyecto",
    editAnswers: "Editar estas respuestas",
    resultSummary: parts => `Según estas respuestas, este prototipo muestra ${parts}.`,
    groupCounts: {
      route: count => `${count} posible${count === 1 ? "" : "s"} vía${count === 1 ? "" : "s"} de permiso`,
      standard: count => `${count} regla${count === 1 ? "" : "s"} adicional${count === 1 ? "" : "es"} que podría${count === 1 ? "" : "n"} aplicarse`,
      local_process: count => `${count} registro${count === 1 ? "" : "s"} de información local`,
      other: count => `${count} registro${count === 1 ? "" : "s"} coincidente${count === 1 ? "" : "s"} adicional${count === 1 ? "" : "es"}`,
    },
    resultNavLabel: "Secciones del resultado",
    onThisPage: "En este resultado",
    localBoundary: "Esta es información local de apoyo. No es un código local completo, una lista de documentos para la solicitud ni una decisión de elegibilidad.",
    none: "Las reglas incluidas no identifican una posible vía con estas respuestas. Esto no significa que el proyecto sea imposible. Pida una revisión en el departamento local de planificación.",
    supportingOnly: "Abajo se muestra información local de apoyo, pero no es una posible vía de permiso.",
    unknownHeading: "Se necesita revisión del personal antes de mostrar una posible vía",
    unknownIntro: "Eligió “No lo sé” para un dato que puede cambiar el resultado. Confirme estos puntos con el departamento local de planificación:",
    explanationBanner: "El texto de la explicación es un borrador creado con ayuda de IA y no ha sido revisado por una persona. El texto en español es una traducción automática sin revisión de exactitud. Una fecha de fuente solo indica cuándo se registró la evidencia. No significa que una persona, un abogado o la jurisdicción haya aprobado la explicación.",
    dataLoadError: "No se pudieron cargar los datos de la demostración. Mantenga las carpetas data y assets junto a estas páginas HTML o sirva el repositorio por HTTP. Los controles de vías y ordenanzas permanecerán desactivados hasta que los datos estén disponibles.",
    groups: {
      route: "Posibles vías de permiso",
      standard: "Reglas que podrían aplicarse",
      local_process: "Información local",
      other: "Otras reglas coincidentes",
    },
    means: "Qué significa este resultado",
    next: "Qué puede hacer ahora",
    confirm: "Preguntas para el personal",
    docs: "Sugerencias de documentos típicos",
    source: "Fuente",
    evidence: "Por qué decimos esto",
    evidenceUnavailable: "No hay un extracto de respaldo registrado para este registro de fuente no vigente.",
    copyRecord: "Detalles de la explicación",
    aiDraft: "Borrador de explicación · creado con IA · no revisado por una persona",
    translationDraft: "Borrador en español · creado con IA · no revisado para comprobar su exactitud",
    unavailable: "Esta explicación no está disponible. Aun así se muestran la regla coincidente y la fuente.",
    withheldUnverified: "No mostramos los próximos pasos porque esta fuente no tiene una fecha registrada. Pida al personal que confirme la fuente antes de usarla.",
    withheldStale: "No mostramos los próximos pasos porque la fuente necesita una nueva comprobación. Confírmela antes de usarla.",
    nextScope: "Estos son puntos de partida, no una lista completa. Pregunte al personal local qué necesita su proyecto.",
    englishOnly: "Se muestra la explicación en inglés porque no hay un borrador válido en español.",
    showDetails: "Mostrar explicación, próximos pasos y evidencia",
    hideDetails: "Ocultar explicación, próximos pasos y evidencia",
    showEvidence: "Mostrar evidencia de la fuente",
    hideEvidence: "Ocultar evidencia de la fuente",
    checkDates: "Revisar los plazos de la ADU (en inglés)",
    simulationApplied: count => `El ensayo del cambio de fuente marcó como desactualizado${count === 1 ? "" : "s"} ${count} registro${count === 1 ? "" : "s"} de orientación.`,
    simulationReset: count => `Se restableció el ensayo del cambio de fuente. ${count} registro${count === 1 ? "" : "s"} de orientación vuelve${count === 1 ? "" : "n"} a mostrar el estado de fuente registrado.`,
    verifiedOn: date => `Evidencia de la fuente registrada: ${date}`,
    stale: "La evidencia de la fuente necesita una nueva comprobación",
    unverified: "No hay fecha de evidencia de la fuente",
    langBtn: "English",
  },
};
let lang = "en";
let RULES = [], GOLDEN = [], SOURCES = {}, CHECKS = [], JURIS = [], LETTERS = {}, SCANS = {};
let EXPLANATIONS = new Map();
let READINESS = null;
let jurisByName = new Map();
let intakeDraft = {};
const SAMPLE_ORDINANCE =
  "Accessory dwelling units shall not exceed sixteen (16) feet in height if " +
  "the dwelling unit does not comply with the setback limitations for a " +
  "single-family residence, prescribed by the applicable zoning district. " +
  "Detached accessory dwelling units exceeding sixteen (16) feet in height " +
  "shall incorporate a hip, gable, or other similar styled roof design.";
function isJsonNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function isRuleInteger(value) {
  return typeof value === "number" && Number.isSafeInteger(value);
}

function isJsonScalar(value) {
  return typeof value === "string"
    || typeof value === "boolean"
    || isRuleInteger(value);
}

const RULE_KEYS = [
  "rule_id", "pathway", "route_class", "jurisdiction_scope", "criteria",
  "citation", "source_dependencies", "display_group", "required_documents",
  "notes",
];
const CITATION_KEYS = [
  "source", "url", "excerpt", "excerpt_sha256", "verified_on",
];
const CITATION_REQUIRED_KEYS = ["source", "url", "excerpt", "verified_on"];
const CRITERION_KEYS = ["field", "op", "value"];

function hasExactKeys(value, allowed, required) {
  if (!value || typeof value !== "object" || Array.isArray(value))
    return false;
  const keys = Object.keys(value);
  return keys.every(key => allowed.includes(key))
    && required.every(key =>
      Object.prototype.hasOwnProperty.call(value, key)
    );
}

function sameScalar(left, right) {
  if (isJsonNumber(left) && isJsonNumber(right)) return left === right;
  return typeof left === typeof right && left === right;
}

const OPS = {
  eq: (actual, expected) =>
    actual != null && sameScalar(actual, expected),
  lte: (actual, expected) =>
    isJsonNumber(actual) && isJsonNumber(expected) && actual <= expected,
  gte: (actual, expected) =>
    isJsonNumber(actual) && isJsonNumber(expected) && actual >= expected,
  in: (actual, expected) =>
    actual != null && Array.isArray(expected)
      && expected.some(candidate => sameScalar(actual, candidate)),
};
const MAX_AGE_DAYS = 180;

function validCriterion(criterion) {
  if (!hasExactKeys(criterion, CRITERION_KEYS, CRITERION_KEYS)
      || !nonBlank(criterion.field)
      || !/^[a-z][a-z0-9_]*$/.test(criterion.field)
      || !Object.prototype.hasOwnProperty.call(OPS, criterion.op)) return false;
  const expected = criterion.value;
  if (criterion.op === "eq")
    return isJsonScalar(expected)
      && !(typeof expected === "string" && !expected.trim());
  if (criterion.op === "in") {
    if (!Array.isArray(expected) || !expected.length
        || !expected.every(isJsonScalar)
        || expected.some(value =>
          typeof value === "string" && !value.trim()
        )) return false;
    const firstType = typeof expected[0];
    return expected.every(value => typeof value === firstType)
      && expected.every((value, index) =>
        !expected.slice(0, index).some(prior =>
          sameScalar(value, prior)
        )
      );
  }
  return isRuleInteger(expected);
}

function matches(rule, intake) {
  return Array.isArray(rule.criteria)
    && rule.criteria.length > 0
    && rule.criteria.every(criterion =>
      validCriterion(criterion)
      && OPS[criterion.op](intake[criterion.field], criterion.value)
    );
}
function screen(intake) {
  return RULES.filter(r =>
    (r.jurisdiction_scope === "statewide" || r.jurisdiction_scope === intake.jurisdiction)
    && matches(r, intake));
}
function ruleStatus(rule, changedSourceIds) {
  const c = rule.citation;
  const dependencies = Array.isArray(rule.source_dependencies)
    ? rule.source_dependencies : [];
  if (changedSourceIds.some(sourceId => dependencies.includes(sourceId)))
    return "stale";
  if (!validIsoDate(c.verified_on)) return "unverified";
  const now = new Date();
  const todayUtc = Date.UTC(
    now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()
  );
  const verifiedUtc = Date.parse(`${c.verified_on}T00:00:00Z`);
  const age = Math.floor((todayUtc - verifiedUtc) / 86400000);
  return age < 0 || age > MAX_AGE_DAYS ? "stale" : "verified";
}

function uiText(value) {
  return String(value ?? "").replace(/\s*\u2014\s*/g, " ");
}

function escapeHtml(value) {
  const element = document.createElement("span");
  element.textContent = value ?? "";
  return element.innerHTML;
}

function esc(value) {
  return escapeHtml(uiText(value));
}

function escVerbatim(value) {
  return escapeHtml(value);
}

function safeExternalUrl(value) {
  try {
    const parsed = new URL(String(value));
    return ["https:", "http:"].includes(parsed.protocol) ? parsed.href : null;
  } catch {
    return null;
  }
}

function safeLocalJsonPath(slug) {
  return /^[a-z0-9-]+$/.test(slug || "")
    ? `data/conformance/results/${slug}.json` : null;
}

function nonBlank(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function validIsoDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime())
    && parsed.toISOString().slice(0, 10) === value;
}

function dateIsNotFuture(value) {
  if (!validIsoDate(value)) return false;
  const now = new Date();
  const todayUtc = Date.UTC(
    now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()
  );
  return Date.parse(`${value}T00:00:00Z`) <= todayUtc;
}

function validStableId(value) {
  return typeof value === "string"
    && /^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)*$/.test(value);
}

function validHttpsUrl(value) {
  try {
    const parsed = new URL(String(value));
    return parsed.protocol === "https:"
      && Boolean(parsed.hostname)
      && !parsed.username
      && !parsed.password;
  } catch {
    return false;
  }
}

function validRuleRecord(rule) {
  if (!hasExactKeys(rule, RULE_KEYS, RULE_KEYS)
      || !validStableId(rule.rule_id)
      || !nonBlank(rule.pathway)
      || !["ministerial", "discretionary", "mixed"].includes(rule.route_class)
      || !validStableId(rule.jurisdiction_scope)
      || !["route", "standard", "local_process"].includes(rule.display_group)
      || !Array.isArray(rule.criteria) || !rule.criteria.length
      || !rule.criteria.every(validCriterion)
      || !Array.isArray(rule.source_dependencies)
      || !rule.source_dependencies.length
      || !rule.source_dependencies.every(validStableId)
      || new Set(rule.source_dependencies).size
         !== rule.source_dependencies.length
      || !Array.isArray(rule.required_documents)
      || !rule.required_documents.every(nonBlank)
      || new Set(rule.required_documents).size
         !== rule.required_documents.length
      || !nonBlank(rule.notes)) return false;
  const citation = rule.citation;
  return hasExactKeys(
    citation, CITATION_KEYS, CITATION_REQUIRED_KEYS
  )
    && nonBlank(citation.source)
    && nonBlank(citation.url)
    && validHttpsUrl(citation.url)
    && (citation.excerpt == null || nonBlank(citation.excerpt))
    && (
      citation.excerpt_sha256 == null
      || /^(?:sha256:)?[0-9a-f]{64}$/.test(citation.excerpt_sha256)
    )
    && (
      citation.verified_on == null
      || dateIsNotFuture(citation.verified_on)
    )
    && !(citation.verified_on && !citation.excerpt);
}

function normalizeRules(records) {
  if (!Array.isArray(records) || !records.length
      || !records.every(validRuleRecord)) {
    throw new Error("rule data failed validation");
  }
  const ids = records.map(rule => rule.rule_id);
  if (new Set(ids).size !== ids.length)
    throw new Error("rule data contains duplicate IDs");
  return records;
}

function validTextList(value) {
  return Array.isArray(value) && value.length > 0 && value.every(nonBlank);
}

function validHighlights(value) {
  return value == null || (
    typeof value === "object"
    && nonBlank(value.title)
    && Array.isArray(value.items)
    && value.items.length > 0
    && value.items.every(item => item && typeof item === "object"
      && nonBlank(item.label) && nonBlank(item.text))
  );
}

async function validReview(review, version, updatedOn, englishCopy) {
  if (!review || typeof review !== "object") return false;
  const allowed = ["prototype_review_pending", "human_reviewed",
                   "jurisdiction_approved"];
  if (!allowed.includes(review.status)) return false;
  const metadata = [review.reviewer, review.reviewed_on, review.method,
                    review.reviewed_version, review.content_fingerprint];
  if (review.status === "prototype_review_pending")
    return metadata.every(value => value == null);
  if (!(metadata.every(nonBlank)
      && dateIsNotFuture(review.reviewed_on)
      && review.reviewed_on >= updatedOn
      && review.reviewed_version === version)) return false;
  try {
    const expected = await localizedContentFingerprint(
      version, "en", englishCopy
    );
    return nonBlank(expected) && review.content_fingerprint === expected;
  } catch {
    return false;
  }
}

function validLocalizedCopy(copy, language) {
  if (!copy || typeof copy !== "object"
      || !nonBlank(copy.title)
      || !nonBlank(copy.summary)
      || !validTextList(copy.next_steps)
      || !validTextList(copy.confirm_with_staff)
      || !validHighlights(copy.highlights)) return false;
  if (language !== "es") return true;
  const allowed = ["machine_draft", "human_reviewed", "jurisdiction_approved"];
  if (!allowed.includes(copy.translation_status)) return false;
  const metadata = [copy.reviewer, copy.reviewed_on, copy.method,
                    copy.reviewed_version, copy.content_fingerprint];
  if (copy.translation_status === "machine_draft")
    return metadata.every(value => value == null);
  return metadata.every(nonBlank);
}

function stableJson(value) {
  if (Array.isArray(value))
    return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object")
    return `{${Object.keys(value).sort().map(key =>
      `${JSON.stringify(key)}:${stableJson(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

async function sha256Fingerprint(value) {
  if (!globalThis.crypto || !globalThis.crypto.subtle) return null;
  const normalized = stableJson(value);
  const digest = await globalThis.crypto.subtle.digest(
    "SHA-256", new TextEncoder().encode(normalized)
  );
  return "sha256:" + Array.from(new Uint8Array(digest))
    .map(byte => byte.toString(16).padStart(2, "0")).join("");
}

async function localizedContentFingerprint(version, language, copy) {
  return sha256Fingerprint({
    confirm_with_staff: copy.confirm_with_staff,
    highlights: copy.highlights ?? null,
    language,
    next_steps: copy.next_steps,
    summary: copy.summary,
    title: copy.title,
    version,
  });
}

async function validTranslationReview(copy, version, updatedOn) {
  if (!validLocalizedCopy(copy, "es")) return false;
  if (copy.translation_status === "machine_draft") return true;
  if (!dateIsNotFuture(copy.reviewed_on)
      || copy.reviewed_on < updatedOn
      || copy.reviewed_version !== version) return false;
  try {
    const expected = await localizedContentFingerprint(version, "es", copy);
    return nonBlank(expected) && copy.content_fingerprint === expected;
  } catch {
    return false;
  }
}

function normalizedCitation(rule) {
  const citation = rule.citation || {};
  return {
    excerpt: citation.excerpt ?? null,
    excerpt_sha256: citation.excerpt_sha256 ?? null,
    source: citation.source,
    url: citation.url,
    verified_on: citation.verified_on ?? null,
  };
}

async function citationFingerprint(rule) {
  return sha256Fingerprint(normalizedCitation(rule));
}

async function ruleFingerprint(rule) {
  return sha256Fingerprint({
    citation: normalizedCitation(rule),
    criteria: rule.criteria,
    display_group: rule.display_group,
    jurisdiction_scope: rule.jurisdiction_scope,
    notes: rule.notes,
    pathway: rule.pathway,
    required_documents: rule.required_documents,
    route_class: rule.route_class,
    rule_id: rule.rule_id,
    source_dependencies: rule.source_dependencies,
  });
}

async function normalizeExplanations(payload, rules) {
  if (!payload || payload.schema_version !== 1
      || !Array.isArray(payload.entries)) return new Map();
  if (!globalThis.crypto || !globalThis.crypto.subtle) return new Map();
  const rulesById = new Map(rules.map(rule => [rule.rule_id, rule]));
  if (rulesById.size !== rules.length) return new Map();
  const normalized = new Map();
  const seen = new Set();
  const blocked = new Set();
  for (const record of payload.entries) {
    const ruleId = record && record.source_rule_id;
    if (!nonBlank(ruleId)) continue;
    if (seen.has(ruleId)) {
      normalized.delete(ruleId);
      blocked.add(ruleId);
      continue;
    }
    seen.add(ruleId);
    if (blocked.has(ruleId)) continue;
    const rule = rulesById.get(ruleId);
    const version = record.version;
    const updatedOn = record.updated_on;
    if (!rule || !/^\d+\.\d+\.\d+$/.test(version || "")
        || !dateIsNotFuture(updatedOn)
        || record.display_group !== rule.display_group
        || record.drafted_by !== "ai_assisted"
        || (record.source_verified_on ?? null)
           !== (rule.citation.verified_on ?? null)
        || (record.source_verified_on
            && !dateIsNotFuture(record.source_verified_on))
        || (record.source_verified_on
            && updatedOn < record.source_verified_on)
        || !validLocalizedCopy(record.en, "en")
        || !(await validReview(
          record.review, version, updatedOn, record.en
        ))) continue;
    let expectedFingerprint;
    let expectedRuleFingerprint;
    try {
      expectedFingerprint = await citationFingerprint(rule);
      expectedRuleFingerprint = await ruleFingerprint(rule);
    } catch {
      return new Map();
    }
    if (!nonBlank(record.citation_fingerprint)
        || !nonBlank(record.rule_fingerprint)
        || !expectedFingerprint
        || !expectedRuleFingerprint
        || record.citation_fingerprint !== expectedFingerprint
        || record.rule_fingerprint !== expectedRuleFingerprint) continue;
    normalized.set(ruleId, {
      ...record,
      es: await validTranslationReview(record.es, version, updatedOn)
        ? record.es : null,
    });
  }
  return normalized;
}

const SB9_BASE_FIELDS = [
  "in_urbanized_area",
  "sf_zone",
  "demolishes_protected_housing",
  "tenant_occupied_last_3_years",
  "ellis_withdrawal_last_15_years",
  "on_protected_site",
];
const SB9_TWO_UNIT_FIELDS = [
  "two_unit_contributing_historic_location",
  "two_unit_individually_listed_historic_property",
];
const SB9_LOT_SPLIT_FIELDS = [
  "lot_split_on_historic_landmark_site",
  "lot_split_alters_historic_district_resource",
  "parcel_created_by_sb9_split",
  "adjacent_sb9_split_same_actor",
  "proposed_lot_ratio_compliant",
  "proposed_lot_size_compliant",
];
const RESULT_GROUPS = ["route", "standard", "local_process", "other"];
const INITIAL_OPEN_ROUTE_BY_PROJECT = Object.freeze({
  adu: "adu-ministerial-review",
  jadu: "jadu-ministerial-review",
  two_unit: "sb9-two-unit-ministerial",
  lot_split: "sb9-urban-lot-split",
});

function radioQuestion(name, legend, options, help = "") {
  const helpId = `${name}-help`;
  const describedBy = help ? ` aria-describedby="${helpId}"` : "";
  return `<fieldset data-question="${esc(name)}"${describedBy}>
    <legend>${esc(legend)}</legend>
    ${help ? `<p class="small question-help" id="${helpId}">${esc(help)}</p>` : ""}
    <div class="choice-grid">
      ${options.map(([value, label]) =>
        `<label><input type="radio" name="${esc(name)}"
          value="${esc(value)}" required> ${esc(label)}</label>`
      ).join("")}
    </div>
  </fieldset>`;
}

function fieldsForProject(projectType) {
  if (projectType === "adu")
    return ["primary_dwelling_status", "adu_project_form",
            "unpermitted_existing"];
  if (projectType === "jadu")
    return ["primary_dwelling_status", "unpermitted_existing"];
  if (projectType === "two_unit")
    return [...SB9_BASE_FIELDS, ...SB9_TWO_UNIT_FIELDS];
  if (projectType === "lot_split")
    return [...SB9_BASE_FIELDS, ...SB9_LOT_SPLIT_FIELDS];
  return [];
}

const PROJECT_SAMPLE_CASE_IDS = Object.freeze({
  adu: "woodland-new-detached-adu-local-layer",
});

function requestedProjectSampleId(searchParams) {
  if (!searchParams) return null;
  const requestedSamples = searchParams.getAll("sample");
  if (requestedSamples.length !== 1) return null;
  return Object.prototype.hasOwnProperty.call(
    PROJECT_SAMPLE_CASE_IDS,
    requestedSamples[0],
  ) ? requestedSamples[0] : null;
}

function prepareProjectSample(searchParams, golden, jurisdictions) {
  const requestedSampleId = requestedProjectSampleId(searchParams);
  if (!requestedSampleId) return null;
  const caseId = PROJECT_SAMPLE_CASE_IDS[requestedSampleId];
  if (!caseId || !Array.isArray(golden) || !Array.isArray(jurisdictions))
    return null;

  const matchingCases = golden.filter(
    item => item && item.case_id === caseId
  );
  if (matchingCases.length !== 1) return null;
  const intake = matchingCases[0].intake;
  if (!intake || typeof intake !== "object" || Array.isArray(intake))
    return null;

  const materialFields = fieldsForProject(intake.project_type);
  if (!materialFields.length) return null;
  const requiredFields = ["project_type", "jurisdiction", ...materialFields];
  if (Object.keys(intake).some(name => !requiredFields.includes(name)))
    return null;
  if (requiredFields.some(name =>
    !nonBlank(intake[name]) || intake[name] === "unknown"
  )) return null;

  const matchingJurisdictions = jurisdictions.filter(
    jurisdiction => jurisdiction && jurisdiction.slug === intake.jurisdiction
  );
  if (matchingJurisdictions.length !== 1) return null;
  return {
    caseId,
    intake: {...intake},
    jurisdiction: matchingJurisdictions[0],
  };
}

function renderProjectQuestions() {
  const s = STRINGS[lang];
  const projectType = intakeDraft.project_type || null;
  const container = document.getElementById("projectQuestions");
  if (!projectType) {
    container.hidden = true;
    container.innerHTML = "";
    return;
  }
  const fields = fieldsForProject(projectType);
  const questions = fields.map(name => {
    if (name === "primary_dwelling_status")
      return radioQuestion(name, s.primaryQuestion, s.primaryOptions, s.primaryHelp);
    if (name === "adu_project_form")
      return radioQuestion(name, s.aduFormQuestion, s.aduFormOptions);
    if (name === "unpermitted_existing")
      return radioQuestion(
        name,
        s.unpermittedQuestions[projectType],
        s.tri
      );
    return radioQuestion(name, s.questions[name], s.tri);
  }).join("");
  container.hidden = false;
  container.lang = lang;
  container.innerHTML = `<p class="small">${esc(s.questionIntro)}</p>${questions}`;
  for (const input of container.querySelectorAll("input[type=radio]")) {
    input.checked = intakeDraft[input.name] === input.value;
  }
}

function rememberIntakeValues() {
  const form = document.getElementById("intake");
  for (const [name, value] of new FormData(form).entries()) {
    if (name !== "jurisdiction_name") intakeDraft[name] = value;
  }
}

function renderForm() {
  const s = STRINGS[lang];
  const translatedIds = ["t-tagline", "translationScope", "screenHeading",
                         "t-juris", "jurisHelp", "t-project", "t-submit",
                         "typeRadios", "projectQuestions", "jurisStatus",
                         "resultStatus", "sampleLink", "sampleSummary",
                         "sampleLabel", "sampleNotice", "sampleClear"];
  translatedIds.forEach(id => { document.getElementById(id).lang = lang; });
  document.getElementById("t-tagline").textContent = s.tagline;
  document.getElementById("translationScope").textContent = s.translationScope;
  document.getElementById("sampleLink").textContent = s.sampleLink;
  document.getElementById("sampleSummary").textContent = s.sampleSummary;
  renderProjectSampleText();
  document.getElementById("screenHeading").textContent = s.screenHeading;
  document.getElementById("t-juris").textContent = s.juris;
  document.getElementById("jurisHelp").textContent = s.jurisHelp;
  document.getElementById("t-project").textContent = s.project;
  document.getElementById("t-submit").textContent = s.submit;
  document.getElementById("langToggle").textContent = s.langBtn;
  document.getElementById("langToggle").lang = lang === "en" ? "es" : "en";
  document.getElementById("jurisInput").placeholder = s.jurisPlaceholder;
  document.getElementById("jurisInput").lang = lang;
  renderJurisStatus();
  document.getElementById("typeRadios").innerHTML =
    s.types.map(([value, text]) =>
      `<label><input type="radio" name="project_type"
        value="${esc(value)}" required
        ${intakeDraft.project_type === value ? "checked" : ""}> ${esc(text)}</label>`
    ).join("");
  renderProjectQuestions();
}

function usableLocalizedExplanation(explanation) {
  if (!explanation || typeof explanation !== "object") return null;
  const preferred = lang === "es" ? explanation.es : explanation.en;
  const fallback = lang === "es" ? explanation.en : null;
  const localized = preferred || fallback;
  if (!localized || typeof localized.title !== "string"
      || typeof localized.summary !== "string"
      || !Array.isArray(localized.next_steps)
      || !localized.next_steps.every(item => typeof item === "string")
      || !Array.isArray(localized.confirm_with_staff)
      || !localized.confirm_with_staff.every(item => typeof item === "string")
      || !validHighlights(localized.highlights)
      || typeof explanation.source_rule_id !== "string"
      || typeof explanation.version !== "string"
      || typeof explanation.updated_on !== "string") return null;
  return {localized, copyLang: preferred ? lang : "en"};
}

function baseExplanationReviewLabel(explanation) {
  const s = STRINGS[lang];
  const review = explanation.review || {};
  if (review.status === "jurisdiction_approved") {
    return lang === "es"
      ? `Explicación aprobada por la jurisdicción · ${review.reviewer} · ${review.reviewed_on} · v${review.reviewed_version}`
      : `Jurisdiction-approved explanation · ${review.reviewer} · ${review.reviewed_on} · v${review.reviewed_version}`;
  }
  if (review.status === "human_reviewed") {
    return lang === "es"
      ? `Explicación revisada por una persona · ${review.reviewer} · ${review.reviewed_on} · v${review.reviewed_version}`
      : `Human-reviewed explanation · ${review.reviewer} · ${review.reviewed_on} · v${review.reviewed_version}`;
  }
  return s.aiDraft;
}

function explanationReviewLabels(explanation, localized, copyLang) {
  const s = STRINGS[lang];
  const labels = [baseExplanationReviewLabel(explanation)];
  if (lang !== "es") return labels;
  if (copyLang !== "es") return [...labels, s.englishOnly];
  if (localized.translation_status === "machine_draft")
    return [...labels, s.translationDraft];
  if (localized.translation_status === "jurisdiction_approved")
    return [...labels,
      `Traducción aprobada por la jurisdicción · ${localized.reviewer} · ${localized.reviewed_on} · v${localized.reviewed_version}`];
  return [...labels,
    `Traducción revisada por una persona · ${localized.reviewer} · ${localized.reviewed_on} · v${localized.reviewed_version}`];
}

function formatResultList(items) {
  if (items.length < 2) return items[0] || "";
  if (items.length === 2) return `${items[0]} ${lang === "es" ? "y" : "and"} ${items[1]}`;
  const conjunction = lang === "es" ? "y" : "and";
  const comma = lang === "es" ? " " : ", ";
  return `${items.slice(0, -1).join(", ")}${comma}${conjunction} ${items[items.length - 1]}`;
}

function formatSourceDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return value || "";
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(lang === "es" ? "es-US" : "en-US", {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
    year: "numeric",
  }).format(date);
}

function optionLabel(options, value) {
  return options.find(([candidate]) => candidate === value)?.[1] || value;
}

function factValueLabel(name, value, projectType) {
  const s = STRINGS[lang];
  if (name === "project_type") return optionLabel(s.types, value);
  if (name === "primary_dwelling_status")
    return optionLabel(s.primaryOptions, value);
  if (name === "adu_project_form")
    return optionLabel(s.aduFormOptions, value);
  return optionLabel(s.tri, value);
}

function resultGroup(rule) {
  const explanation = EXPLANATIONS.get(rule.rule_id);
  const candidate = rule.display_group || explanation?.display_group;
  return RESULT_GROUPS.includes(candidate) ? candidate : "other";
}

function groupResultRecords(list) {
  const grouped = new Map(RESULT_GROUPS.map(group => [group, []]));
  list.forEach(rule => grouped.get(resultGroup(rule)).push(rule));
  return grouped;
}

function resultSummaryText(grouped) {
  const s = STRINGS[lang];
  const parts = RESULT_GROUPS
    .map(group => [group, grouped.get(group).length])
    .filter(([, count]) => count > 0)
    .map(([group, count]) => s.groupCounts[group](count));
  return s.resultSummary(formatResultList(parts));
}

function renderProjectFacts() {
  if (!LAST_INTAKE || !LAST_JURISDICTION) return "";
  const s = STRINGS[lang];
  const projectType = LAST_INTAKE.project_type;
  const facts = [
    {
      name: "jurisdiction",
      label: s.jurisdictionFact,
      value: jurisDisplay(LAST_JURISDICTION),
    },
    {
      name: "project_type",
      label: s.projectFact,
      value: factValueLabel("project_type", projectType, projectType),
    },
    ...fieldsForProject(projectType).map(name => ({
      name,
      label: questionLabel(name, projectType),
      value: factValueLabel(name, LAST_INTAKE[name], projectType),
    })),
  ];
  const isSample = projectSampleState === "active";
  return `<section class="result-cover-sheet" aria-labelledby="projectFactsHeading"
      lang="${lang}">
    <div class="result-cover-heading">
      <h3 id="projectFactsHeading">
        ${esc(isSample ? s.sampleAnswersHeading : s.answersHeading)}
      </h3>
      <a class="edit-answers" href="#screenHeading">${esc(s.editAnswers)}</a>
    </div>
    <p class="small">${esc(isSample ? s.sampleAnswersIntro : s.answersIntro)}</p>
    <dl class="result-facts">
      ${facts.map(fact => `<div data-field="${esc(fact.name)}">
        <dt>${esc(fact.label)}</dt>
        <dd>${esc(fact.value)}</dd>
      </div>`).join("")}
    </dl>
  </section>`;
}

function renderResultIndex(grouped) {
  const s = STRINGS[lang];
  const links = RESULT_GROUPS
    .map(group => [group, grouped.get(group).length])
    .filter(([, count]) => count > 0)
    .map(([group, count]) =>
      `<li><a href="#result-group-${group}">${esc(s.groups[group])}
        <span aria-hidden="true">(${count})</span></a></li>`
    ).join("");
  return `<nav class="result-index" aria-label="${esc(s.resultNavLabel)}"
      lang="${lang}">
    <p>${esc(s.onThisPage)}</p>
    <ul>${links}</ul>
  </nav>`;
}

function renderResultCard(rule, explanation, options = {}) {
  const {suppressPendingReview = false} = options;
  const s = STRINGS[lang];
  const c = rule.citation;
  const safeId = String(rule.rule_id).replace(/[^A-Za-z0-9_-]/g, "-");
  const group = resultGroup(rule);
  const status = ruleStatus(
    rule, simulating ? ["ca-gov-66321"] : []
  );
  const ok = status === "verified";
  const badge = ok
    ? `<span class="badge info" lang="${lang}"><span class="status-ico" aria-hidden="true">◷</span>${esc(s.verifiedOn(formatSourceDate(c.verified_on)))}</span>`
    : status === "stale"
    ? `<span class="badge bad" lang="${lang}"><span class="status-ico" aria-hidden="true">✕</span>${esc(s.stale)}</span>`
    : `<span class="badge warn" lang="${lang}"><span class="status-ico" aria-hidden="true">⚠</span>${esc(s.unverified)}</span>`;
  const localizedRecord = ok ? usableLocalizedExplanation(explanation) : null;
  let consequence = status === "unverified"
    ? `<div class="notice small" lang="${lang}">${esc(s.withheldUnverified)}</div>`
    : status === "stale"
    ? `<div class="notice small" lang="${lang}">${esc(s.withheldStale)}</div>`
    : `<div class="notice small" lang="${lang}">${esc(s.unavailable)}</div>`;
  let guidance = "";
  let reviewNote = "";
  let copyRecord = "";
  let displayTitle = rule.pathway;
  let displayTitleLang = "en";
  if (localizedRecord) {
    const {localized, copyLang} = localizedRecord;
    displayTitle = localized.title;
    displayTitleLang = copyLang;
    const steps = localized.next_steps.map(step => `<li>${esc(step)}</li>`).join("");
    const confirmations = localized.confirm_with_staff.map(item => `<li>${esc(item)}</li>`).join("");
    const highlights = localized.highlights
      ? `<div class="key-points">
          <h5 lang="${copyLang}">${esc(localized.highlights.title)}</h5>
          <ul lang="${copyLang}">${localized.highlights.items.map(item =>
            `<li><strong>${esc(item.label)}:</strong> ${esc(item.text)}</li>`
          ).join("")}</ul>
        </div>`
      : "";
    consequence = `<p class="result-consequence"
      lang="${copyLang}">${esc(localized.summary)}</p>`;
    guidance = `<div class="plain-layer">
      ${highlights}
      <h5 lang="${lang}">${esc(s.next)}</h5>
      <p class="small" lang="${lang}">${esc(s.nextScope)}</p>
      <ol lang="${copyLang}">${steps}</ol>
      <div class="confirmation">
        <h5 lang="${lang}">${esc(s.confirm)}</h5>
        <ul lang="${copyLang}">${confirmations}</ul>
      </div>
    </div>`;
    const pendingOnly = explanation.review.status === "prototype_review_pending"
      && (lang !== "es"
        || (copyLang === "es" && localized.translation_status === "machine_draft"));
    if (!(suppressPendingReview && pendingOnly)) {
      reviewNote = explanationReviewLabels(explanation, localized, copyLang)
        .map(label => `<p class="review-note" lang="${lang}">${esc(label)}</p>`)
        .join("");
    }
    copyRecord = `<p class="small"><span lang="${lang}">${esc(s.copyRecord)}:</span>
      <span lang="en">${esc(explanation.source_rule_id)} v${esc(explanation.version)}, ${esc(explanation.updated_on)}</span></p>`;
  }
  const docs = (rule.required_documents || []).map(d => `<li>${esc(d)}</li>`).join("");
  const evidence = `<section class="evidence-block"
      aria-labelledby="evidence-title-${safeId}">
    <h5 id="evidence-title-${safeId}" lang="${lang}">${esc(s.evidence)}</h5>
    ${ok && rule.notes ? `<p class="small" lang="en">${esc(rule.notes)}</p>` : ""}
    ${c.excerpt ? `<blockquote lang="en">${escVerbatim(c.excerpt)}</blockquote>` : ""}
    ${!ok && !c.excerpt ? `<p class="small" lang="${lang}">${esc(s.evidenceUnavailable)}</p>` : ""}
    ${ok && docs ? `<h5 lang="${lang}">${esc(s.docs)}</h5><ul class="small" lang="en">${docs}</ul>` : ""}
    ${copyRecord}
  </section>`;
  const sourceUrl = safeExternalUrl(c.url);
  const sourceMarkup = sourceUrl
    ? `<a lang="en" href="${esc(sourceUrl)}" rel="noopener">${esc(c.source)}</a>`
    : `<span lang="en">${esc(c.source)}</span>`;
  const hasGuidance = Boolean(localizedRecord);
  const showLabel = hasGuidance ? s.showDetails : s.showEvidence;
  const hideLabel = hasGuidance ? s.hideDetails : s.hideEvidence;
  const isOpen = OPEN_RULE_IDS.has(rule.rule_id);
  const isConfiguredRoute = group === "route"
    && INITIAL_OPEN_ROUTE_BY_PROJECT[LAST_INTAKE?.project_type] === rule.rule_id;
  const clockLink = ok
    && LAST_INTAKE?.project_type === "adu"
    && isConfiguredRoute
    ? `<p class="result-tool-link" lang="${lang}">
        <a href="#clocks">${esc(s.checkDates)}</a>
      </p>` : "";
  return `<article id="rule-${safeId}"
      class="card result-card ${isConfiguredRoute ? "result-route" : "result-card-compact"} ${ok ? "" : "unverified"}"
      data-rule-id="${esc(rule.rule_id)}" data-result-group="${group}"
      aria-labelledby="result-title-${safeId}" tabindex="-1">
    <div class="result-head">
      <h4 class="result-title" id="result-title-${safeId}"
        lang="${displayTitleLang}">${esc(displayTitle)}</h4>
      ${badge}
    </div>
    ${reviewNote}
    ${consequence}
    <p class="source-basis"><b lang="${lang}">${esc(s.source)}:</b>
      ${sourceMarkup}</p>
    <details class="rule-details" data-rule-id="${esc(rule.rule_id)}"
        ${isOpen ? "open" : ""}>
      <summary lang="${lang}">
        <span class="when-closed">${esc(showLabel)}</span>
        <span class="when-open">${esc(hideLabel)}</span>
      </summary>
      <div class="rule-details-body">
        ${guidance}${clockLink}${evidence}
      </div>
    </details>
  </article>`;
}

function renderResults(list) {
  const s = STRINGS[lang];
  const el = document.getElementById("results");
  LAST_RESULTS = list;
  LAST_UNRESOLVED = null;
  const hasRoute = list.some(rule => resultGroup(rule) === "route");
  const status = document.getElementById("resultStatus");
  status.lang = lang;
  if (!list.length) {
    status.textContent = `${s.resultCount(0)} ${s.none}`;
    el.innerHTML = `<div lang="${lang}">
      <h2 class="result-heading" id="resultsHeading" tabindex="-1">${esc(s.results)}</h2>
      ${renderProjectFacts()}
      <div class="notice">${esc(s.none)}</div></div>`;
    return;
  }
  const grouped = groupResultRecords(list);
  const summaryText = resultSummaryText(grouped);
  status.textContent = hasRoute
    ? `${summaryText} ${s.resultIntro} ${s.routeOrientation}`
    : `${summaryText} ${s.none} ${s.supportingOnly}`;
  const shownExplanations = list.map(rule => {
    if (ruleStatus(
      rule, simulating ? ["ca-gov-66321"] : []
    ) !== "verified") return null;
    const explanation = EXPLANATIONS.get(rule.rule_id);
    const localized = usableLocalizedExplanation(explanation);
    return localized ? {explanation, ...localized} : null;
  }).filter(Boolean);
  const oneSharedDraftLabel = shownExplanations.length > 0
    && shownExplanations.every(({explanation, localized, copyLang}) =>
      explanation.review.status === "prototype_review_pending"
      && (lang !== "es"
        || (copyLang === "es" && localized.translation_status === "machine_draft"))
    );
  const sections = RESULT_GROUPS.map(group => {
    const records = grouped.get(group);
    if (!records.length) return "";
    const cards = records.map(rule =>
      renderResultCard(rule, EXPLANATIONS.get(rule.rule_id), {
        suppressPendingReview: oneSharedDraftLabel,
      })
    ).join("");
    const localBoundary = group === "local_process"
      ? `<p class="small result-local-boundary" lang="${lang}">
          ${esc(s.localBoundary)}
        </p>` : "";
    return `<section class="result-group ${group === "local_process" ? "result-local" : ""}"
        aria-labelledby="result-group-${group}">
          <h3 id="result-group-${group}" tabindex="-1"
            lang="${lang}">${esc(s.groups[group])}</h3>
          ${localBoundary}<div class="result-records">${cards}</div>
        </section>`;
  }).join("");
  const draftBanner = oneSharedDraftLabel
    ? `<div class="result-trust-note small" lang="${lang}">${esc(s.explanationBanner)}</div>`
    : "";
  const noRouteNotice = hasRoute
    ? ""
    : `<div class="notice" lang="${lang}">
        <p>${esc(s.none)}</p>
        <p>${esc(s.supportingOnly)}</p>
      </div>`;
  const packetSampleLink = projectSampleState === "active"
    ? `<aside class="packet-route-link" lang="${lang}">
        <p class="utility-label">${esc(s.packetSampleTitle)}</p>
        <p>${esc(s.packetSampleText)}</p>
        <p><a href="prepare.html">${esc(s.packetSampleLink)}</a></p>
      </aside>`
    : "";
  el.innerHTML = `<h2 class="result-heading" id="resultsHeading"
      tabindex="-1" lang="${lang}">${esc(s.results)}</h2>
    ${renderProjectFacts()}
    <p class="result-count" lang="${lang}">${esc(summaryText)}</p>
    <p class="small result-limit" lang="${lang}">${esc(s.resultIntro)}
      ${hasRoute ? esc(s.routeOrientation) : ""}</p>
    ${noRouteNotice}${packetSampleLink}${draftBanner}${renderResultIndex(grouped)}${sections}`;
}

function questionLabel(name, projectType = intakeDraft.project_type) {
  const s = STRINGS[lang];
  if (name === "primary_dwelling_status") return s.primaryQuestion;
  if (name === "adu_project_form") return s.aduFormQuestion;
  if (name === "unpermitted_existing")
    return s.unpermittedQuestions[projectType]
      || s.unpermittedQuestions.adu;
  return s.questions[name] || name;
}

function renderNeedsStaffReview(fieldNames) {
  const s = STRINGS[lang];
  LAST_RESULTS = null;
  LAST_UNRESOLVED = [...fieldNames];
  const status = document.getElementById("resultStatus");
  status.lang = lang;
  status.textContent = s.unknownHeading;
  document.getElementById("results").innerHTML =
    `<div lang="${lang}">
      <h2 class="result-heading" id="resultsHeading" tabindex="-1">
        ${esc(s.unknownHeading)}
      </h2>
      ${renderProjectFacts()}
      <div class="notice">
        <p>${esc(s.unknownIntro)}</p>
        <ul>${fieldNames.map(name =>
          `<li>${esc(questionLabel(name, LAST_INTAKE?.project_type))}</li>`
        ).join("")}</ul>
      </div>
    </div>`;
}

function focusResults() {
  const heading = document.getElementById("resultsHeading");
  if (!heading) return;
  heading.focus({preventScroll: true});
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  heading.scrollIntoView({behavior: reduceMotion ? "auto" : "smooth"});
}

function focusProjectSampleNotice() {
  const notice = document.getElementById("projectSampleNotice");
  if (!notice) return;
  notice.focus({preventScroll: true});
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  notice.scrollIntoView({behavior: reduceMotion ? "auto" : "smooth"});
}

const projectSearchParams = pageIs("project")
  ? new URLSearchParams(window.location.search)
  : null;
const rehearsedSourceId = projectSearchParams
  ? projectSearchParams.get("changed")
  : null;
let simulating = rehearsedSourceId === "ca-gov-66321";
let LAST_RESULTS = null;
let LAST_UNRESOLVED = null;
let LAST_INTAKE = null;
let LAST_JURISDICTION = null;
const OPEN_RULE_IDS = new Set();
let sampleSubmissionInProgress = false;
let projectSampleState = null;

function renderProjectSampleText() {
  const s = STRINGS[lang];
  let suffix = "";
  if (projectSampleState === "edited") suffix = "Edited";
  if (projectSampleState === "unavailable") suffix = "Unavailable";
  document.getElementById("sampleLabel").textContent =
    s[`sample${suffix}Label`];
  document.getElementById("sampleNotice").textContent =
    s[`sample${suffix}Notice`];
  document.getElementById("sampleClear").textContent =
    s[`sample${suffix}Clear`];
}

function storeSubmittedProject(intake, jurisdiction, list = []) {
  LAST_INTAKE = {...intake};
  LAST_JURISDICTION = {
    county: jurisdiction.county,
    kind: jurisdiction.kind,
    name: jurisdiction.name,
    slug: jurisdiction.slug,
  };
  OPEN_RULE_IDS.clear();
  const initialRuleId = INITIAL_OPEN_ROUTE_BY_PROJECT[intake.project_type];
  if (list.some(rule =>
    rule.rule_id === initialRuleId && resultGroup(rule) === "route"
  )) OPEN_RULE_IDS.add(initialRuleId);
}

function invalidateRenderedProjectResult(message = "") {
  LAST_RESULTS = null;
  LAST_UNRESOLVED = null;
  LAST_INTAKE = null;
  LAST_JURISDICTION = null;
  OPEN_RULE_IDS.clear();
  const results = document.getElementById("results");
  if (results) results.innerHTML = "";
  const status = document.getElementById("resultStatus");
  if (status) status.textContent = message;
}

const resultContainerElement = document.getElementById("results");
if (pageIs("project") && resultContainerElement) {
  resultContainerElement.addEventListener("click", event => {
    const editLink = event.target.closest?.("a.edit-answers");
    if (!editLink) return;
    const heading = document.getElementById("screenHeading");
    if (!heading) return;
    event.preventDefault();
    heading.focus();
  });
  resultContainerElement.addEventListener("toggle", event => {
    const disclosure = event.target;
    if (!disclosure.matches?.("details.rule-details")) return;
    const ruleId = disclosure.dataset.ruleId;
    if (!ruleId) return;
    if (disclosure.open) OPEN_RULE_IDS.add(ruleId);
    else OPEN_RULE_IDS.delete(ruleId);
  }, true);
}

function renderDashboard() {
  const changed = simulating ? ["ca-gov-66321"] : [];
  const statuses = RULES.map(r => ({ rule: r, st: ruleStatus(r, changed) }));
  const n = { verified: 0, stale: 0, unverified: 0 };
  statuses.forEach(x => n[x.st]++);
  const total = RULES.length;
  const pct = total ? Math.round(100 * n.verified / total) : 0;
  document.getElementById("pct").textContent = pct;
  const meter = document.getElementById("meter");
  meter.setAttribute(
    "aria-label",
    `${n.verified} rule records inside the review window; ${n.stale} stale; ` +
    `${n.unverified} without a dated source record.`
  );
  meter.innerHTML =
    `<div class="m-good" style="width:${100*n.verified/total}%"></div>` +
    `<div class="m-bad" style="width:${100*n.stale/total}%"></div>` +
    `<div class="m-warn" style="width:${100*n.unverified/total}%"></div>`;
  document.getElementById("meterLegend").innerHTML =
    `<span class="badge ok"><span class="status-ico" aria-hidden="true">✓</span>within review window ${n.verified}</span> ` +
    `<span class="badge bad"><span class="status-ico" aria-hidden="true">✕</span>stale/simulated change ${n.stale}</span> ` +
    `<span class="badge warn"><span class="status-ico" aria-hidden="true">⚠</span>no dated source record ${n.unverified}</span>`;
  // Golden replay runs live in the page: same matcher, same data.
  let pass = 0;
  GOLDEN.forEach(g => {
    const got = screen(g.intake).map(r => r.rule_id).sort().join(",");
    if (got === [...g.expected_rule_ids].sort().join(",")) pass++;
  });
  document.getElementById("goldenLine").textContent =
    `${pass}/${GOLDEN.length} structured golden scenarios replayed and passing in this browser`;
  const goldenScore = document.getElementById("goldenScore");
  if (goldenScore) goldenScore.textContent = `${pass}/${GOLDEN.length}`;
  if (JURIS.length) {
    const nCities = JURIS.filter(j => j.kind === "city").length;
    const nLocal = JURIS.filter(j => j.has_local_layer).length;
    const nHcd = Object.keys(LETTERS).length;
    document.getElementById("covLine").textContent =
      `Registry: ${JURIS.length} California jurisdictions (${nCities} cities, ` +
      `${JURIS.length - nCities} counties) can screen the same statewide ` +
      `candidate-rule set; ${nLocal} have jurisdiction-scoped metadata records; ` +
      `${nHcd} have known HCD letter history.`;
    const coverageScore = document.getElementById("coverageScore");
    if (coverageScore) coverageScore.textContent = JURIS.length;
  }
  document.querySelector("#ruleTable tbody").innerHTML = statuses.map(({rule, st}) => {
    const b = st === "verified"
      ? `<span class="badge ok"><span class="status-ico" aria-hidden="true">✓</span>within review window</span>`
      : st === "stale"
      ? `<span class="badge bad"><span class="status-ico" aria-hidden="true">✕</span>STALE: re-verify</span>`
      : `<span class="badge warn"><span class="status-ico" aria-hidden="true">⚠</span>no dated source record</span>`;
    return `<tr><td data-label="Rule">${esc(rule.pathway)}</td>
      <td data-label="Scope" class="mutedtxt">${esc(rule.jurisdiction_scope)}</td>
      <td data-label="Status">${b}</td></tr>`;
  }).join("");
  document.getElementById("simNote").classList.toggle("hidden", !simulating);
  document.getElementById("simBtn").classList.toggle("hidden", simulating);
  document.getElementById("resetBtn").classList.toggle("hidden", !simulating);
}

function renderSources() {
  document.querySelector("#sourceTable tbody").innerHTML =
    Object.entries(SOURCES).map(([url, sourceRecord]) => {
      const metadata = sourceRecord && typeof sourceRecord === "object"
        ? sourceRecord : {};
      const sourceUrl = safeExternalUrl(url);
      const label = esc(metadata.label || url);
      const source = sourceUrl
        ? `<a href="${esc(sourceUrl)}" rel="noopener">${label}</a>`
        : `<span>${label}</span>`;
      const watched = metadata.watch !== false && nonBlank(metadata.sha256);
      const monitoring = watched
        ? `<span class="badge info">watched</span>`
        : `<span class="badge info">reference only</span>`;
      const recorded = metadata.fetched_on ? esc(metadata.fetched_on) : "Not recorded";
      const digest = nonBlank(metadata.sha256)
        ? `${esc(metadata.sha256.slice(0, 16))}…` : "not recorded";
      return `<tr><td data-label="Source">${source}</td>
        <td data-label="Monitoring">${monitoring}</td>
        <td data-label="Recorded" class="mutedtxt">${recorded}</td>
        <td data-label="SHA-256" class="mutedtxt source-digest">${digest}</td></tr>`;
    }).join("");
}

const intakeFormElement = document.getElementById("intake");
function removeProjectSampleFromUrl() {
  const updatedUrl = new URL(window.location.href);
  updatedUrl.searchParams.delete("sample");
  window.history.replaceState(
    null,
    "",
    `${updatedUrl.pathname}${updatedUrl.search}${updatedUrl.hash}`,
  );
}

function deactivateProjectSample() {
  const hadRenderedProjectResult = LAST_RESULTS !== null
    || LAST_UNRESOLVED !== null
    || LAST_INTAKE !== null;
  if (projectSampleState === "unavailable") {
    projectSampleState = null;
    document.getElementById("sampleEntry").classList.remove("hidden");
    document.getElementById("projectSampleNotice").classList.add("hidden");
    removeProjectSampleFromUrl();
    invalidateRenderedProjectResult(
      hadRenderedProjectResult ? STRINGS[lang].resultCleared : ""
    );
    return;
  }
  if (projectSampleState === "active") {
    projectSampleState = "edited";
    document.getElementById("sampleEntry").classList.remove("hidden");
    renderProjectSampleText();
    invalidateRenderedProjectResult(
      hadRenderedProjectResult ? STRINGS[lang].sampleEditedNotice : ""
    );
    removeProjectSampleFromUrl();
    return;
  }
  invalidateRenderedProjectResult(
    hadRenderedProjectResult
      ? projectSampleState === "edited"
        ? STRINGS[lang].sampleEditedNotice
        : STRINGS[lang].resultCleared
      : ""
  );
}

function applyRequestedProjectSample() {
  const requestedSampleId = requestedProjectSampleId(projectSearchParams);
  const sample = prepareProjectSample(
    projectSearchParams,
    GOLDEN,
    JURIS,
  );
  if (!sample || !intakeFormElement) {
    if (requestedSampleId) {
      projectSampleState = "unavailable";
      document.getElementById("sampleEntry").classList.add("hidden");
      document.getElementById("projectSampleNotice").classList.remove("hidden");
      renderProjectSampleText();
      document.getElementById("resultStatus").textContent =
        STRINGS[lang].sampleUnavailableNotice;
      focusProjectSampleNotice();
    }
    return false;
  }

  projectSampleState = "active";
  intakeDraft = {...sample.intake};
  const jurisdictionInput = document.getElementById("jurisInput");
  jurisdictionInput.value = jurisDisplay(sample.jurisdiction);
  renderForm();
  document.getElementById("sampleEntry").classList.add("hidden");
  document.getElementById("projectSampleNotice").classList.remove("hidden");
  sampleSubmissionInProgress = true;
  try {
    intakeFormElement.requestSubmit();
  } finally {
    sampleSubmissionInProgress = false;
  }
  return true;
}

if (pageIs("project") && intakeFormElement) {
  intakeFormElement.addEventListener("submit", e => {
  e.preventDefault();
  rememberIntakeValues();
  const form = e.target;
  const f = new FormData(form);
  const jurisdiction = resolveJurisdiction();
  if (!jurisdiction) {
    const s = STRINGS[lang];
    invalidateRenderedProjectResult(s.jurisRequired);
    document.getElementById("results").innerHTML =
      `<div lang="${lang}"><h2 class="result-heading" id="resultsHeading"
        tabindex="-1">${esc(s.results)}</h2>
       <div class="notice">${esc(s.jurisRequired)}</div></div>`;
    renderJurisStatus(true);
    document.getElementById("jurisInput").focus();
    return;
  }
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  if (["edited", "unavailable"].includes(projectSampleState)) {
    projectSampleState = null;
    document.getElementById("projectSampleNotice").classList.add("hidden");
  }
  const projectType = f.get("project_type");
  const materialFields = fieldsForProject(projectType);
  const intake = {
    project_type: projectType,
    jurisdiction: jurisdiction.slug,
  };
  materialFields.forEach(name => {
    intake[name] = f.get(name);
  });
  const unresolved = materialFields.filter(name => {
    const value = intake[name];
    return value == null || value === "unknown";
  });
  if (unresolved.length) {
    storeSubmittedProject(intake, jurisdiction);
    renderNeedsStaffReview(unresolved);
    if (sampleSubmissionInProgress) focusProjectSampleNotice();
    else focusResults();
    return;
  }
  const matchedRules = screen(intake);
  storeSubmittedProject(intake, jurisdiction, matchedRules);
  renderResults(matchedRules);
  if (sampleSubmissionInProgress) focusProjectSampleNotice();
  else focusResults();
  });

  intakeFormElement.addEventListener("change", event => {
    const target = event.target;
    if (!target.name) return;
    deactivateProjectSample();
    intakeDraft[target.name] = target.value;
    if (target.name === "project_type") renderProjectQuestions();
  });
}
function jurisDisplay(j) {
  return j.kind === "county" ? j.name : `${j.name} (${j.county.replace(" County","")} Co.)`;
}
function resolveJurisdiction() {
  const raw = document.getElementById("jurisInput").value.trim();
  return jurisByName.get(raw.toLowerCase()) || null;
}
function renderJurisStatus(showError = false) {
  const s = STRINGS[lang];
  const el = document.getElementById("jurisStatus");
  const input = document.getElementById("jurisInput");
  const raw = document.getElementById("jurisInput").value.trim();
  if (!raw) {
    if (el.textContent) el.textContent = "";
    input.removeAttribute("aria-invalid");
    return;
  }
  const j = resolveJurisdiction();
  if (!j) {
    if (el.textContent !== s.statusUnknown) el.textContent = s.statusUnknown;
    if (showError) input.setAttribute("aria-invalid", "true");
    return;
  }
  input.removeAttribute("aria-invalid");
  const localCount = JURIS.filter(x => x.has_local_layer).length;
  let html = j.has_local_layer
    ? `<strong>${esc(s.localMetadata)}.</strong> ${esc(s.statusLocal)}`
    : `${esc(s.statusBaseline)} (${esc(s.localCoverage(localCount, JURIS.length))})`;
  const scanRec = SCANS[j.slug];
  if (scanRec) {
    const scanPath = safeLocalJsonPath(j.slug);
    const scanLink = scanPath
      ? `: <a href="${esc(scanPath)}" rel="noopener">${esc(s.viewScan)}</a>`
      : "";
    html += `<br><span class="badge info">${esc(s.scanned)}</span> ` +
      `${esc(s.scanRecord(scanRec.scanned_on, scanRec.findings))}${scanLink}.`;
  }
  const history = LETTERS[j.slug] || [];
  if (history.length) {
    html += `<br><span class="badge warn"><span class="status-ico" aria-hidden="true">⚠</span>HCD</span> ` +
      `${esc(s.hcdHistory)}: ${esc(s.letterCount(history.length))}`;
    for (const letter of history.slice(0, 3)) {
      const label = `${esc(letter.kind)}, ${esc(letter.date)}` +
        (letter.authority ? `: ${esc(letter.authority)}` : "");
      const letterUrl = safeExternalUrl(letter.url);
      html += `<br>&nbsp;&nbsp;· ` +
        (letterUrl
          ? `<a lang="en" href="${esc(letterUrl)}" rel="noopener">${label}</a>`
          : `<span lang="en">${label}</span>`);
    }
    if (history.length > 3)
      html += `<br>&nbsp;&nbsp;· …${esc(s.moreLetters(history.length - 3))}`;
  }
  if (el.innerHTML !== html) el.innerHTML = html;
}

function scanOrdinance(text) {
  const findings = [];
  for (const check of CHECKS) {
    const seen = [];
    for (const pattern of check.patterns) {
      const re = new RegExp(pattern, "gi");
      let m;
      while ((m = re.exec(text)) !== null) {
        const excluded = (check.exclude_patterns || []).some(ex => {
          const exRe = new RegExp(ex, "gi");
          let e;
          while ((e = exRe.exec(text)) !== null)
            if (e.index <= m.index && m.index + m[0].length <= e.index + e[0].length) return true;
          return false;
        });
        if (excluded || seen.some(([s, e]) => s <= m.index && m.index < e)) continue;
        if (check.context_patterns) {
          const ws = Math.max(0, m.index - 300);
          const win = text.slice(ws, m.index + m[0].length + 300);
          if (!check.context_patterns.some(p => new RegExp(p, "i").test(win))) continue;
        }
        seen.push([m.index, m.index + m[0].length]);
        const start = Math.max(0, m.index - 120);
        const end = Math.min(text.length, m.index + m[0].length + 120);
        findings.push({ check, excerpt: text.slice(start, end).replace(/\s+/g, " "), offset: m.index });
      }
    }
  }
  return findings.sort((a, b) => a.offset - b.offset);
}

const scanButtonElement = document.getElementById("scanBtn");
if (pageIs("review") && scanButtonElement) {
  scanButtonElement.addEventListener("click", () => {
  const text = document.getElementById("ordText").value;
  const el = document.getElementById("scanResults");
  const status = document.getElementById("scanStatus");
  if (!text.trim()) {
    el.innerHTML = "";
    status.textContent = "Paste ordinance text before scanning.";
    document.getElementById("ordText").focus();
    return;
  }
  const findings = scanOrdinance(text);
  if (!findings.length) {
    el.innerHTML = `<div class="notice">No candidate provisions flagged.
      Presence-based screen only. This is <b>not</b> a certification of compliance.</div>`;
    status.textContent = "No candidate provisions were flagged. This is only a presence-based screen.";
    return;
  }
  el.innerHTML = findings.map(f => {
    const definite = f.check.severity === "definite";
    return `<div class="card ${definite ? "" : "unverified"}"
      style="border-left-color:${definite ? "var(--critical)" : "var(--warning)"}">
      <h3>${esc(f.check.title)}
        <span class="badge ${definite ? "bad" : "warn"}">
        <span class="status-ico" aria-hidden="true">${definite ? "✕" : "⚠"}</span>${definite ? "finding" : "review"}</span></h3>
      <blockquote>…${escVerbatim(f.excerpt)}…</blockquote>
      <p class="small"><b>State law:</b> ${esc(f.check.state_law)}</p>
      <p class="small"><b>Explanation:</b> ${esc(f.check.explanation)}</p>
      <p class="small mutedtxt"><b>HCD precedent:</b> ${esc(f.check.hcd_precedent)}</p>
    </div>`;
  }).join("");
  status.textContent = `${findings.length} potential provision${findings.length === 1 ? "" : "s"} flagged for review.`;
  });
}

const loadSampleElement = document.getElementById("loadSample");
if (pageIs("review") && loadSampleElement && scanButtonElement) {
  loadSampleElement.addEventListener("click", () => {
    document.getElementById("ordText").value = SAMPLE_ORDINANCE;
    scanButtonElement.click();
  });
}

const clockButtonElement = document.getElementById("clockBtn");
if (pageIs("project") && clockButtonElement) {
  clockButtonElement.addEventListener("click", () => {
  const v = document.getElementById("recvDate").value;
  const el = document.getElementById("clockResults");
  const status = document.getElementById("clockStatus");
  if (!v) {
    el.innerHTML = "";
    status.textContent = "Enter the application receipt date first.";
    document.getElementById("recvDate").focus();
    return;
  }
  const received = new Date(`${v}T00:00:00Z`);
  const addCal = (dateValue, days) => {
    const out = new Date(dateValue);
    out.setUTCDate(out.getUTCDate() + days);
    return out;
  };
  const fmt = d => d.toISOString().slice(0, 10);
  const fmtDisplay = d => new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "long",
    timeZone: "UTC",
    year: "numeric",
  }).format(d);
  const canShowDecision = document.getElementById("clockComplete").checked
    && document.getElementById("clockExisting").checked;
  const decisionDate = addCal(received, 60);
  const decision = canShowDecision
    ? `<time datetime="${fmt(decisionDate)}">${fmtDisplay(decisionDate)}</time>`
    : "Not shown";
  const decisionReason = canShowDecision
    ? "Shown because both statements above were confirmed."
    : "Confirm both statements above to show this date.";
  el.innerHTML = `<section class="clock-output" aria-labelledby="clockOutputHeading">
    <h3 id="clockOutputHeading">Review date information</h3>
    <dl class="clock-milestones">
      <div>
        <dt>Completeness notice</dt>
        <dd><strong>Not calculated.</strong> The agency’s closure calendar is
          required to count 15 business days.</dd>
      </div>
      <div>
        <dt>If the agency does not send a completeness notice</dt>
        <dd><strong>Not calculated.</strong> This depends on the exact date
          required for that notice.</dd>
      </div>
      <div>
        <dt>Conditional approval or denial date</dt>
        <dd><strong>${decision}.</strong> ${decisionReason}</dd>
      </div>
    </dl>
  </section>
  <p class="small mutedtxt">These are separate clocks. A completeness notice is
  not an approval. Corrections, resubmittals, tolling, and local closures are
  not modeled.</p>`;
  status.textContent = canShowDecision
    ? "Date information updated. The conditional 60-day date is shown. The 15-business-day date remains unknown without the agency closure calendar."
    : "Date information updated. Exact dates are not shown until their required facts or calendar are available.";
  });
}

function matchingSimulationCount() {
  if (pageIs("evidence")) {
    return RULES.filter(rule =>
      ruleStatus(rule, []) === "verified"
      && ruleStatus(rule, ["ca-gov-66321"]) === "stale"
    ).length;
  }
  if (LAST_RESULTS === null) return 0;
  return LAST_RESULTS.filter(rule =>
    ruleStatus(rule, []) === "verified"
    && ruleStatus(rule, ["ca-gov-66321"]) === "stale"
  ).length;
}

function rerenderSimulationState() {
  if (pageIs("evidence") && document.getElementById("ruleTable"))
    renderDashboard();
  if (pageIs("project") && LAST_RESULTS !== null) renderResults(LAST_RESULTS);
}

const simulationButtonElement = document.getElementById("simBtn");
const resetSimulationButtonElement = document.getElementById("resetBtn");
if (pageIs("evidence")
    && simulationButtonElement
    && resetSimulationButtonElement) {
  simulationButtonElement.addEventListener("click", () => {
    const affected = matchingSimulationCount();
    simulating = true;
    rerenderSimulationState();
    const status = document.getElementById("simulationStatus");
    status.lang = "en";
    status.textContent = STRINGS.en.simulationApplied(affected);
    resetSimulationButtonElement.focus();
  });
  resetSimulationButtonElement.addEventListener("click", () => {
    const restored = matchingSimulationCount();
    simulating = false;
    rerenderSimulationState();
    const status = document.getElementById("simulationStatus");
    status.lang = "en";
    status.textContent = STRINGS.en.simulationReset(restored);
    simulationButtonElement.focus();
  });
}

const languageToggleElement = document.getElementById("langToggle");
if (pageIs("project") && languageToggleElement) {
  languageToggleElement.addEventListener("click", event => {
    rememberIntakeValues();
    event.preventDefault();
    lang = lang === "en" ? "es" : "en";
    renderForm();
    renderJurisStatus();
    if (LAST_RESULTS !== null) renderResults(LAST_RESULTS);
    else if (LAST_UNRESOLVED !== null)
      renderNeedsStaffReview(LAST_UNRESOLVED);
  });
}

const READINESS_FINDING_STATUSES = new Set([
  "present",
  "missing",
  "not_applicable",
  "conflicting",
  "needs_staff_review",
  "not_evaluated",
]);

const READINESS_OVERALL_STATUSES = new Set([
  "known_gaps",
  "needs_review",
  "no_known_gaps_in_bounded_manifest",
  "outside_bounded_workflow",
  "source_review_required",
]);

const READINESS_SOURCE_STATUSES = new Set([
  "current",
  "source_review_required",
]);

function readinessReviewDueOn(data) {
  const candidates = [
    data?.source_review_due_on,
    data?.result?.source_review_due_on,
    data?.evidence_manifest?.source_review_due_on,
  ].filter(value => value != null);
  if (!candidates.length || !candidates.every(validIsoDate)) return null;
  const unique = new Set(candidates);
  return unique.size === 1 ? candidates[0] : null;
}

function readinessSourceStatusAsOf(data) {
  const candidates = [
    data?.result?.source_status_as_of,
    data?.evidence_manifest?.source_status_as_of,
  ].filter(value => value != null);
  if (!candidates.length) return data?.result?.evaluated_on || null;
  if (!candidates.every(validIsoDate)) return null;
  const unique = new Set(candidates);
  return unique.size === 1 ? candidates[0] : null;
}

function validReadinessData(data) {
  if (!data || typeof data !== "object"
      || !data.workflow || !data.packet || !data.result
      || !data.remedies || !data.counts || !data.evidence_manifest
      || data.packet.synthetic !== true
      || !validStableId(data.workflow.workflow_id)
      || data.packet.workflow_id !== data.workflow.workflow_id
      || data.result.workflow_id !== data.workflow.workflow_id
      || data.result.packet_id !== data.packet.packet_id
      || !validIsoDate(data.packet.evaluated_on)
      || !validIsoDate(data.result.evaluated_on)
      || data.result.evaluated_on !== data.packet.evaluated_on
      || !readinessReviewDueOn(data)
      || !readinessSourceStatusAsOf(data)
      || !READINESS_OVERALL_STATUSES.has(data.result.overall_status)
      || !READINESS_SOURCE_STATUSES.has(data.result.source_status)
      || (
        data.result.overall_status === "source_review_required"
          ? data.result.source_status !== "source_review_required"
          : data.result.source_status !== "current"
      )
      || !Array.isArray(data.workflow.source_bindings)
      || data.workflow.source_bindings.length < 1
      || !Array.isArray(data.workflow.facts)
      || !Array.isArray(data.packet.facts)
      || data.workflow.facts.length !== data.packet.facts.length
      || !Array.isArray(data.workflow.requirements)
      || !Array.isArray(data.result.findings)
      || data.workflow.requirements.length !== data.result.findings.length
      || !Array.isArray(data.remedies.entries)
      || data.remedies.entries.length !== data.workflow.requirements.length
      || !Array.isArray(data.result.staff_questions)
      || !data.result.staff_questions.every(nonBlank)
      || !nonBlank(data.result.boundary)) return false;
  const requirementIds = data.workflow.requirements.map(
    requirement => requirement.requirement_id
  );
  const factIds = data.workflow.facts.map(fact => fact.fact_id);
  const packetFactIds = data.packet.facts.map(fact => fact.fact_id);
  const sourceBindings = new Map(
    data.workflow.source_bindings.map(binding => [binding.source_id, binding])
  );
  const factDefinitions = new Map(
    data.workflow.facts.map(fact => [fact.fact_id, fact])
  );
  const findingIds = data.result.findings.map(
    finding => finding.requirement_id
  );
  const remedyIds = data.remedies.entries.map(
    remedy => remedy.requirement_id
  );
  const review = data.remedies.review;
  const reviewStatuses = [
    "prototype_review_pending",
    "human_reviewed",
    "jurisdiction_approved",
  ];
  const reviewMetadata = [
    review?.reviewer,
    review?.method,
    review?.reviewed_on,
    review?.reviewed_version,
    review?.content_fingerprint,
  ];
  const reviewValid = review
    && reviewStatuses.includes(review.status)
    && (
      review.status === "prototype_review_pending"
        ? reviewMetadata.every(value => value == null)
        : reviewMetadata.every(nonBlank)
          && validIsoDate(review.reviewed_on)
          && review.reviewed_version === data.remedies.version
          && /^sha256:[0-9a-f]{64}$/.test(
            review.content_fingerprint || ""
          )
    );
  const countsMatch = [...READINESS_FINDING_STATUSES].every(status =>
    Number.isInteger(data.counts[status])
    && data.counts[status] >= 0
    && data.counts[status] === data.result.findings.filter(
      finding => finding.status === status
    ).length
  );
  const unresolvedCount = data.counts.conflicting
    + data.counts.needs_staff_review
    + data.counts.not_evaluated;
  const overallMatchesFindings = {
    known_gaps: data.counts.missing > 0,
    needs_review: data.counts.missing === 0 && unresolvedCount > 0,
    no_known_gaps_in_bounded_manifest:
      data.counts.missing === 0 && unresolvedCount === 0,
    outside_bounded_workflow:
      data.counts.not_evaluated === data.result.findings.length,
    source_review_required:
      data.counts.needs_staff_review === data.result.findings.length,
  }[data.result.overall_status] === true;
  return requirementIds.every(validStableId)
    && factIds.every(validStableId)
    && new Set(factIds).size === factIds.length
    && packetFactIds.every((id, index) => id === factIds[index])
    && data.workflow.facts.every(fact => {
      const hasSource = fact.source_id != null || fact.source_field != null;
      return hasSource
        ? validStableId(fact.source_id)
          && /^[A-Za-z][A-Za-z0-9_]*$/.test(fact.source_field || "")
          && sourceBindings.has(fact.source_id)
        : fact.source_id == null && fact.source_field == null;
    })
    && data.packet.facts.every(fact => {
      const definition = factDefinitions.get(fact.fact_id);
      if (!definition || !["yes", "no", "unknown"].includes(fact.value))
        return false;
      if (definition.source_id == null)
        return ["synthetic_applicant_assertion", "applicant_assertion"].includes(
          fact.provenance
        )
          && fact.source_id == null
          && fact.source_field == null
          && fact.source_checked_on == null;
      const binding = sourceBindings.get(definition.source_id);
      return fact.provenance === "synthetic_public_record_fixture"
        && fact.value !== "unknown"
        && fact.source_id === definition.source_id
        && fact.source_field === definition.source_field
        && fact.source_checked_on === binding?.source_checked_on;
    })
    && new Set(requirementIds).size === requirementIds.length
    && findingIds.every((id, index) => id === requirementIds[index])
    && new Set(remedyIds).size === remedyIds.length
    && remedyIds.every(id => requirementIds.includes(id))
    && data.result.findings.every(finding =>
      nonBlank(finding.label)
      && nonBlank(finding.category)
      && nonBlank(finding.reason)
      && READINESS_FINDING_STATUSES.has(finding.status)
    )
    && data.workflow.source_bindings.every(binding =>
      validStableId(binding.source_id)
      && validHttpsUrl(binding.url)
      && validIsoDate(binding.source_checked_on)
      && /^[0-9a-f]{64}$/.test(binding.sha256 || "")
    )
    && data.remedies.entries.every(entry =>
      nonBlank(entry.action)
      && /^sha256:[0-9a-f]{64}$/.test(
        entry.requirement_fingerprint || ""
      )
    )
    && reviewValid
    && countsMatch
    && overallMatchesFindings;
}

function readinessParcelEvidenceMarkup(data, current) {
  if (!current) return "";
  const definitions = new Map(
    data.workflow.facts.map(fact => [fact.fact_id, fact])
  );
  const bindings = new Map(
    data.workflow.source_bindings.map(binding => [binding.source_id, binding])
  );
  const parcelFacts = data.packet.facts.filter(
    fact => fact.provenance === "synthetic_public_record_fixture"
  );
  if (!parcelFacts.length) return "";
  const rows = parcelFacts.map(fact => {
    const definition = definitions.get(fact.fact_id);
    const binding = bindings.get(fact.source_id);
    const sourceUrl = safeExternalUrl(binding?.url);
    const sourceLabel = sourceUrl
      ? `<a href="${esc(sourceUrl)}">${esc(binding.label
        || "Public parcel dataset")}</a>`
      : esc(binding?.label || "Public parcel dataset");
    return `<div>
      <dt>${esc(definition.label)}</dt>
      <dd><strong>${fact.value === "yes" ? "Yes" : "No"}</strong>.
        Invented fixture value shaped like
        <code>${esc(fact.source_field)}</code> in ${sourceLabel};
        source metadata recorded
        ${esc(formatSourceDate(fact.source_checked_on))}.</dd>
    </div>`;
  }).join("");
  return `<section class="packet-evidence"
    aria-labelledby="parcelEvidenceHeading">
    <div>
      <p class="section-kicker">Parcel-aware fixture</p>
      <h2 id="parcelEvidenceHeading">Which parcel fields shaped this sample</h2>
      <p>These values are fabricated for testing. The links and field names
        are real source bindings; no address, APN, or live parcel was
        queried.</p>
    </div>
    <dl>${rows}</dl>
  </section>`;
}

function readinessSourceIsCurrent(data) {
  if (data.result.source_status !== "current") return false;
  const reviewDueOn = readinessReviewDueOn(data);
  if (!reviewDueOn) return false;
  const now = new Date();
  const today = [
    now.getUTCFullYear(),
    String(now.getUTCMonth() + 1).padStart(2, "0"),
    String(now.getUTCDate()).padStart(2, "0"),
  ].join("-");
  return today <= reviewDueOn;
}

function readinessCount(data, status) {
  const value = data.counts[status];
  return Number.isInteger(value) && value >= 0 ? value : 0;
}

function readinessFindingRow(
  finding,
  remedy,
  showAction,
  tone,
  review,
) {
  const stateLabels = {
    missing: "Reported missing",
    conflict: "Reported conflict",
    question: "Needs confirmation",
  };
  const stateLabel = stateLabels[tone];
  const pendingReview = review.status === "prototype_review_pending";
  const actionLabel = pendingReview
    ? "AI-assisted draft next step"
    : "Reviewed next step";
  const actionReview = pendingReview
    ? `<span class="finding-review">Not human-reviewed</span>`
    : "";
  const action = showAction && remedy
    ? `<div class="finding-action">
        <p class="utility-label">${actionLabel} ${actionReview}</p>
        <p>${esc(remedy.action)}</p>
      </div>` : "";
  const reconcile = tone === "conflict"
    ? `<div class="finding-action finding-action-reconcile">
        <p class="utility-label">Reconcile before submission</p>
        <p>Confirm which reported version is correct, then align the packet.
          Ask Woodland staff which record controls if the conflict remains.</p>
      </div>`
    : "";
  return `<article class="packet-finding packet-finding-${tone}">
    <div class="finding-state">
      <span>${esc(stateLabel)}</span>
    </div>
    <div class="finding-copy">
      <p class="finding-category">${esc(finding.category)}</p>
      <h3>${esc(finding.label)}</h3>
      <p>${esc(finding.reason)}</p>
      ${action}
      ${reconcile}
      <p class="finding-source">Checklist location:
        ${esc(finding.source_locator)}</p>
    </div>
  </article>`;
}

function readinessCompactList(findings, label) {
  if (!findings.length) return "";
  return `<details class="packet-detail">
    <summary>${esc(label)} <span>(${findings.length})</span></summary>
    <ul>${findings.map(finding =>
      `<li><strong>${esc(finding.label)}</strong>
        <span>${esc(finding.reason)}</span></li>`
    ).join("")}</ul>
  </details>`;
}

function readinessReviewLabel(review) {
  if (review.status === "jurisdiction_approved")
    return `Jurisdiction-approved action wording. ${review.reviewer}, ${formatSourceDate(review.reviewed_on)}, version ${review.reviewed_version}.`;
  if (review.status === "human_reviewed")
    return `Human-reviewed action wording. ${review.reviewer}, ${formatSourceDate(review.reviewed_on)}, version ${review.reviewed_version}.`;
  return "Action wording is an AI-assisted draft. It has not been reviewed by Woodland staff or a named human reviewer.";
}

function readinessCountPhrase(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function readinessStatusSummary(data, current) {
  const overall = data.result.overall_status;
  const missing = readinessCount(data, "missing");
  const conflicts = readinessCount(data, "conflicting");
  const needsConfirmation = readinessCount(data, "needs_staff_review");
  const notEvaluated = readinessCount(data, "not_evaluated");
  const staffQuestions = data.result.staff_questions.length;
  const staffQuestionText = staffQuestions
    ? `${readinessCountPhrase(
      staffQuestions,
      "direct question",
    )} for staff ${staffQuestions === 1 ? "is" : "are"} included in the generated result.`
    : "";

  if (!current || overall === "source_review_required") {
    return {
      headline: "Source review is required before using this packet result",
      intro: [
        "The dated checklist record is outside its review window or was marked changed.",
        staffQuestionText,
        "Draft actions and packet findings are withheld until the source is checked again.",
      ].filter(Boolean).join(" "),
    };
  }
  if (overall === "outside_bounded_workflow") {
    return {
      headline: "This packet is outside the encoded Woodland workflow",
      intro: [
        `${readinessCountPhrase(
          notEvaluated,
          "checklist item",
        )} ${notEvaluated === 1 ? "was" : "were"} not evaluated.`,
        "This prototype only covers the City preapproved detached ADU workflow.",
        staffQuestionText,
      ].filter(Boolean).join(" "),
    };
  }
  if (overall === "needs_review") {
    const headline = conflicts
      ? `${readinessCountPhrase(
        conflicts,
        "reported conflict",
      )} ${conflicts === 1 ? "needs" : "need"} reconciliation`
      : notEvaluated
        ? "Confirm the workflow before using this checklist result"
        : "This bounded checklist result needs confirmation";
    return {
      headline,
      intro: [
        conflicts
          ? `${readinessCountPhrase(
            conflicts,
            "item",
          )} has information that does not agree.`
          : "",
        needsConfirmation
          ? `${readinessCountPhrase(
            needsConfirmation,
            "item",
          )} ${needsConfirmation === 1 ? "needs" : "need"} an answer or staff confirmation.`
          : "",
        notEvaluated
          ? `${readinessCountPhrase(
            notEvaluated,
            "item",
          )} ${notEvaluated === 1 ? "was" : "were"} not evaluated.`
          : "",
        staffQuestionText,
        "Reported presence is not a review of the files.",
      ].filter(Boolean).join(" "),
    };
  }
  if (overall === "no_known_gaps_in_bounded_manifest") {
    return {
      headline: "No reported gaps in this bounded checklist",
      intro: "The generated inventory has no missing, conflicting, unresolved, or unevaluated items. Reported presence is not a review of the files and does not certify completeness.",
    };
  }
  return {
    headline: `${readinessCountPhrase(
      missing,
      "reported missing item",
    )} in this bounded checklist`,
    intro: [
      conflicts
        ? `${readinessCountPhrase(
          conflicts,
          "reported conflict",
        )} ${conflicts === 1 ? "also needs" : "also need"} reconciliation.`
        : "",
      needsConfirmation
        ? `${readinessCountPhrase(
          needsConfirmation,
          "other item",
        )} ${needsConfirmation === 1 ? "needs" : "need"} an answer or staff confirmation.`
        : "",
      notEvaluated
        ? `${readinessCountPhrase(
          notEvaluated,
          "item",
        )} ${notEvaluated === 1 ? "was" : "were"} not evaluated.`
        : "",
      staffQuestionText,
      "Reported presence is not a review of the files.",
    ].filter(Boolean).join(" "),
  };
}

function readinessCountMarkup(data) {
  const entries = [
    ["Reported missing", readinessCount(data, "missing")],
    ["Reported conflicts", readinessCount(data, "conflicting")],
    ["Need confirmation", readinessCount(data, "needs_staff_review")],
    ["Not evaluated", readinessCount(data, "not_evaluated")],
    ["Reported present", readinessCount(data, "present")],
    ["Not applicable", readinessCount(data, "not_applicable")],
  ].filter(([, count]) => count > 0);
  return `<dl class="packet-counts" aria-label="Finding counts">
    ${entries.map(([label, count]) =>
      `<div><dt>${esc(label)}</dt><dd>${count}</dd></div>`
    ).join("")}
  </dl>`;
}

function renderReadiness(data) {
  if (!validReadinessData(data))
    throw new Error("generated packet-presence data failed validation");
  READINESS = data;
  const output = document.getElementById("readinessOutput");
  const remedyById = new Map(
    data.remedies.entries.map(entry => [entry.requirement_id, entry])
  );
  const current = readinessSourceIsCurrent(data);
  const missing = data.result.findings.filter(
    finding => finding.status === "missing"
  );
  const conflicts = data.result.findings.filter(
    finding => finding.status === "conflicting"
  );
  const questions = data.result.findings.filter(
    finding => finding.status === "needs_staff_review"
  );
  const present = data.result.findings.filter(
    finding => finding.status === "present"
  );
  const notApplicable = data.result.findings.filter(
    finding => finding.status === "not_applicable"
  );
  const notEvaluated = data.result.findings.filter(
    finding => finding.status === "not_evaluated"
  );
  const source = data.workflow.source_bindings[0];
  const sourceUrl = safeExternalUrl(source.url);
  const reviewDueOn = readinessReviewDueOn(data);
  const summary = readinessStatusSummary(data, current);
  const missingRows = current
    ? missing.map(finding => readinessFindingRow(
      finding,
      remedyById.get(finding.requirement_id),
      true,
      "missing",
      data.remedies.review,
    )).join("")
    : "";
  const conflictRows = current
    ? conflicts.map(finding => readinessFindingRow(
      finding,
      null,
      false,
      "conflict",
      data.remedies.review,
    )).join("")
    : "";
  const questionRows = current
    ? questions.map(finding => readinessFindingRow(
      finding,
      remedyById.get(finding.requirement_id),
      true,
      "question",
      data.remedies.review,
    )).join("")
    : "";
  const directQuestions = current && data.result.staff_questions.length
    ? `<div class="staff-question-list">
        <h3>Questions to take to Woodland staff</h3>
        <ul>${data.result.staff_questions.map(question =>
          `<li>${esc(question)}</li>`
        ).join("")}</ul>
      </div>` : "";
  const sourceLink = sourceUrl
    ? `<a href="${esc(sourceUrl)}">City of Woodland preapproved ADU
        checklist</a>`
    : "City of Woodland preapproved ADU checklist";
  const reviewLabel = readinessReviewLabel(data.remedies.review);
  const countsMarkup = current
    ? readinessCountMarkup(data)
    : `<p class="source-review-hold"><strong>Action copy is
        withheld.</strong> The dated source must be checked before this
        result can be used again.</p>`;
  const inventoryMarkup = current
    ? `<section class="packet-inventory" aria-labelledby="inventoryHeading">
        <p class="section-kicker">Full bounded record</p>
        <h2 id="inventoryHeading">What happened to every checklist item</h2>
        ${readinessCompactList(present, "Reported present")}
        ${readinessCompactList(notApplicable, "Not applicable from the made-up facts")}
        ${readinessCompactList(notEvaluated, "Not evaluated")}
      </section>`
    : "";
  const sourceStatusAsOf = readinessSourceStatusAsOf(data);
  const recordedSourceStatus = data.evidence_manifest.source_status
    || data.result.source_status;
  const manifestLink = current
    ? `<a href="data/readiness/generated/woodland-preapproved-adu-evidence.json">Open the generated evidence manifest</a>`
    : `<a href="data/readiness/generated/woodland-preapproved-adu-evidence.json">Open the historical generated evidence manifest</a>
      <span class="evidence-record-note">This record captured source status
        “${esc(recordedSourceStatus)}” as of
        ${esc(formatSourceDate(sourceStatusAsOf))}. It is not a current source
        check.</span>`;
  const runtimeSourceStatus = current
    ? ""
    : `<div>
        <dt>Browser source status now</dt>
        <dd>Source review required. The generated result is historical.</dd>
      </div>`;

  document.getElementById("readinessPacketId").textContent =
    data.packet.packet_id;
  document.getElementById("readinessDate").textContent =
    formatSourceDate(data.packet.evaluated_on);
  output.innerHTML = `
    <section class="readiness-verdict ${current ? "is-current" : "needs-source"}"
      aria-labelledby="readinessVerdictHeading">
      <div class="verdict-copy">
        <p class="section-kicker">Deterministic packet-presence result</p>
        <h2 id="readinessVerdictHeading">${esc(summary.headline)}</h2>
        <p>${esc(summary.intro)}</p>
      </div>
      ${countsMarkup}
    </section>

    ${readinessParcelEvidenceMarkup(data, current)}

    ${current && missing.length ? `<section class="packet-ledger"
      aria-labelledby="missingHeading">
      <div class="ledger-heading">
        <p class="section-kicker">Act before submission</p>
        <h2 id="missingHeading">Reported missing items</h2>
        <p>${esc(reviewLabel)}</p>
      </div>
      <div class="finding-list">${missingRows}</div>
    </section>` : ""}

    ${current && conflicts.length ? `<section class="packet-ledger"
      aria-labelledby="conflictHeading">
      <div class="ledger-heading">
        <p class="section-kicker">Reconcile before submission</p>
        <h2 id="conflictHeading">Reported conflicts</h2>
        <p>A conflict means two reported packet facts do not agree. It is not
          treated as a missing document.</p>
      </div>
      <div class="finding-list">${conflictRows}</div>
    </section>` : ""}

    ${current && (questions.length || data.result.staff_questions.length)
    ? `<section class="packet-ledger" aria-labelledby="questionHeading">
      <div class="ledger-heading">
        <p class="section-kicker">Do not guess</p>
        <h2 id="questionHeading">Items and questions to confirm</h2>
        <p>Use the generated questions to confirm unknown facts, unresolved
          packet assertions, or which City workflow applies.</p>
      </div>
      <div class="finding-list">${questionRows}</div>
      ${directQuestions}
    </section>` : ""}

    ${inventoryMarkup}

    <section class="packet-evidence" aria-labelledby="packetEvidenceHeading">
      <div>
        <p class="section-kicker">Evidence record</p>
        <h2 id="packetEvidenceHeading">Trace this result to its source</h2>
        <p>${esc(data.result.boundary)}</p>
      </div>
      <dl>
        <div>
          <dt>Official source</dt>
          <dd>${sourceLink}</dd>
        </div>
        <div>
          <dt>Source recorded</dt>
          <dd>${esc(formatSourceDate(source.source_checked_on))}</dd>
        </div>
        <div>
          <dt>Review window through</dt>
          <dd>${esc(formatSourceDate(reviewDueOn))}</dd>
        </div>
        ${runtimeSourceStatus}
        <div>
          <dt>AI draft review</dt>
          <dd>${esc(reviewLabel)}</dd>
        </div>
        <div>
          <dt>${current
            ? "Machine-readable record"
            : "Historical machine-readable record"}</dt>
          <dd>${manifestLink}</dd>
        </div>
      </dl>
    </section>`;
  output.setAttribute("aria-busy", "false");
}

function fetchJson(path) {
  return fetch(path).then(response => {
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response.json();
  });
}

function fetchOptionalJson(path, fallback) {
  return fetchJson(path).catch(error => {
    console.warn(`Optional demo data unavailable: ${error.message}`);
    return fallback;
  });
}

function validRuleManifest(manifest) {
  return manifest && manifest.schema_version === 1
    && Array.isArray(manifest.files)
    && manifest.files.length > 0
    && manifest.files.every(file =>
      /^[a-z0-9][a-z0-9-]*\.json$/.test(file) && file !== "index.json"
    );
}

async function fetchRuleData() {
  const manifest = await fetchJson("data/rules/index.json");
  if (!validRuleManifest(manifest))
    throw new Error("data/rules/index.json: invalid rule manifest");
  const files = await Promise.all(
    manifest.files.map(file => fetchJson(`data/rules/${file}`))
  );
  if (!files.every(Array.isArray))
    throw new Error("rule manifest contains a non-list rule file");
  return {rules: files.flat(), rule_manifest: manifest};
}

function loadDemoData() {
  if (globalThis.PERMIT_PATHWAYS_DEMO_DATA) {
    const data = globalThis.PERMIT_PATHWAYS_DEMO_DATA;
    if (!Array.isArray(data.rules) || !validRuleManifest(data.rule_manifest))
      return Promise.reject(new Error("generated demo bundle has invalid rule data"));
    return Promise.resolve(data);
  }
  return Promise.all([
    fetchRuleData(),
    fetchOptionalJson("data/golden/example.json", []),
    fetchOptionalJson("data/sources.json", {}),
    fetchOptionalJson("data/conformance/checks.json", []),
    fetchJson("data/jurisdictions/registry.json"),
    fetchOptionalJson("data/jurisdictions/hcd-letters.json", {letters: {}}),
    fetchOptionalJson("data/conformance/results/index.json", {}),
    fetchOptionalJson("data/explanations/plain-language.json",
                      {schema_version: 1, entries: []}),
  ]).then(([ruleData, golden, sources,
            checks, registry, letters, scans, plainLanguage]) => ({
    rules: ruleData.rules,
    rule_manifest: ruleData.rule_manifest,
    golden, sources, checks, registry, letters, scans,
    plain_language: plainLanguage,
  }));
}

function syncDataControls() {
  const submit = document.getElementById("t-submit");
  const scan = document.getElementById("scanBtn");
  const simulate = document.getElementById("simBtn");
  const reset = document.getElementById("resetBtn");
  if (submit) submit.disabled = !(RULES.length && JURIS.length);
  if (scan) scan.disabled = !CHECKS.length;
  if (simulate) simulate.disabled = !RULES.length;
  if (reset) reset.disabled = !RULES.length;
}

function showDataLoadError(error) {
  console.error("Permit Bearings demo data failed to load", error);
  syncDataControls();
  const message = STRINGS[lang].dataLoadError;
  const status = document.getElementById("resultStatus")
    || document.getElementById("scanStatus")
    || document.getElementById("simulationStatus");
  if (status) {
    status.lang = lang;
    status.textContent = message;
  }
  const output = document.getElementById("dataLoadError")
    || document.getElementById("results")
    || document.getElementById("scanResults")
    || document.getElementById("readinessOutput");
  if (output) {
    output.classList.remove("hidden");
    output.innerHTML =
      `<div class="notice" lang="${lang}">${esc(message)}</div>`;
  }
  const readinessOutput = document.getElementById("readinessOutput");
  if (readinessOutput) {
    readinessOutput.innerHTML = "";
    readinessOutput.setAttribute("aria-busy", "false");
  }
}

async function initializeDemo() {
  if (pageIs("project") && intakeFormElement) renderForm();
  if (ACTIVE_PAGE === "none") return;

  try {
    const data = await loadDemoData();
    RULES = normalizeRules(data.rules);
    GOLDEN = data.golden;
    SOURCES = data.sources;
    CHECKS = data.checks;
    LETTERS = data.letters.letters || {};
    SCANS = data.scans;
    if (pageIs("readiness")) {
      renderReadiness(data.readiness);
    }
    if (pageIs("project")) {
      EXPLANATIONS = await normalizeExplanations(
        data.plain_language,
        RULES,
      );
    }

    const localSlugs = new Set(
      RULES.filter(rule => rule.jurisdiction_scope !== "statewide")
        .map(rule => rule.jurisdiction_scope),
    );
    JURIS = data.registry.jurisdictions.map(jurisdiction => ({
      ...jurisdiction,
      has_local_layer: localSlugs.has(jurisdiction.slug),
    }));
    for (const jurisdiction of JURIS) {
      jurisByName.set(
        jurisDisplay(jurisdiction).toLowerCase(),
        jurisdiction,
      );
      jurisByName.set(jurisdiction.name.toLowerCase(), jurisdiction);
      jurisByName.set(jurisdiction.slug, jurisdiction);
    }

    if (pageIs("project")) {
      const datalist = document.getElementById("jurisList");
      if (datalist) {
        datalist.innerHTML = JURIS.map(
          jurisdiction =>
            `<option value="${esc(jurisDisplay(jurisdiction))}">`,
        ).join("");
      }
      const jurisdictionInput = document.getElementById("jurisInput");
      if (jurisdictionInput) {
        jurisdictionInput.addEventListener("input", () => {
          deactivateProjectSample();
          renderJurisStatus();
        });
      }
      const rehearsalNotice = document.getElementById("projectRehearsal");
      if (rehearsalNotice && simulating) {
        rehearsalNotice.classList.remove("hidden");
      }
    }

    syncDataControls();
    if (pageIs("project") && intakeFormElement) {
      renderForm();
      applyRequestedProjectSample();
    }
    if (pageIs("evidence")) {
      renderDashboard();
      renderSources();
    }
  } catch (error) {
    showDataLoadError(error);
  }
}

initializeDemo();
