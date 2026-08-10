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
    intakeStepPlace: "Step 1 of 3 · Place",
    intakeStepProject: "Step 2 of 3 · Project",
    intakeStepDetails: "Step 3 of 3 · Details",
    sampleLink: "Open a hypothetical detached ADU example",
    sampleSummary: "Made-up project facts run through the same screening logic as any other answers.",
    sampleLabel: "Example project.",
    sampleNotice: "These made-up Woodland ADU facts were screened with the same rules as your answers. They do not describe a real property.",
    sampleResult: "View this sample result",
    sampleClear: "Clear the example and check another project",
    sampleEditedLabel: "Example changed.",
    sampleEditedNotice: "These answers no longer match the made-up Woodland example. The old results were cleared. Choose Check candidate pathways to calculate results from your answers.",
    sampleEditedClear: "Start over with a blank project check",
    resultCleared: "Your answers changed. The previous result was cleared. Choose Check candidate pathways to calculate a new result.",
    sampleUnavailableLabel: "Example unavailable.",
    sampleUnavailableNotice: "The example could not be loaded from its canonical test case. Continue with a blank form.",
    sampleUnavailableClear: "Continue with a blank project check",
    packetSampleTitle: "Explore a future-state packet simulation",
    packetSampleText: "The date-bound City status below does not support a current-plan claim. Confirm the made-up applicability fact only to explore the future-state simulation.",
    packetSampleLink: "Open the future-state simulation",
    journeyStage: "Stage 3 of 4 · Packet",
    journeyApplicabilityLegend: "Is this made-up project using a City of Woodland preapproved ADU plan?",
    journeyApplicabilityHelp: "The public-record-shaped parcel facts in this example are also made up. No parcel was queried or verified.",
    journeyFixedFactsSummary: "See the other made-up applicability facts",
    journeySyntheticParcelFact: field => `Made-up value shaped like the ${field} field in the linked public parcel data.`,
    journeyReadyHeading: "The future-state simulation is ready for these made-up facts",
    journeyReadyText: "Continue to see a hypothetical packet workflow. The English City status below is date-bound; this simulation is not evidence that a usable plan exists today.",
    journeyNoHeading: "This packet example does not apply",
    journeyNoText: "The encoded packet workflow is only for a project using a City of Woodland preapproved ADU plan. Ask staff which current checklist applies.",
    journeyUnknownHeading: "Pause and ask Woodland staff",
    journeyUnavailableHeading: "Packet preparation is on hold",
    journeyUnavailableText: "The versioned route, source status, or packet evidence no longer agrees. Start the made-up example again or take the shown source question to staff.",
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
    profileKicker: "Statewide coverage profile",
    profileSummary: jurisdiction => `Coverage and source records for ${jurisdiction}`,
    profileTitle: "What is recorded for this jurisdiction",
    profileIntro: jurisdiction => `This profile shows the bounded source records committed to this prototype build for ${jurisdiction}. It is decision support, not a finding about a property, current local requirements, or permit approval.`,
    profileAvailable: "Review the coverage profile below.",
    profileStatewideLabel: "Statewide candidate-rule set",
    profileStatewideTitle: count => `${count} bounded candidate-rule records`,
    profileStatewideCopy: "The same limited California ADU, JADU, and SB 9 rule set can be screened after you enter project facts. It can identify candidate pathways to discuss; it does not verify parcel facts, establish eligibility, reproduce local requirements, determine completeness, or predict approval.",
    profileStatewideReviewHoldTitle: (affected, total) => `${affected} of ${total} candidate-rule records need a new source check`,
    profileStatewideReviewHoldCopy: "This inventory is on a source-review hold. Do not treat it as ready to screen until the affected source records are re-verified; see Sources & limits for the source state.",
    profileLocalLabel: "Local requirements",
    profileLocalMissingTitle: "Not encoded",
    profileLocalMissingCopy: jurisdiction => `No jurisdiction-specific rules, forms, fees, or complete checklist are recorded here. Confirm the current ordinance, application materials, fees, process, and parcel-specific conditions with ${jurisdiction} staff.`,
    profileLocalPresentTitle: count => `${count} limited jurisdiction-scoped source record${count === 1 ? "" : "s"}`,
    profileLocalPresentCopy: "These records are not a complete local code or checklist, and do not decide which requirements apply to a project. Review each cited source and confirm current forms, fees, process, and parcel-specific conditions with staff.",
    profileLocalReviewHoldTitle: count => `${count} local source record${count === 1 ? "" : "s"} need${count === 1 ? "s" : ""} a new check`,
    profileLocalReviewHoldCopy: "The raw citation remains visible below, but this local inventory is on a source-review hold. Do not rely on it for coverage until its source is re-verified.",
    profileHcdLabel: "Public HCD record history",
    profileHcdPresentTitle: count => `${count} linked public record${count === 1 ? "" : "s"}`,
    profileHcdPresentCopy: date => `These are public Housing Accountability Unit records linked to this jurisdiction in a dataset retrieved ${date}. They may include technical assistance, inquiries, findings, or other correspondence. They do not establish the current local ordinance, a compliance status, or what applies to a project.`,
    profileHcdNoneTitle: "No linked records in this dataset",
    profileHcdNoneCopy: date => `No HCD record was linked to this jurisdiction in the dataset retrieved ${date}. This is not evidence of compliance, no HCD activity, or complete data coverage.`,
    profileHcdDetails: count => `Show ${count} linked public HCD record${count === 1 ? "" : "s"}`,
    profileHcdReference: "HCD reference",
    profileOnboardingTitle: "What is needed to add a local layer",
    profileOnboarding: "An authorized local maintainer can start with the operative ordinance sections and effective dates; current forms, checklist, fee, and process pages; official URLs plus a source-check date and content fingerprint; project and parcel scope, exceptions, and unresolved questions; and a named review owner with a re-verification cadence. A source link alone does not create a local rule.",
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
    candidateResultTitle: "Candidate route to discuss with staff",
    candidateRouteRecord: "Route record",
    decisionBoundaryHeading: "Decision boundary",
    decisionBoundaryShows: "What this shows",
    decisionBoundaryUnconfirmed: "Still unconfirmed",
    decisionBoundaryNext: "Next step",
    decisionBoundaryCandidateShows: "A candidate route to discuss with staff. It is not an approval.",
    decisionBoundaryCandidateUnconfirmed: "Property facts, local rules, and a complete application checklist.",
    decisionBoundaryCandidateNext: jurisdiction => `Confirm jurisdiction-specific questions with ${jurisdiction} staff.`,
    decisionBoundaryUnknownShows: "Staff review is needed before this prototype can show a candidate route.",
    decisionBoundaryUnknownUnconfirmed: "The facts marked \"I'm not sure.\"",
    decisionBoundaryUnknownNext: jurisdiction => `Confirm those facts with ${jurisdiction} staff.`,
    decisionBoundaryNoRouteShows: "No candidate route was identified in this limited rule set.",
    decisionBoundaryNoRouteUnconfirmed: "Other statewide or local routes may apply.",
    decisionBoundaryNoRouteNext: jurisdiction => `Ask ${jurisdiction} staff to review the project and current local requirements.`,
    decisionBoundarySourceReviewShows: "Source review is needed. Guidance for affected records is withheld.",
    decisionBoundarySourceReviewUnconfirmed: "One or more matching source records need a source check before they can support guidance.",
    decisionBoundarySourceReviewNext: jurisdiction => `Review the source status below and confirm current requirements with ${jurisdiction} staff.`,
    resultCount: count => count === 1 ? "1 result found." : `${count} results found.`,
    answersHeading: "Answers used for this result",
    sampleAnswersHeading: "Sample answers used for this result",
    answersIntro: "We used these answers to compare the project with the limited rules in this prototype. We did not check them against parcel, zoning, or agency records.",
    sampleAnswersIntro: "These answers are made up and do not describe a real property.",
    jurisdictionFact: "Jurisdiction selected",
    projectFact: "Project",
    editAnswers: "Edit these answers",
    statewideStage: "Statewide handoff",
    statewideTitle: "Take this orientation to local staff",
    statewideIntro: (jurisdiction, total) => `This receipt applies the same bounded statewide candidate-rule set available for all ${total} California cities and counties to the answers entered for ${jurisdiction}.`,
    statewideCoverage: "Coverage for this jurisdiction",
    statewideBaselineLabel: "Statewide baseline",
    statewideBaselineValue: "Candidate ADU, JADU, and SB 9 screening is available.",
    statewideLocalLabel: "Local requirements",
    statewideLocalPresent: "A limited jurisdiction-scoped source record is encoded. It is not a complete local code or checklist.",
    statewideLocalMissing: "Not encoded. Confirm the current local ordinance, forms, fees, and process with staff.",
    statewideRoutes: "Candidate routes to discuss",
    statewideNoRoute: "The bounded rules did not identify a candidate route. This is a question for staff, not a finding that the project is impossible.",
    statewideQuestions: "Questions to bring",
    statewideCurrentLocalQuestion: "Which current local ordinance, application form, and checklist apply to this project?",
    statewideFactsQuestion: "Which parcel, zoning, hazard, historic, utility, and prior-permit facts should staff verify?",
    statewideProcessQuestion: "Which department should receive the application, and what local steps or fees are not represented here?",
    statewideBoundary: "Orientation only. This receipt does not verify the property, encode a complete local requirements layer, certify completeness or eligibility, or predict approval. Source-linked explanation and Spanish copy remain review-pending unless their records say otherwise.",
    statewidePrint: "Print or save this orientation",
    statewidePrintHelp: "Your browser handles printing or saving as PDF. Permit Bearings does not upload or store this receipt.",
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
    intakeStepPlace: "Paso 1 de 3 · Lugar",
    intakeStepProject: "Paso 2 de 3 · Proyecto",
    intakeStepDetails: "Paso 3 de 3 · Detalles",
    sampleLink: "Abrir un ejemplo hipotético de una ADU separada",
    sampleSummary: "Los datos inventados del proyecto pasan por la misma lógica de evaluación que cualquier otra respuesta.",
    sampleLabel: "Proyecto de ejemplo.",
    sampleNotice: "Estos datos inventados para una ADU en Woodland se evaluaron con las mismas reglas que sus respuestas. No describen una propiedad real.",
    sampleResult: "Ver el resultado de este ejemplo",
    sampleClear: "Borrar el ejemplo y revisar otro proyecto",
    sampleEditedLabel: "El ejemplo cambió.",
    sampleEditedNotice: "Estas respuestas ya no coinciden con el ejemplo inventado de Woodland. Se borraron los resultados anteriores. Elija Revisar posibles vías para calcular resultados con sus respuestas.",
    sampleEditedClear: "Empezar de nuevo con un formulario en blanco",
    resultCleared: "Sus respuestas cambiaron. Se borró el resultado anterior. Elija Revisar posibles vías para calcular un resultado nuevo.",
    sampleUnavailableLabel: "El ejemplo no está disponible.",
    sampleUnavailableNotice: "No se pudo cargar el ejemplo desde su caso de prueba canónico. Continúe con un formulario en blanco.",
    sampleUnavailableClear: "Continuar con un formulario en blanco",
    packetSampleTitle: "Explore una simulación futura del paquete",
    packetSampleText: "El estado oficial del programa aparece abajo en inglés. Confirme el dato inventado solo para explorar la simulación futura.",
    packetSampleLink: "Abrir la simulación futura en inglés",
    journeyStage: "Etapa 3 de 4 · Paquete",
    journeyApplicabilityLegend: "¿Este proyecto inventado usa un plano de ADU preaprobado por la Ciudad de Woodland?",
    journeyApplicabilityHelp: "Los datos de parcela con formato de registro público también son inventados. No se consultó ni verificó ninguna parcela.",
    journeyFixedFactsSummary: "Ver los demás datos inventados de aplicabilidad",
    journeySyntheticParcelFact: field => `Valor inventado con el formato del campo ${field} en los datos públicos de parcela enlazados.`,
    journeyReadyHeading: "La simulación futura está lista para estos datos inventados",
    journeyReadyText: "Continúe para ver un flujo hipotético. El estado oficial aparece en inglés. No use esta simulación como evidencia de disponibilidad actual.",
    journeyNoHeading: "Este ejemplo de paquete no se aplica",
    journeyNoText: "El flujo codificado solo cubre proyectos que usan un plano de ADU preaprobado por la Ciudad de Woodland. Pregunte al personal qué lista vigente corresponde.",
    journeyUnknownHeading: "Deténgase y pregunte al personal de Woodland",
    journeyUnavailableHeading: "La preparación del paquete está en espera",
    journeyUnavailableText: "La vía versionada, el estado de la fuente o la evidencia del paquete ya no concuerdan. Reinicie el ejemplo inventado o lleve al personal la pregunta de fuente mostrada.",
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
    profileKicker: "Perfil de cobertura estatal",
    profileSummary: jurisdiction => `Cobertura y fuentes registradas para ${jurisdiction}`,
    profileTitle: "Lo que está registrado para esta jurisdicción",
    profileIntro: jurisdiction => `Este perfil muestra los registros de fuentes limitados incluidos en esta versión del prototipo para ${jurisdiction}. Es apoyo para decisiones, no una conclusión sobre una propiedad, requisitos locales vigentes ni la aprobación de un permiso.`,
    profileAvailable: "Revise el perfil de cobertura a continuación.",
    profileStatewideLabel: "Conjunto estatal de reglas posibles",
    profileStatewideTitle: count => `${count} registros limitados de reglas posibles`,
    profileStatewideCopy: "El mismo conjunto limitado de reglas de California para ADU, JADU y SB 9 se puede evaluar después de ingresar los datos del proyecto. Puede identificar posibles vías para consultar; no verifica datos de parcela, no establece elegibilidad, no reproduce requisitos locales, no determina integridad ni predice aprobación.",
    profileStatewideReviewHoldTitle: (affected, total) => `${affected} de ${total} registros de reglas posibles necesitan una nueva comprobación de fuente`,
    profileStatewideReviewHoldCopy: "Este inventario está retenido para revisión de fuentes. No lo trate como listo para evaluar hasta que se vuelvan a verificar las fuentes afectadas; vea Fuentes y límites para conocer el estado de la fuente.",
    profileLocalLabel: "Requisitos locales",
    profileLocalMissingTitle: "No codificados",
    profileLocalMissingCopy: jurisdiction => `Aquí no se registran reglas, formularios, tarifas ni una lista de documentos completa específicos de la jurisdicción. Confirme la ordenanza, los materiales de solicitud, las tarifas, el proceso y las condiciones específicas de la parcela con el personal de ${jurisdiction}.`,
    profileLocalPresentTitle: count => `${count} registro${count === 1 ? "" : "s"} limitado${count === 1 ? "" : "s"} de fuente específica de la jurisdicción`,
    profileLocalPresentCopy: "Estos registros no son un código local ni una lista de documentos completa, y no deciden qué requisitos se aplican a un proyecto. Revise cada fuente citada y confirme con el personal los formularios, las tarifas, el proceso y las condiciones específicas de la parcela vigentes.",
    profileLocalReviewHoldTitle: count => `${count} registro${count === 1 ? "" : "s"} local${count === 1 ? "" : "es"} de fuente necesita${count === 1 ? "" : "n"} una nueva comprobación`,
    profileLocalReviewHoldCopy: "La cita original sigue visible abajo, pero este inventario local está retenido para revisión de fuentes. No lo use para determinar cobertura hasta que se vuelva a verificar su fuente.",
    profileHcdLabel: "Historial de registros públicos de HCD",
    profileHcdPresentTitle: count => `${count} registro${count === 1 ? "" : "s"} público${count === 1 ? "" : "s"} vinculado${count === 1 ? "" : "s"}`,
    profileHcdPresentCopy: date => `Estos son registros públicos de la Unidad de Responsabilidad de Vivienda vinculados a esta jurisdicción en un conjunto de datos recuperado el ${date}. Pueden incluir asistencia técnica, consultas, hallazgos u otra correspondencia. No establecen la ordenanza local actual, un estado de cumplimiento ni lo que se aplica a un proyecto.`,
    profileHcdNoneTitle: "No hay registros vinculados en este conjunto de datos",
    profileHcdNoneCopy: date => `No se vinculó ningún registro de HCD a esta jurisdicción en el conjunto de datos recuperado el ${date}. Esto no es evidencia de cumplimiento, de ausencia de actividad de HCD ni de cobertura completa de datos.`,
    profileHcdDetails: count => `Mostrar ${count} registro${count === 1 ? "" : "s"} público${count === 1 ? "" : "s"} vinculado${count === 1 ? "" : "s"} de HCD`,
    profileHcdReference: "Referencia de HCD",
    profileOnboardingTitle: "Qué se necesita para agregar una capa local",
    profileOnboarding: "Un responsable local autorizado puede empezar con las secciones vigentes de la ordenanza y sus fechas de vigencia; las páginas actuales de formularios, lista de documentos, tarifas y proceso; las URL oficiales más una fecha de comprobación y una huella de contenido; el alcance del proyecto y de la parcela, las excepciones y las preguntas sin resolver; y una persona responsable de la revisión con una cadencia de nueva comprobación. Un enlace de fuente por sí solo no crea una regla local.",
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
    candidateResultTitle: "Posible vía para consultar con el personal",
    candidateRouteRecord: "Registro de la vía",
    decisionBoundaryHeading: "Límites de este resultado",
    decisionBoundaryShows: "Lo que muestra",
    decisionBoundaryUnconfirmed: "Lo que sigue sin confirmar",
    decisionBoundaryNext: "Siguiente paso",
    decisionBoundaryCandidateShows: "Una posible vía para consultar con el personal. No es una aprobación.",
    decisionBoundaryCandidateUnconfirmed: "Datos de la propiedad, reglas locales y una lista completa de requisitos.",
    decisionBoundaryCandidateNext: jurisdiction => `Confirme las preguntas específicas de la jurisdicción con el personal de ${jurisdiction}.`,
    decisionBoundaryUnknownShows: "Se necesita revisión del personal antes de que este prototipo muestre una posible vía.",
    decisionBoundaryUnknownUnconfirmed: "Los datos marcados como \"No lo sé.\"",
    decisionBoundaryUnknownNext: jurisdiction => `Confirme esos datos con el personal de ${jurisdiction}.`,
    decisionBoundaryNoRouteShows: "No se identificó una posible vía en este conjunto limitado de reglas.",
    decisionBoundaryNoRouteUnconfirmed: "Podrían aplicarse otras vías estatales o locales.",
    decisionBoundaryNoRouteNext: jurisdiction => `Pida al personal de ${jurisdiction} que revise el proyecto y los requisitos locales vigentes.`,
    decisionBoundarySourceReviewShows: "Se necesita revisar la fuente. Se ocultan las indicaciones de los registros afectados.",
    decisionBoundarySourceReviewUnconfirmed: "Uno o más registros de fuentes coincidentes necesitan una comprobación antes de respaldar indicaciones.",
    decisionBoundarySourceReviewNext: jurisdiction => `Revise el estado de la fuente indicado y confirme los requisitos vigentes con el personal de ${jurisdiction}.`,
    resultCount: count => count === 1 ? "Se encontró 1 resultado." : `Se encontraron ${count} resultados.`,
    answersHeading: "Respuestas usadas para este resultado",
    sampleAnswersHeading: "Respuestas de ejemplo usadas para este resultado",
    answersIntro: "Usamos estas respuestas para comparar el proyecto con las reglas limitadas de este prototipo. No las verificamos con registros de parcelas, zonificación o de la agencia.",
    sampleAnswersIntro: "Estas respuestas son inventadas y no describen una propiedad real.",
    jurisdictionFact: "Jurisdicción seleccionada",
    projectFact: "Proyecto",
    editAnswers: "Editar estas respuestas",
    statewideStage: "Entrega para cualquier jurisdicción",
    statewideTitle: "Lleve esta orientación al personal local",
    statewideIntro: (jurisdiction, total) => `Este comprobante aplica a las respuestas ingresadas para ${jurisdiction} el mismo conjunto limitado de posibles reglas estatales disponible para las ${total} ciudades y condados de California.`,
    statewideCoverage: "Cobertura para esta jurisdicción",
    statewideBaselineLabel: "Base estatal",
    statewideBaselineValue: "Está disponible la evaluación de posibles vías para ADU, JADU y SB 9.",
    statewideLocalLabel: "Requisitos locales",
    statewideLocalPresent: "Se codificó un registro limitado de fuentes de la jurisdicción. No es un código local ni una lista de documentos completa.",
    statewideLocalMissing: "No están codificados. Confirme con el personal la ordenanza, los formularios, las tarifas y el proceso vigentes.",
    statewideRoutes: "Posibles vías para consultar",
    statewideNoRoute: "Las reglas limitadas no identificaron una posible vía. Es una pregunta para el personal, no una conclusión de que el proyecto sea imposible.",
    statewideQuestions: "Preguntas para llevar",
    statewideCurrentLocalQuestion: "¿Qué ordenanza, formulario de solicitud y lista de documentos locales vigentes corresponden a este proyecto?",
    statewideFactsQuestion: "¿Qué datos de parcela, zonificación, riesgos, patrimonio histórico, servicios públicos y permisos anteriores debe verificar el personal?",
    statewideProcessQuestion: "¿Qué departamento debe recibir la solicitud y qué pasos o tarifas locales no se representan aquí?",
    statewideBoundary: "Solo para orientación. Este comprobante no verifica la propiedad, no codifica todos los requisitos locales, no certifica integridad ni elegibilidad y no predice la aprobación. Las explicaciones vinculadas a fuentes y el texto en español siguen pendientes de revisión, salvo que sus registros indiquen lo contrario.",
    statewidePrint: "Imprimir o guardar esta orientación",
    statewidePrintHelp: "El navegador se encarga de imprimir o guardar como PDF. Permit Bearings no carga ni almacena este comprobante.",
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
let RULE_VERIFICATIONS = null;
let READINESS = null;
let JOURNEY = null;
let SOURCE_STATE = null;
let PROGRAM_AVAILABILITY = null;
let COVERAGE_INDEX = null;
const NORMALIZED_READINESS_DATA = new WeakSet();
const NORMALIZED_PROGRAM_AVAILABILITY = new WeakSet();
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

function committedChangedSourceIds() {
  return typeof SOURCE_STATE !== "undefined"
    && Array.isArray(SOURCE_STATE?.changed_source_ids)
    ? SOURCE_STATE.changed_source_ids : [];
}

function activeChangedSourceIds() {
  const changed = new Set(committedChangedSourceIds());
  if (typeof simulating !== "undefined" && simulating)
    changed.add("ca-gov-66321");
  return [...changed].sort();
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
    return ["https:", "http:"].includes(parsed.protocol)
      && !parsed.username && !parsed.password ? parsed.href : null;
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

function dateIsNotPast(value) {
  if (!validIsoDate(value)) return false;
  const now = new Date();
  const todayUtc = Date.UTC(
    now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()
  );
  return Date.parse(`${value}T00:00:00Z`) >= todayUtc;
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
  return sha256TextFingerprint(stableJson(value));
}

async function sha256TextFingerprint(value) {
  if (!globalThis.crypto || !globalThis.crypto.subtle
      || typeof value !== "string") return null;
  const digest = await globalThis.crypto.subtle.digest(
    "SHA-256", new TextEncoder().encode(value)
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

const PROGRAM_AVAILABILITY_URL =
  "https://www.cityofwoodland.gov/1616/Preapproved-ADU-Plan-Program";
const PROGRAM_AVAILABILITY_BOUNDARY =
  "No currently listed City of Woodland preapproved ADU plan was identified "
  + "on the checked program page. This future-state simulation is not evidence "
  + "that a plan is available; real workflow applicability must be confirmed "
  + "with the City before use.";
const PROGRAM_AVAILABILITY_EXCERPT = "Preapproved ADU List: Coming soon!";
const PROGRAM_TOP_LEVEL_KEYS = ["availability", "schema_version"];
const PROGRAM_RECORD_KEYS = [
  "boundary", "jurisdiction", "mode", "monitoring_status", "program_id",
  "source", "status", "workflow_id",
];
const PROGRAM_SOURCE_KEYS = [
  "checked_on", "excerpt", "excerpt_sha256", "label", "recheck_due_on",
  "source_id", "url",
];

function normalizeProgramExcerpt(value) {
  return typeof value === "string"
    ? value.normalize("NFKC").trim().split(/\s+/u).join(" ") : "";
}

async function normalizeProgramAvailability(payload) {
  try {
    if (!hasExactKeys(payload, PROGRAM_TOP_LEVEL_KEYS, PROGRAM_TOP_LEVEL_KEYS)
        || payload.schema_version !== 1
        || !hasExactKeys(
          payload.availability,
          PROGRAM_RECORD_KEYS,
          PROGRAM_RECORD_KEYS,
        )) return null;
    const record = payload.availability;
    if (record.program_id !== "woodland-preapproved-adu-plan-program"
        || record.workflow_id !== "woodland-preapproved-detached-adu"
        || record.jurisdiction !== "woodland"
        || record.mode !== "future_state_simulation"
        || record.status !== "plans_not_listed"
        || record.monitoring_status !== "manual_date_bound"
        || record.boundary !== PROGRAM_AVAILABILITY_BOUNDARY
        || !hasExactKeys(
          record.source,
          PROGRAM_SOURCE_KEYS,
          PROGRAM_SOURCE_KEYS,
        )) return null;
    const source = record.source;
    if (source.source_id !== "woodland-preapproved-adu-program-page"
        || source.url !== PROGRAM_AVAILABILITY_URL
        || !validHttpsUrl(source.url)
        || !nonBlank(source.label)
        || source.excerpt !== PROGRAM_AVAILABILITY_EXCERPT
        || !dateIsNotFuture(source.checked_on)
        || !dateIsNotPast(source.recheck_due_on)
        || source.recheck_due_on <= source.checked_on
        || (Date.parse(`${source.recheck_due_on}T00:00:00Z`)
          - Date.parse(`${source.checked_on}T00:00:00Z`)) / 86400000 > 31
        || !/^(?:sha256:)[0-9a-f]{64}$/.test(source.excerpt_sha256)) return null;
    const expected = await sha256TextFingerprint(
      normalizeProgramExcerpt(source.excerpt),
    );
    if (!expected || source.excerpt_sha256 !== expected) return null;
    deepFreezeGeneratedData(record);
    if (!generatedDataIsDeeplyFrozen(record)) return null;
    NORMALIZED_PROGRAM_AVAILABILITY.add(record);
    return record;
  } catch {
    return null;
  }
}

function programAvailabilityIsCurrent(
  availability = PROGRAM_AVAILABILITY,
  journey = JOURNEY,
) {
  return Boolean(
    availability
    && NORMALIZED_PROGRAM_AVAILABILITY.has(availability)
    && availability.mode === "future_state_simulation"
    && availability.status === "plans_not_listed"
    && availability.workflow_id === "woodland-preapproved-detached-adu"
    && (!journey
      || availability.workflow_id === journey.readiness_workflow_id)
    && dateIsNotFuture(availability.source.checked_on)
    && dateIsNotPast(availability.source.recheck_due_on),
  );
}

const RULE_VERIFICATION_TOP_LEVEL_KEYS = ["entries", "schema_version"];
const RULE_VERIFICATION_ENTRY_KEYS = [
  "level", "method", "reviewed_citation_fingerprint",
  "reviewed_on", "reviewed_rule_fingerprint", "reviewer", "rule_id",
];
const RULE_VERIFICATION_LEVELS = [
  "machine_linked", "human_reviewed", "jurisdiction_approved",
];

async function normalizeRuleVerifications(payload, rules) {
  try {
    if (!hasExactKeys(
      payload,
      RULE_VERIFICATION_TOP_LEVEL_KEYS,
      RULE_VERIFICATION_TOP_LEVEL_KEYS,
    ) || payload.schema_version !== 2
      || !Array.isArray(payload.entries)
      || payload.entries.length !== rules.length) return null;
    const rulesById = new Map(rules.map(rule => [rule.rule_id, rule]));
    if (rulesById.size !== rules.length) return null;
    const ledger = new Map();
    for (const entry of payload.entries) {
      if (!hasExactKeys(
        entry,
        RULE_VERIFICATION_ENTRY_KEYS,
        RULE_VERIFICATION_ENTRY_KEYS,
      ) || !rulesById.has(entry.rule_id)
        || ledger.has(entry.rule_id)
        || !RULE_VERIFICATION_LEVELS.includes(entry.level)) return null;
      const metadata = [
        entry.reviewer, entry.method, entry.reviewed_on,
        entry.reviewed_citation_fingerprint,
        entry.reviewed_rule_fingerprint,
      ];
      if (entry.level === "machine_linked") {
        if (!metadata.every(value => value === null)) return null;
      } else {
        const rule = rulesById.get(entry.rule_id);
        if (!metadata.every(nonBlank)
            || !dateIsNotFuture(entry.reviewed_on)
            || !validIsoDate(rule.citation.verified_on)
            || entry.reviewed_on < rule.citation.verified_on
            || !/^(?:sha256:)[0-9a-f]{64}$/.test(
              entry.reviewed_citation_fingerprint,
            )
            || !/^(?:sha256:)[0-9a-f]{64}$/.test(
              entry.reviewed_rule_fingerprint,
            )
            || entry.reviewed_citation_fingerprint
              !== await citationFingerprint(rule)
            || entry.reviewed_rule_fingerprint
              !== await ruleFingerprint(rule)) return null;
      }
      const normalized = Object.freeze({...entry});
      ledger.set(entry.rule_id, normalized);
    }
    return ledger.size === rules.length ? ledger : null;
  } catch {
    return null;
  }
}

function effectiveRuleVerification(rule) {
  const entry = RULE_VERIFICATIONS?.get(rule.rule_id);
  const recordedLevel = entry?.level || "machine_linked";
  const sourceStatus = ruleStatus(rule, activeChangedSourceIds());
  if (sourceStatus !== "verified") {
    return {
      level: "machine_linked",
      recordedLevel,
      stale: true,
      reason: sourceStatus === "stale"
        ? "Source dependency changed or review window elapsed; re-verify."
        : "Source evidence has no recorded date; re-verify.",
    };
  }
  if (!RULE_VERIFICATIONS || !entry) {
    return {
      level: "machine_linked",
      recordedLevel,
      stale: true,
      reason: "Verification ledger is missing or invalid; named review is not in force.",
    };
  }
  if (entry.level === "machine_linked") {
    return {level: entry.level, recordedLevel, stale: false, reason: null};
  }
  const now = new Date();
  const todayUtc = Date.UTC(
    now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(),
  );
  const reviewedUtc = Date.parse(`${entry.reviewed_on}T00:00:00Z`);
  const reviewAge = Math.floor((todayUtc - reviewedUtc) / 86400000);
  if (reviewAge < 0 || reviewAge > MAX_AGE_DAYS) {
    return {
      level: "machine_linked",
      recordedLevel,
      stale: true,
      reason: `${recordedLevel} review window elapsed; re-verify.`,
    };
  }
  return {level: recordedLevel, recordedLevel, stale: false, reason: null};
}

const JOURNEY_KEYS = [
  "applicability_facts", "applicability_status", "boundary",
  "candidate_route_rule_ids", "candidate_routes",
  "editable_applicability_fact_ids", "fact_envelope",
  "fact_envelope_fingerprint", "journey_fingerprint", "journey_id", "label",
  "readiness_evidence_manifest", "readiness_packet_fingerprint",
  "readiness_packet_id", "readiness_workflow_fingerprint",
  "readiness_workflow_id", "route_source_review_due_on",
  "route_source_status", "route_source_status_as_of", "schema_version",
  "screening_case_fingerprint", "screening_case_id",
  "screening_expected_rule_ids", "screening_intake", "status", "synthetic",
  "version",
];
const FACT_ENVELOPE_KEYS = [
  "readiness_facts", "schema_version", "screening_facts", "synthetic",
];

function sameStringSet(left, right) {
  if (!Array.isArray(left) || !Array.isArray(right)
      || left.length !== right.length
      || !left.every(validStableId) || !right.every(validStableId)
      || new Set(left).size !== left.length
      || new Set(right).size !== right.length) return false;
  const sortedLeft = [...left].sort();
  const sortedRight = [...right].sort();
  return sortedLeft.every((value, index) => value === sortedRight[index]);
}

const SOURCE_STATE_KEYS = [
  "affected_golden_case_ids", "affected_rule_ids", "changed_source_ids",
  "checked_at", "observations", "receipt", "schema_version", "snapshot_id",
  "source_registry_sha256", "unaffected_golden_case_ids",
  "unaffected_rule_ids", "unverifiable_source_ids",
];
const SOURCE_OBSERVATION_KEYS = [
  "last_verified_on", "observed_sha256", "reason", "recorded_sha256",
  "source_id", "status",
];
const SOURCE_RECEIPT_KEYS = ["commit_sha", "method", "run_url", "status"];

function validSha256(value) {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

function validCommitSha(value) {
  return typeof value === "string" && /^[0-9a-f]{40}$/.test(value);
}

function validUtcTimestamp(value) {
  if (typeof value !== "string"
      || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value)) return false;
  const parsed = new Date(value);
  return !Number.isNaN(parsed.getTime())
    && parsed.toISOString().replace(".000Z", "Z") === value;
}

function exactSortedStringList(value) {
  return Array.isArray(value)
    && value.every(item => typeof item === "string")
    && value.length === new Set(value).size
    && value.every((item, index) => !index || value[index - 1] < item);
}

function sourceStateObservationIsValid(observation, source) {
  if (!hasExactKeys(
    observation,
    SOURCE_OBSERVATION_KEYS,
    SOURCE_OBSERVATION_KEYS,
  ) || !source || source.watch === false
      || observation.source_id !== source.source_id
      || !["unchanged", "changed", "unverifiable"].includes(
        observation.status,
      )
      || observation.recorded_sha256 !== source.sha256
      || observation.last_verified_on !== source.fetched_on
      || !validSha256(observation.recorded_sha256)) return false;
  if (observation.status === "unverifiable") {
    return observation.observed_sha256 === null
      && nonBlank(observation.reason);
  }
  return validSha256(observation.observed_sha256)
    && observation.reason === null
    && (observation.status === "unchanged")
      === (observation.observed_sha256 === observation.recorded_sha256);
}

function sourceImpactLists(changedSourceIds, rules, golden) {
  const changed = new Set(changedSourceIds);
  const affectedRules = rules.filter(rule =>
    rule.source_dependencies.some(sourceId => changed.has(sourceId))
  ).map(rule => rule.rule_id).sort();
  const affectedRuleSet = new Set(affectedRules);
  const unaffectedRules = rules.map(rule => rule.rule_id)
    .filter(ruleId => !affectedRuleSet.has(ruleId)).sort();
  const affectedCases = golden.filter(record =>
    record.rule_dependency_ids.some(ruleId => affectedRuleSet.has(ruleId))
  ).map(record => record.case_id).sort();
  const affectedCaseSet = new Set(affectedCases);
  const unaffectedCases = golden.map(record => record.case_id)
    .filter(caseId => !affectedCaseSet.has(caseId)).sort();
  return {affectedRules, unaffectedRules, affectedCases, unaffectedCases};
}

function normalizeSourceState(data, sources, rules, golden, generatedFrom = {}) {
  if (!hasExactKeys(data, SOURCE_STATE_KEYS, SOURCE_STATE_KEYS)
      || data.schema_version !== 1
      || !validStableId(data.snapshot_id)
      || !validUtcTimestamp(data.checked_at)
      || !validSha256(data.source_registry_sha256)
      || (generatedFrom["data/sources.json"]
        && generatedFrom["data/sources.json"]
          !== data.source_registry_sha256)
      || !hasExactKeys(
        data.receipt,
        SOURCE_RECEIPT_KEYS,
        SOURCE_RECEIPT_KEYS,
      )
      || data.receipt.status !== "reviewed"
      || !nonBlank(data.receipt.method)
      || !safeExternalUrl(data.receipt.run_url)?.startsWith("https://")
      || !validCommitSha(data.receipt.commit_sha)) return null;
  const watched = Object.values(sources)
    .filter(source => source && source.watch !== false && validSha256(source.sha256))
    .sort((left, right) => left.source_id === right.source_id
      ? 0 : left.source_id < right.source_id ? -1 : 1);
  if (!Array.isArray(data.observations)
      || data.observations.length !== watched.length
      || !data.observations.every((observation, index) =>
        sourceStateObservationIsValid(observation, watched[index])
      )) return null;
  const changed = data.observations.filter(item => item.status === "changed")
    .map(item => item.source_id);
  const unverifiable = data.observations
    .filter(item => item.status === "unverifiable")
    .map(item => item.source_id);
  if (!exactSortedStringList(data.changed_source_ids)
      || !exactSortedStringList(data.unverifiable_source_ids)
      || stableJson(data.changed_source_ids) !== stableJson(changed)
      || stableJson(data.unverifiable_source_ids) !== stableJson(unverifiable))
    return null;
  const impact = sourceImpactLists(changed, rules, golden);
  const expected = {
    affected_golden_case_ids: impact.affectedCases,
    affected_rule_ids: impact.affectedRules,
    unaffected_golden_case_ids: impact.unaffectedCases,
    unaffected_rule_ids: impact.unaffectedRules,
  };
  if (!Object.entries(expected).every(([field, value]) =>
    exactSortedStringList(data[field])
      && stableJson(data[field]) === stableJson(value)
  )) return null;
  deepFreezeGeneratedData(data);
  return generatedDataIsDeeplyFrozen(data) ? data : null;
}

function expectedJourneyFactEnvelope(journey, readiness) {
  return {
    readiness_facts: readiness.packet.facts,
    schema_version: 1,
    screening_facts: Object.keys(journey.screening_intake).sort().map(
      factId => ({
        fact_id: factId,
        provenance: "synthetic_golden_fixture",
        value: journey.screening_intake[factId],
      })
    ),
    synthetic: true,
  };
}

function journeyApplicabilityIsBound(journey, readiness) {
  const conditions = readiness.workflow.applicability;
  const definitions = new Map(
    readiness.workflow.facts.map(fact => [fact.fact_id, fact])
  );
  const packetFacts = new Map(
    readiness.packet.facts.map(fact => [fact.fact_id, fact])
  );
  if (!Array.isArray(conditions) || !conditions.length
      || !Array.isArray(journey.applicability_facts)
      || journey.applicability_facts.length !== conditions.length
      || !Array.isArray(journey.editable_applicability_fact_ids)
      || journey.editable_applicability_fact_ids.length !== 1) return false;
  const editableIds = journey.applicability_facts
    .filter(fact => fact.editable === true)
    .map(fact => fact.fact_id);
  if (!sameStringSet(editableIds, journey.editable_applicability_fact_ids))
    return false;
  return conditions.every((condition, index) => {
    const fact = journey.applicability_facts[index];
    const definition = definitions.get(condition.fact_id);
    const packetFact = packetFacts.get(condition.fact_id);
    const boundFields = [
      "fact_id", "value", "provenance", "source_id", "source_field",
      "source_checked_on",
    ];
    return fact && definition && packetFact
      && fact.fact_id === condition.fact_id
      && fact.expected_value === condition.equals
      && fact.value === condition.equals
      && fact.value === packetFact.value
      && boundFields.every(field => fact[field] === packetFact[field])
      && fact.label === definition.label
      && fact.question === definition.question
      && nonBlank(fact.question);
  });
}

async function resolveJourney(journeys, readiness, rules, golden) {
  if (!Array.isArray(journeys) || journeys.length !== 1
      || !Array.isArray(rules) || !Array.isArray(golden)) return null;
  readiness = await normalizeReadinessData(readiness);
  if (!readiness) return null;
  const journey = journeys[0];
  if (!hasExactKeys(journey, JOURNEY_KEYS, JOURNEY_KEYS)
      || journey.schema_version !== 1
      || journey.synthetic !== true
      || journey.status !== "prototype"
      || !validStableId(journey.journey_id)
      || !/^\d+\.\d+\.\d+$/.test(journey.version || "")
      || !nonBlank(journey.label) || !nonBlank(journey.boundary)
      || !journey.screening_intake
      || typeof journey.screening_intake !== "object"
      || Array.isArray(journey.screening_intake)
      || !Array.isArray(journey.screening_expected_rule_ids)
      || !journey.screening_expected_rule_ids.length
      || !Array.isArray(journey.candidate_route_rule_ids)
      || !journey.candidate_route_rule_ids.length
      || !Array.isArray(journey.candidate_routes)
      || !journey.candidate_routes.length
      || !journey.candidate_routes.every(
        route => route && typeof route === "object" && !Array.isArray(route)
      )
      || !Array.isArray(journey.applicability_facts)
      || !journey.applicability_facts.every(
        fact => fact && typeof fact === "object" && !Array.isArray(fact)
      )
      || journey.applicability_status !== "applies"
      || readiness.result.applicability_status !== "applies"
      || journey.readiness_workflow_id !== readiness.workflow.workflow_id
      || journey.readiness_packet_id !== readiness.packet.packet_id
      || journey.readiness_workflow_fingerprint
        !== readiness.result.workflow_fingerprint
      || journey.readiness_packet_fingerprint
        !== readiness.result.packet_fingerprint
      || stableJson(journey.readiness_evidence_manifest)
        !== stableJson(readiness.evidence_manifest)
      || !hasExactKeys(
        journey.fact_envelope,
        FACT_ENVELOPE_KEYS,
        FACT_ENVELOPE_KEYS,
      )
      || !journeyApplicabilityIsBound(journey, readiness)) return null;

  const cases = golden.filter(
    record => record && record.case_id === journey.screening_case_id
  );
  if (cases.length !== 1
      || stableJson(cases[0].intake) !== stableJson(journey.screening_intake)
      || !sameStringSet(
        cases[0].expected_rule_ids,
        journey.screening_expected_rule_ids,
      )) return null;
  const matchedRules = rules.filter(rule =>
    (rule.jurisdiction_scope === "statewide"
      || rule.jurisdiction_scope === journey.screening_intake.jurisdiction)
    && matches(rule, journey.screening_intake)
  );
  const matchedRouteRuleIds = matchedRules
    .filter(rule => rule.display_group === "route")
    .map(rule => rule.rule_id);
  if (!sameStringSet(
    matchedRules.map(rule => rule.rule_id),
    journey.screening_expected_rule_ids,
  ) || !sameStringSet(
    matchedRouteRuleIds,
    journey.candidate_route_rule_ids,
  ) || !sameStringSet(
    journey.candidate_route_rule_ids,
    journey.candidate_routes.map(route => route.rule_id),
  )) return null;

  if (journey.route_source_status !== "current"
      || !validIsoDate(journey.route_source_status_as_of)
      || !validIsoDate(journey.route_source_review_due_on)
      || journey.route_source_status_as_of > journey.route_source_review_due_on
      || journey.route_source_status_as_of !== readiness.result.evaluated_on)
    return null;
  for (const route of journey.candidate_routes) {
    const matchingRules = rules.filter(rule => rule.rule_id === route.rule_id);
    if (matchingRules.length !== 1
        || matchingRules[0].display_group !== "route"
        || route.pathway !== matchingRules[0].pathway
        || route.route_class !== matchingRules[0].route_class
        || route.jurisdiction_scope !== matchingRules[0].jurisdiction_scope
        || stableJson(route.citation)
          !== stableJson(normalizedCitation(matchingRules[0]))
        || !sameStringSet(
          route.source_dependencies,
          matchingRules[0].source_dependencies,
        )
        || route.source_status !== "current"
        || route.source_status_as_of !== journey.route_source_status_as_of
        || !validIsoDate(route.source_review_due_on)
        || route.source_review_due_on < route.source_status_as_of
        || route.rule_fingerprint !== await ruleFingerprint(matchingRules[0]))
      return null;
  }
  const routeReviewDueOn = journey.candidate_routes
    .map(route => route.source_review_due_on).sort()[0];
  if (journey.route_source_review_due_on !== routeReviewDueOn) return null;

  const expectedEnvelope = expectedJourneyFactEnvelope(journey, readiness);
  if (stableJson(journey.fact_envelope) !== stableJson(expectedEnvelope)
      || journey.fact_envelope_fingerprint
        !== await sha256Fingerprint(expectedEnvelope)
      || journey.screening_case_fingerprint
        !== await sha256Fingerprint(cases[0])) return null;
  const {journey_fingerprint: recordedFingerprint, ...unsignedJourney} = journey;
  if (recordedFingerprint !== await sha256Fingerprint(unsignedJourney))
    return null;
  deepFreezeGeneratedData(journey);
  if (!generatedDataIsDeeplyFrozen(journey)) return null;
  return journey;
}

async function normalizeJourney(journeys, readiness, rules, golden) {
  try {
    return await resolveJourney(journeys, readiness, rules, golden);
  } catch {
    return null;
  }
}

function journeySourcesAreCurrent(
  journey,
  readiness,
  rules = RULES,
  changedSourceIds = activeChangedSourceIds(),
) {
  if (!journey || !readiness
      || journey.route_source_status !== "current"
      || !dateIsNotFuture(journey.route_source_status_as_of)
      || !dateIsNotPast(journey.route_source_review_due_on)
      || !readinessSourceIsCurrent(readiness, changedSourceIds)) return false;
  return journey.candidate_route_rule_ids.every(ruleId => {
    const matchesId = rules.filter(rule => rule.rule_id === ruleId);
    return matchesId.length === 1
      && ruleStatus(matchesId[0], changedSourceIds) === "verified";
  });
}

function journeyHandoffState(
  journey,
  readiness,
  intake,
  results,
  applicabilityValue,
  sampleState,
  rules = RULES,
  availability = PROGRAM_AVAILABILITY,
) {
  if (!journey || !readiness)
    return {status: "unavailable"};
  if (sampleState !== "active")
    return {status: "sample_required"};
  if (stableJson(intake) !== stableJson(journey.screening_intake))
    return {status: "intake_mismatch"};
  if (!Array.isArray(results) || !sameStringSet(
    results.map(rule => rule.rule_id),
    journey.screening_expected_rule_ids,
  ) || !journey.candidate_route_rule_ids.every(ruleId =>
    results.some(rule => rule.rule_id === ruleId && rule.display_group === "route")
  )) return {status: "route_mismatch"};
  if (!journeySourcesAreCurrent(journey, readiness, rules))
    return {status: "source_review_required"};
  if (!programAvailabilityIsCurrent(availability, journey))
    return {status: "program_status_review_required"};
  const editableFact = journey.applicability_facts.find(
    fact => fact.editable === true
  );
  if (!editableFact) return {status: "unavailable"};
  if (applicabilityValue === "unknown" || !nonBlank(applicabilityValue))
    return {status: "unknown", question: editableFact.question};
  if (!["yes", "no"].includes(applicabilityValue))
    return {status: "unavailable"};
  if (applicabilityValue !== editableFact.expected_value)
    return {status: "does_not_apply"};
  return {
    status: "simulation_ready",
    href: `prepare.html?journey=${encodeURIComponent(journey.journey_id)}`
      + `&version=${encodeURIComponent(journey.version)}`,
  };
}

function journeyQueryState(
  searchParams,
  journey,
  readiness,
  rules = RULES,
  availability = PROGRAM_AVAILABILITY,
) {
  const keys = [...searchParams.keys()];
  if (!keys.length) return {status: "start_required"};
  if (keys.some(key => !["journey", "version"].includes(key))
      || searchParams.getAll("journey").length !== 1
      || searchParams.getAll("version").length !== 1
      || !journey || !readiness
      || searchParams.get("journey") !== journey.journey_id
      || searchParams.get("version") !== journey.version)
    return {status: "invalid"};
  if (!journeySourcesAreCurrent(journey, readiness, rules))
    return {status: "source_review_required"};
  if (!programAvailabilityIsCurrent(availability, journey))
    return {status: "program_status_review_required"};
  return {status: "simulation_ready"};
}

function journeyEntryHoldMarkup(state) {
  if (state.status === "source_review_required") {
    return `<section class="journey-entry-hold ca-shout" aria-labelledby="entryHoldHeading">
      <p class="journey-stage-label">Stage 3 of 4 · Packet</p>
      <h2 id="entryHoldHeading">Source review is required before using this packet example</h2>
      <p>The route or one of the packet’s bound source records changed or is
        outside its recorded review window. No packet findings are shown as
        current.</p>
      <p><a href="evidence.html">Inspect sources and limits</a></p>
    </section>`;
  }
  if (state.status === "program_status_review_required") {
    return `<section class="journey-entry-hold ca-shout" aria-labelledby="entryHoldHeading">
      <p class="journey-stage-label">Stage 3 of 4 · Packet</p>
      <h2 id="entryHoldHeading">The City program status needs a new check</h2>
      <p>The future-state packet simulation stays locked because its strict
        program-availability record is missing, malformed, or outside its
        recheck window. This is not evidence that a current plan is available.</p>
      <p><a href="${PROGRAM_AVAILABILITY_URL}">Check the official City of
        Woodland program page</a> · <a href="evidence.html">Inspect sources
        and limits</a></p>
    </section>`;
  }
  const invalid = state.status === "invalid";
  return `<section class="journey-entry-hold ca-shout" aria-labelledby="entryHoldHeading">
    <p class="journey-stage-label">Stage 3 of 4 · Packet</p>
    <h2 id="entryHoldHeading">${invalid
      ? "This packet link does not match the current made-up journey"
      : "Start with the made-up Woodland example"}</h2>
    <p>${invalid
      ? "The journey ID or version is missing, duplicated, or different from the generated evidence."
      : "Packet preparation follows the candidate route and its applicability check. No project facts are carried in this URL."}</p>
    <p><a class="button ca-button" href="check.html?sample=adu">
      Open the made-up Woodland example</a></p>
  </section>`;
}

function journeyEvidenceScreeningLabel(factId, projectType) {
  if (factId === "jurisdiction") return "Jurisdiction selected";
  if (factId === "project_type") return "Project";
  return questionLabel(factId, projectType);
}

function journeyEvidenceScreeningValue(factId, value, projectType) {
  if (factId === "jurisdiction" && value === "woodland")
    return "City of Woodland";
  if (factId === "adu_project_form" && value === "new_detached")
    return "New detached ADU";
  return factValueLabel(factId, value, projectType);
}

function journeyEvidenceProvenance(fact) {
  if (fact.provenance === "synthetic_public_record_fixture") {
    const sourceField = nonBlank(fact.source_field)
      ? ` It is shaped like the ${fact.source_field} source field.` : "";
    const recorded = validIsoDate(fact.source_checked_on)
      ? ` Source metadata was recorded ${formatSourceDate(
        fact.source_checked_on,
      )}.` : "";
    return "Fabricated public-record-shaped fixture; no parcel was queried "
      + `or verified.${sourceField}${recorded}`;
  }
  if (fact.provenance === "synthetic_applicant_assertion")
    return "Made-up applicant assertion; not independently checked.";
  return "Made-up canonical screening answer from the synthetic golden "
    + "fixture; not independently checked.";
}

function journeyEvidenceSourceLabel(binding) {
  const source = binding && SOURCES[binding.url];
  return nonBlank(source?.label) ? source.label : binding.source_id;
}

function journeyEvidenceOfficialLink(binding, fallbackLabel) {
  const sourceUrl = safeExternalUrl(binding?.url);
  if (!sourceUrl) return esc(fallbackLabel);
  return `<a href="${esc(sourceUrl)}">${esc(fallbackLabel)}</a>`;
}

function journeyEvidenceRouteMarkup(journey) {
  return `<ul>${journey.candidate_routes.map(route => {
    const citationUrl = safeExternalUrl(route.citation.url);
    const citation = citationUrl
      ? `<a href="${esc(citationUrl)}">${esc(route.citation.source)}</a>`
      : esc(route.citation.source);
    return `<li class="journey-evidence-route-line">
      <h4>${escVerbatim(route.pathway)}</h4>
      <p><strong>Candidate only.</strong> This orientation record does not
        rank or recommend the route, determine eligibility, or predict a
        permit decision.</p>
      <dl>
        <div>
          <dt>Review type recorded</dt>
          <dd>${esc(route.route_class)}</dd>
        </div>
        <div>
          <dt>Rule scope</dt>
          <dd>${esc(route.jurisdiction_scope)}</dd>
        </div>
        <div>
          <dt>Official route source</dt>
          <dd>${citation}; evidence recorded
            ${esc(formatSourceDate(route.citation.verified_on))}</dd>
        </div>
        <div>
          <dt>Recorded source status</dt>
          <dd>${route.source_status === "current" ? "Current" : esc(route.source_status)}
            as of ${esc(formatSourceDate(route.source_status_as_of))};
            review through ${esc(formatSourceDate(
              route.source_review_due_on,
            ))}</dd>
        </div>
      </dl>
    </li>`;
  }).join("")}</ul>`;
}

function journeyEvidenceFactsMarkup(data) {
  const projectType = JOURNEY.screening_intake.project_type;
  const definitions = new Map(
    data.workflow.facts.map(fact => [fact.fact_id, fact])
  );
  const screeningFacts = JOURNEY.fact_envelope.screening_facts.map(fact => ({
    ...fact,
    label: journeyEvidenceScreeningLabel(fact.fact_id, projectType),
    displayValue: journeyEvidenceScreeningValue(
      fact.fact_id,
      fact.value,
      projectType,
    ),
  }));
  const readinessFacts = JOURNEY.fact_envelope.readiness_facts.map(fact => ({
    ...fact,
    label: definitions.get(fact.fact_id).label,
    displayValue: factValueLabel(fact.fact_id, fact.value, projectType),
  }));
  return [...screeningFacts, ...readinessFacts].map(fact => `<div>
    <dt>${esc(fact.label)}</dt>
    <dd><strong>${esc(fact.displayValue)}</strong>
      <span class="journey-evidence-provenance">
        ${esc(journeyEvidenceProvenance(fact))}
      </span>
    </dd>
  </div>`).join("");
}

function journeyEvidenceActionsMarkup(data) {
  const remedies = new Map(
    data.remedies.entries.map(entry => [entry.requirement_id, entry])
  );
  const bindings = new Map(
    data.workflow.source_bindings.map(binding => [binding.source_id, binding])
  );
  return data.result.findings
    .filter(finding => finding.status === "missing")
    .slice(0, 3)
    .map(finding => {
      const remedy = remedies.get(finding.requirement_id);
      const binding = bindings.get(finding.source_id);
      const sourceLink = journeyEvidenceOfficialLink(
        binding,
        journeyEvidenceSourceLabel(binding),
      );
      return `<li>
        <h4>${esc(finding.label)}</h4>
        <p class="journey-evidence-action-review"><strong>AI-assisted
          preparation step · not human-reviewed · review pending</strong></p>
        <p>${esc(remedy.action)}</p>
        <p class="journey-evidence-action-source">Requirement source:
          ${sourceLink}; ${esc(finding.source_locator)}.</p>
      </li>`;
    }).join("");
}

function journeyEvidenceSourcesMarkup(data) {
  const packetStatus = data.result.source_status === "current"
    ? "Current" : data.result.source_status;
  const route = JOURNEY.candidate_routes[0];
  const routeUrl = safeExternalUrl(route.citation.url);
  const routeSource = routeUrl
    ? `<a href="${esc(routeUrl)}">${escVerbatim(route.citation.source)}</a>`
    : escVerbatim(route.citation.source);
  const bindingRows = data.workflow.source_bindings.map(binding => {
    const label = journeyEvidenceSourceLabel(binding);
    const sourceLink = journeyEvidenceOfficialLink(binding, label);
    return `<div>
      <dt>${esc(label)}</dt>
      <dd>${sourceLink}<br>
        Packet evidence ${esc(packetStatus.toLowerCase())} as of
        ${esc(formatSourceDate(readinessSourceStatusAsOf(data)))}; review
        through ${esc(formatSourceDate(readinessReviewDueOn(data)))}.<br>
        Source metadata recorded
        ${esc(formatSourceDate(binding.source_checked_on))}.<br>
        Bound content fingerprint:
        <code>${esc(`sha256:${binding.sha256}`)}</code></dd>
    </div>`;
  }).join("");
  const program = PROGRAM_AVAILABILITY;
  const programRow = programAvailabilityIsCurrent(program, JOURNEY)
    ? `<div>
      <dt>City program availability</dt>
      <dd><a href="${esc(program.source.url)}">${escVerbatim(
        program.source.label,
      )}</a><br>
        <q>${escVerbatim(program.source.excerpt)}</q><br>
        Checked ${esc(formatSourceDate(program.source.checked_on))}; recheck
        due ${esc(formatSourceDate(program.source.recheck_due_on))}. This
        supports a future-state simulation only; it is not evidence that a
        current plan is available. Fingerprint:
        <code>${esc(program.source.excerpt_sha256)}</code></dd>
    </div>` : "";
  return `${programRow}<div>
      <dt>Candidate-route evidence</dt>
      <dd>${routeSource}<br>
        Recorded status ${JOURNEY.route_source_status === "current"
          ? "current" : esc(JOURNEY.route_source_status)} as of
        ${esc(formatSourceDate(JOURNEY.route_source_status_as_of))}; review
        through ${esc(formatSourceDate(
          JOURNEY.route_source_review_due_on,
        ))}. Rule fingerprint:
        <code>${esc(route.rule_fingerprint)}</code></dd>
    </div>
    <div>
      <dt>Packet evidence</dt>
      <dd>${esc(packetStatus)} as of
        ${esc(formatSourceDate(readinessSourceStatusAsOf(data)))}; review
        through ${esc(formatSourceDate(readinessReviewDueOn(data)))}.</dd>
    </div>
    ${bindingRows}
    <div>
      <dt>Generated evidence record</dt>
      <dd><a href="data/readiness/generated/woodland-preapproved-adu-evidence.json">Open
        the generated source-bound JSON manifest</a>. Packet
        <code>${esc(data.packet.packet_id)}</code>; evaluated
        ${esc(formatSourceDate(data.result.evaluated_on))}.</dd>
    </div>`;
}

function renderJourneyEvidenceSummary(data) {
  const section = document.getElementById("journeyEvidenceSummary");
  if (!section) return;
  section.hidden = true;
  const state = journeyQueryState(
    new URLSearchParams(window.location.search),
    JOURNEY,
    data,
  );
  if (state.status !== "simulation_ready"
      || !generatedDataIsDeeplyFrozen(JOURNEY)
      || !NORMALIZED_READINESS_DATA.has(data)
      || !generatedDataIsDeeplyFrozen(data)
      || !validReadinessData(data)) return;

  const requiredIds = [
    "journeyEvidenceId", "journeyEvidenceVersion",
    "journeyEvidenceRouteContent", "journeyEvidenceFactsList",
    "journeyEvidenceActionsReview", "journeyEvidenceActionsList",
    "journeyEvidenceQuestionsList", "journeyEvidenceSourcesList",
    "journeyEvidenceBoundaryText", "printJourneySummary",
  ];
  const elements = new Map(requiredIds.map(id => [
    id,
    document.getElementById(id),
  ]));
  if ([...elements.values()].some(element => !element)) return;

  elements.get("journeyEvidenceId").textContent = JOURNEY.journey_id;
  elements.get("journeyEvidenceVersion").textContent = JOURNEY.version;
  elements.get("journeyEvidenceRouteContent").innerHTML =
    journeyEvidenceRouteMarkup(JOURNEY);
  elements.get("journeyEvidenceFactsList").innerHTML =
    journeyEvidenceFactsMarkup(data);
  elements.get("journeyEvidenceActionsReview").textContent =
    "These are the first three reported missing-item actions. Each is an "
    + "AI-assisted draft, not human-reviewed; review pending.";
  elements.get("journeyEvidenceActionsList").innerHTML =
    journeyEvidenceActionsMarkup(data);
  elements.get("journeyEvidenceQuestionsList").innerHTML =
    data.result.staff_questions.map(question =>
      `<li>${esc(question)}</li>`
    ).join("");
  elements.get("journeyEvidenceSourcesList").innerHTML =
    journeyEvidenceSourcesMarkup(data);
  elements.get("journeyEvidenceBoundaryText").textContent =
    "This summary is a made-up, versioned orientation artifact, not a permit "
    + `decision. ${JOURNEY.boundary} ${data.result.boundary} Printing or `
    + "saving it does not make it an eligibility, legal-sufficiency, "
    + "completeness, or approval finding. Confirm facts, sources, and current "
    + "requirements with Woodland staff.";
  elements.get("printJourneySummary").addEventListener("click", () => {
    window.print();
  });
  section.hidden = false;
}

function renderReadinessEntry(data) {
  const state = journeyQueryState(
    new URLSearchParams(window.location.search),
    JOURNEY,
    data,
  );
  const output = document.getElementById("readinessOutput");
  const cover = document.getElementById("packetCover");
  const summary = document.getElementById("journeyEntrySummary");
  const evidenceSummary = document.getElementById("journeyEvidenceSummary");
  const method = document.getElementById("readinessMethod");
  renderProgramAvailabilityNotice();
  if (state.status !== "simulation_ready") {
    if (cover) cover.hidden = true;
    if (summary) summary.hidden = true;
    if (evidenceSummary) evidenceSummary.hidden = true;
    if (method) method.hidden = true;
    output.innerHTML = journeyEntryHoldMarkup(state);
    output.setAttribute("aria-busy", "false");
    return;
  }
  if (cover) cover.hidden = false;
  if (summary) {
    summary.hidden = false;
    document.getElementById("journeyEntryId").textContent = JOURNEY.journey_id;
    document.getElementById("journeyEntryVersion").textContent = JOURNEY.version;
  }
  if (method) method.hidden = false;
  renderReadiness(data);
  renderJourneyEvidenceSummary(data);
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
const CANDIDATE_ROUTE_BY_PROJECT = Object.freeze({
  adu: "adu-ministerial-review",
  jadu: "jadu-ministerial-review",
  two_unit: "sb9-two-unit-ministerial",
  lot_split: "sb9-urban-lot-split",
});

function radioQuestion(name, legend, options, help = "") {
  const helpId = `${name}-help`;
  const describedBy = help ? ` aria-describedby="${helpId}"` : "";
  return `<fieldset data-question="${esc(name)}"${describedBy} class="ca-field">
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
  container.innerHTML = `<div class="intake-stage-heading">
      <p class="intake-step" id="intakeStepDetails">${esc(s.intakeStepDetails)}</p>
      <p class="small">${esc(s.questionIntro)}</p>
    </div>${questions}`;
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
                         "sampleLabel", "sampleNotice", "sampleResult",
                         "sampleClear", "intakeStepPlace",
                         "intakeStepProject"];
  translatedIds.forEach(id => { document.getElementById(id).lang = lang; });
  document.getElementById("t-tagline").textContent = s.tagline;
  document.getElementById("translationScope").textContent = s.translationScope;
  document.getElementById("sampleLink").textContent = s.sampleLink;
  document.getElementById("sampleSummary").textContent = s.sampleSummary;
  document.getElementById("sampleResult").textContent = s.sampleResult;
  renderProjectSampleText();
  document.getElementById("screenHeading").textContent = s.screenHeading;
  document.getElementById("t-juris").textContent = s.juris;
  document.getElementById("jurisHelp").textContent = s.jurisHelp;
  document.getElementById("t-project").textContent = s.project;
  document.getElementById("intakeStepPlace").textContent = s.intakeStepPlace;
  document.getElementById("intakeStepProject").textContent = s.intakeStepProject;
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

function projectFactRecords() {
  if (!LAST_INTAKE || !LAST_JURISDICTION) return [];
  const s = STRINGS[lang];
  const projectType = LAST_INTAKE.project_type;
  return [
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
}

function renderProjectFacts() {
  const facts = projectFactRecords();
  if (!facts.length) return "";
  const s = STRINGS[lang];
  const isSample = projectSampleState === "active";
  return `<details class="result-cover-sheet result-support ca-box"
      aria-labelledby="projectFactsHeading" lang="${lang}">
    <summary class="result-support-summary" id="projectFactsHeading">
      <span class="result-support-title">
        ${esc(isSample ? s.sampleAnswersHeading : s.answersHeading)}
      </span>
    </summary>
    <div class="result-support-body">
      <p class="small">${esc(isSample ? s.sampleAnswersIntro : s.answersIntro)}</p>
      <p><a class="edit-answers" href="#screenHeading">${esc(s.editAnswers)}</a></p>
      <dl class="result-facts">
        ${facts.map(fact => `<div data-field="${esc(fact.name)}">
          <dt>${esc(fact.label)}</dt>
          <dd>${esc(fact.value)}</dd>
        </div>`).join("")}
      </dl>
    </div>
  </details>`;
}

function decisionBoundaryMarkup(state) {
  const s = STRINGS[lang];
  const jurisdiction = jurisDisplay(LAST_JURISDICTION);
  const copy = {
    candidate: {
      shows: s.decisionBoundaryCandidateShows,
      unconfirmed: s.decisionBoundaryCandidateUnconfirmed,
      next: s.decisionBoundaryCandidateNext(jurisdiction),
    },
    unknown: {
      shows: s.decisionBoundaryUnknownShows,
      unconfirmed: s.decisionBoundaryUnknownUnconfirmed,
      next: s.decisionBoundaryUnknownNext(jurisdiction),
    },
    "no-route": {
      shows: s.decisionBoundaryNoRouteShows,
      unconfirmed: s.decisionBoundaryNoRouteUnconfirmed,
      next: s.decisionBoundaryNoRouteNext(jurisdiction),
    },
    "source-review-hold": {
      shows: s.decisionBoundarySourceReviewShows,
      unconfirmed: s.decisionBoundarySourceReviewUnconfirmed,
      next: s.decisionBoundarySourceReviewNext(jurisdiction),
    },
  }[state];
  if (!copy) return "";
  const rows = [
    ["shows", s.decisionBoundaryShows, copy.shows],
    ["unconfirmed", s.decisionBoundaryUnconfirmed, copy.unconfirmed],
    ["next", s.decisionBoundaryNext, copy.next],
  ];
  return `<aside class="decision-boundary ca-box" id="decisionBoundary"
      data-boundary-state="${esc(state)}" role="note"
      aria-labelledby="decisionBoundaryHeading" lang="${lang}">
    <h3 id="decisionBoundaryHeading">${esc(s.decisionBoundaryHeading)}</h3>
    <dl>${rows.map(([name, label, value]) => `<div data-boundary-part="${name}">
      <dt>${esc(label)}</dt><dd>${esc(value)}</dd>
    </div>`).join("")}</dl>
  </aside>`;
}

function statewideOrientationMarkup(list = [], unresolved = []) {
  if (!LAST_INTAKE || !LAST_JURISDICTION) return "";
  const s = STRINGS[lang];
  const facts = projectFactRecords();
  const candidateRoutes = list.filter(rule => resultGroup(rule) === "route");
  const routeItems = candidateRoutes.map(rule => {
    const status = ruleStatus(rule, activeChangedSourceIds());
    const statusLabel = status === "verified"
      ? s.verifiedOn(formatSourceDate(rule.citation.verified_on))
      : status === "stale" ? s.stale : s.unverified;
    return `<li>
      <strong lang="${lang}">${esc(s.candidateResultTitle)}</strong>
      <span class="small"><span lang="${lang}">${esc(s.candidateRouteRecord)}:</span>
        <span lang="en">${escVerbatim(rule.pathway)}</span></span>
      <span class="small" lang="en">${esc(rule.citation.source)}</span>
      <span class="small" lang="${lang}">${esc(statusLabel)}</span>
    </li>`;
  }).join("");
  const questions = [
    ...unresolved.map(name => questionLabel(name, LAST_INTAKE.project_type)),
    s.statewideCurrentLocalQuestion,
    s.statewideFactsQuestion,
    s.statewideProcessQuestion,
  ];
  const jurisdiction = jurisDisplay(LAST_JURISDICTION);
  const localCoverage = LAST_JURISDICTION.has_local_layer
    ? s.statewideLocalPresent : s.statewideLocalMissing;
  return `<details class="statewide-orientation result-support ca-box" id="statewideOrientation"
      aria-labelledby="statewideOrientationHeading" lang="${lang}"
      data-jurisdiction="${esc(LAST_JURISDICTION.slug)}"
      data-local-layer="${LAST_JURISDICTION.has_local_layer ? "true" : "false"}">
    <summary class="result-support-summary">
      <span class="statewide-orientation-stage">${esc(s.statewideStage)}</span>
      <span class="result-support-title" id="statewideOrientationHeading">${esc(s.statewideTitle)}</span>
    </summary>
    <div class="statewide-orientation-body">
      <p>${esc(s.statewideIntro(jurisdiction, JURIS.length))}</p>
      <section class="statewide-orientation-coverage"
        aria-labelledby="statewideCoverageHeading">
      <h4 id="statewideCoverageHeading">${esc(s.statewideCoverage)}</h4>
      <dl>
        <div><dt>${esc(s.statewideBaselineLabel)}</dt>
          <dd>${esc(s.statewideBaselineValue)}</dd></div>
        <div><dt>${esc(s.statewideLocalLabel)}</dt>
          <dd>${esc(localCoverage)}</dd></div>
      </dl>
    </section>
    <section aria-labelledby="statewideFactsHeading">
      <h4 id="statewideFactsHeading">${esc(s.answersHeading)}</h4>
      <dl class="statewide-orientation-facts">
        ${facts.map(fact => `<div><dt>${esc(fact.label)}</dt>
          <dd>${esc(fact.value)}</dd></div>`).join("")}
      </dl>
    </section>
    <section aria-labelledby="statewideRoutesHeading">
      <h4 id="statewideRoutesHeading">${esc(s.statewideRoutes)}</h4>
      ${routeItems ? `<ul class="statewide-route-list">${routeItems}</ul>`
        : `<p class="notice ca-shout">${esc(s.statewideNoRoute)}</p>`}
    </section>
    <section aria-labelledby="statewideQuestionsHeading">
      <h4 id="statewideQuestionsHeading">${esc(s.statewideQuestions)}</h4>
      <ul>${questions.map(question => `<li>${esc(question)}</li>`).join("")}</ul>
    </section>
    <p class="statewide-orientation-boundary">${esc(s.statewideBoundary)}</p>
      <div class="statewide-print-action">
        <button class="button ca-button print-statewide-orientation" type="button">
          ${esc(s.statewidePrint)}</button>
        <p class="small">${esc(s.statewidePrintHelp)}</p>
      </div>
    </div>
  </details>`;
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
  const status = ruleStatus(rule, activeChangedSourceIds());
  const ok = status === "verified";
  const badge = ok
    ? `<span class="badge info" lang="${lang}"><span class="status-ico" aria-hidden="true">◷</span>${esc(s.verifiedOn(formatSourceDate(c.verified_on)))}</span>`
    : status === "stale"
    ? `<span class="badge bad" lang="${lang}"><span class="status-ico" aria-hidden="true">✕</span>${esc(s.stale)}</span>`
    : `<span class="badge warn" lang="${lang}"><span class="status-ico" aria-hidden="true">⚠</span>${esc(s.unverified)}</span>`;
  const localizedRecord = ok ? usableLocalizedExplanation(explanation) : null;
  let consequence = status === "unverified"
    ? `<div class="notice ca-shout small" lang="${lang}">${esc(s.withheldUnverified)}</div>`
    : status === "stale"
    ? `<div class="notice ca-shout small" lang="${lang}">${esc(s.withheldStale)}</div>`
    : `<div class="notice ca-shout small" lang="${lang}">${esc(s.unavailable)}</div>`;
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
  if (group === "route") {
    displayTitle = s.candidateResultTitle;
    displayTitleLang = lang;
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
    && CANDIDATE_ROUTE_BY_PROJECT[LAST_INTAKE?.project_type] === rule.rule_id;
  const clockLink = ok
    && LAST_INTAKE?.project_type === "adu"
    && isConfiguredRoute
    ? `<p class="result-tool-link" lang="${lang}">
        <a href="#clocks">${esc(s.checkDates)}</a>
      </p>` : "";
  const routeRecord = group === "route"
    ? `<p class="candidate-route-record small" aria-hidden="true"><span lang="${lang}">${esc(s.candidateRouteRecord)}:</span>
        <span lang="en">${escVerbatim(rule.pathway)}</span></p>`
    : "";
  const routeHeadingIdentity = group === "route"
    ? `<span class="visually-hidden" lang="${lang}">${esc(s.candidateRouteRecord)}:
        <span lang="en">${escVerbatim(rule.pathway)}</span></span>`
    : "";
  return `<article id="rule-${safeId}"
      class="card result-card ca-card ${isConfiguredRoute ? "result-route" : "result-card-compact"} ${ok ? "" : "unverified"}"
      data-rule-id="${esc(rule.rule_id)}" data-result-group="${group}"
      aria-labelledby="result-title-${safeId}" tabindex="-1">
    <div class="result-head">
      <h4 class="result-title" id="result-title-${safeId}"
        lang="${displayTitleLang}"><span class="result-title-visible">${esc(displayTitle)}${group === "route" ? "." : ""}</span>${routeHeadingIdentity}</h4>
      ${badge}
    </div>
    ${routeRecord}
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

function programAvailabilityStatusMarkup(availability = PROGRAM_AVAILABILITY) {
  if (!programAvailabilityIsCurrent(availability)) {
    return `<div class="program-availability program-availability-hold ca-shout" lang="en">
      <p class="utility-label">Official program status</p>
      <p><strong>Program status review required.</strong> The strict City
        program record is missing, malformed, or outside its recheck window.
        The future-state packet simulation remains locked.</p>
      <p><a href="${PROGRAM_AVAILABILITY_URL}">Check the official City of
        Woodland program page</a>.</p>
    </div>`;
  }
  const source = availability.source;
  return `<div class="program-availability ca-shout" lang="en">
    <p class="utility-label">Official program status</p>
    <p><strong>Future-state simulation only.</strong> The City page says
      <q>${escVerbatim(source.excerpt)}</q></p>
    <p>Checked ${esc(formatSourceDate(source.checked_on))}; recheck due
      ${esc(formatSourceDate(source.recheck_due_on))}.
      <a href="${esc(source.url)}">Open the official City of Woodland program
      page</a>.</p>
    <p>This record is not evidence that a current preapproved plan is
      available. Confirm program applicability with the City before use.</p>
  </div>`;
}

function renderProgramAvailabilityNotice() {
  const notice = document.getElementById("programAvailabilityNotice");
  if (notice) notice.innerHTML = programAvailabilityStatusMarkup();
}

function journeyGateOutcomeMarkup(state) {
  const s = STRINGS[lang];
  if (state.status === "simulation_ready") {
    return `<div class="journey-outcome ca-shout">
      <h4>${esc(s.journeyReadyHeading)}</h4>
      <p>${esc(s.journeyReadyText)}</p>
      <p><a class="button ca-button" href="${esc(state.href)}">
        ${esc(s.packetSampleLink)}</a></p>
    </div>`;
  }
  if (state.status === "does_not_apply") {
    return `<div class="journey-outcome journey-outcome-hold ca-shout">
      <h4>${esc(s.journeyNoHeading)}</h4>
      <p>${esc(s.journeyNoText)}</p>
    </div>`;
  }
  if (state.status === "unknown") {
    return `<div class="journey-outcome journey-outcome-hold ca-shout">
      <h4>${esc(s.journeyUnknownHeading)}</h4>
      <p lang="en">${esc(state.question)}</p>
    </div>`;
  }
  return `<div class="journey-outcome journey-outcome-hold ca-shout">
    <h4>${esc(s.journeyUnavailableHeading)}</h4>
    <p>${esc(s.journeyUnavailableText)}</p>
  </div>`;
}

function renderJourneyHandoffOutcome() {
  const output = document.getElementById("journeyGateOutcome");
  if (!output) return;
  const state = journeyHandoffState(
    JOURNEY,
    READINESS,
    LAST_INTAKE,
    LAST_RESULTS,
    journeyApplicabilityValue,
    projectSampleState,
  );
  output.innerHTML = journeyGateOutcomeMarkup(state);
}

function journeyHandoffMarkup() {
  if (projectSampleState !== "active") return "";
  const s = STRINGS[lang];
  if (!JOURNEY) {
    return `<aside class="journey-handoff ca-box" lang="${lang}"
        aria-labelledby="journeyGateHeading">
      <p class="journey-stage-label">${esc(s.journeyStage)}</p>
      <h3 id="journeyGateHeading">${esc(s.journeyUnavailableHeading)}</h3>
      <div id="journeyGateOutcome" role="status" aria-live="polite">
        ${journeyGateOutcomeMarkup({status: "unavailable"})}
      </div>
    </aside>`;
  }
  const editableFact = JOURNEY.applicability_facts.find(
    fact => fact.editable === true
  );
  if (!editableFact) return "";
  if (!programAvailabilityIsCurrent(PROGRAM_AVAILABILITY, JOURNEY)) {
    return `<aside class="journey-handoff ca-box" lang="${lang}"
        aria-labelledby="journeyGateHeading">
      <p class="journey-stage-label">${esc(s.journeyStage)}</p>
      <h3 id="journeyGateHeading">${esc(s.journeyUnavailableHeading)}</h3>
      ${programAvailabilityStatusMarkup()}
      <div id="journeyGateOutcome" role="status" aria-live="polite">
        ${journeyGateOutcomeMarkup({
          status: "program_status_review_required",
        })}
      </div>
    </aside>`;
  }
  const fixedFacts = JOURNEY.applicability_facts.filter(
    fact => fact.editable !== true
  );
  const yesLabel = STRINGS[lang].tri.find(([value]) => value === "yes")[1];
  const options = STRINGS[lang].tri.map(([value, label]) =>
    `<label><input type="radio" name="journey_applicability"
      value="${esc(value)}"
      ${journeyApplicabilityValue === value ? "checked" : ""}>
      ${esc(label)}</label>`
  ).join("");
  return `<aside class="journey-handoff ca-box" lang="${lang}"
      aria-labelledby="journeyGateHeading">
    <p class="journey-stage-label">${esc(s.journeyStage)}</p>
    <h3 id="journeyGateHeading">${esc(s.packetSampleTitle)}</h3>
    <p>${esc(s.packetSampleText)}</p>
    ${programAvailabilityStatusMarkup()}
    <fieldset class="ca-field" aria-describedby="journeyApplicabilityHelp">
      <legend>${esc(s.journeyApplicabilityLegend)}</legend>
      <p class="small" id="journeyApplicabilityHelp">
        ${esc(s.journeyApplicabilityHelp)}</p>
      <div class="choice-grid">${options}</div>
    </fieldset>
    <details class="journey-fixed-facts">
      <summary lang="${lang}">${esc(s.journeyFixedFactsSummary)}</summary>
      <ul lang="${lang}">${fixedFacts.map(fact =>
        `<li><strong lang="en">${esc(fact.label)}:</strong> ${esc(yesLabel)}.
          ${esc(s.journeySyntheticParcelFact(fact.source_field))}</li>`
      ).join("")}</ul>
    </details>
    <div id="journeyGateOutcome" role="status" aria-live="polite"></div>
  </aside>`;
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
    el.innerHTML = `<h2 class="result-heading" id="resultsHeading"
        tabindex="-1" lang="${lang}">${esc(s.results)}</h2>
      ${decisionBoundaryMarkup("no-route")}
      <div class="notice ca-shout" lang="${lang}">${esc(s.none)}</div>
      ${renderProjectFacts()}
      ${statewideOrientationMarkup()}`;
    return;
  }
  const grouped = groupResultRecords(list);
  const summaryText = resultSummaryText(grouped);
  const sourceReviewHold = list.some(rule =>
    ruleStatus(rule, activeChangedSourceIds()) !== "verified"
  );
  const boundaryState = sourceReviewHold
    ? "source-review-hold" : hasRoute ? "candidate" : "no-route";
  status.textContent = hasRoute
    ? `${summaryText} ${s.resultIntro} ${s.routeOrientation}`
    : `${summaryText} ${s.none} ${s.supportingOnly}`;
  const shownExplanations = list.map(rule => {
    if (ruleStatus(rule, activeChangedSourceIds()) !== "verified") return null;
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
  const packetSampleLink = journeyHandoffMarkup();
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
    const section = `<section class="result-group ${group === "local_process" ? "result-local" : ""}"
        aria-labelledby="result-group-${group}">
          <h3 id="result-group-${group}" tabindex="-1"
            lang="${lang}">${esc(s.groups[group])}</h3>
          ${localBoundary}<div class="result-records">${cards}</div>
        </section>`;
    return section;
  }).join("");
  const draftBanner = oneSharedDraftLabel
    ? `<div class="result-trust-note ca-shout small" lang="${lang}">${esc(s.explanationBanner)}</div>`
    : "";
  const noRouteNotice = hasRoute
    ? ""
    : `<div class="notice ca-shout" lang="${lang}">
        <p>${esc(s.none)}</p>
        <p>${esc(s.supportingOnly)}</p>
      </div>`;
  el.innerHTML = `<h2 class="result-heading" id="resultsHeading"
      tabindex="-1" lang="${lang}">${esc(s.results)}</h2>
    ${decisionBoundaryMarkup(boundaryState)}
    <p class="result-count" lang="${lang}">${esc(summaryText)}</p>
    <p class="small result-limit" lang="${lang}">${esc(s.resultIntro)}
      ${hasRoute ? esc(s.routeOrientation) : ""}</p>
    ${noRouteNotice}${draftBanner}${renderResultIndex(grouped)}${sections}
    ${packetSampleLink}
    ${renderProjectFacts()}
    ${statewideOrientationMarkup(list)}`;
  renderJourneyHandoffOutcome();
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
    `<h2 class="result-heading" id="resultsHeading" tabindex="-1"
        lang="${lang}">
        ${esc(s.unknownHeading)}
      </h2>
      ${decisionBoundaryMarkup("unknown")}
      <div class="notice ca-shout" lang="${lang}">
        <p>${esc(s.unknownIntro)}</p>
        <ul>${fieldNames.map(name =>
          `<li>${esc(questionLabel(name, LAST_INTAKE?.project_type))}</li>`
        ).join("")}</ul>
      </div>
      ${renderProjectFacts()}
      ${statewideOrientationMarkup([], fieldNames)}`;
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
let journeyApplicabilityValue = null;

function renderProjectSampleText() {
  const s = STRINGS[lang];
  let suffix = "";
  if (projectSampleState === "edited") suffix = "Edited";
  if (projectSampleState === "unavailable") suffix = "Unavailable";
  document.getElementById("sampleLabel").textContent =
    s[`sample${suffix}Label`];
  document.getElementById("sampleNotice").textContent =
    s[`sample${suffix}Notice`];
  document.getElementById("sampleResult").hidden =
    projectSampleState !== "active";
  document.getElementById("sampleClear").textContent =
    s[`sample${suffix}Clear`];
}

function storeSubmittedProject(intake, jurisdiction) {
  LAST_INTAKE = {...intake};
  LAST_JURISDICTION = {
    county: jurisdiction.county,
    has_local_layer: jurisdiction.has_local_layer === true,
    kind: jurisdiction.kind,
    name: jurisdiction.name,
    slug: jurisdiction.slug,
  };
  OPEN_RULE_IDS.clear();
}

function invalidateRenderedProjectResult(message = "") {
  LAST_RESULTS = null;
  LAST_UNRESOLVED = null;
  LAST_INTAKE = null;
  LAST_JURISDICTION = null;
  journeyApplicabilityValue = null;
  OPEN_RULE_IDS.clear();
  const results = document.getElementById("results");
  if (results) results.innerHTML = "";
  const status = document.getElementById("resultStatus");
  if (status) status.textContent = message;
}

const resultContainerElement = document.getElementById("results");
if (pageIs("project") && resultContainerElement) {
  resultContainerElement.addEventListener("click", event => {
    const printButton = event.target.closest?.(".print-statewide-orientation");
    if (printButton) {
      window.print();
      return;
    }
    const clockLink = event.target.closest?.('a[href="#clocks"]');
    if (clockLink) {
      const clockDisclosure = document.getElementById("clocks");
      if (clockDisclosure) clockDisclosure.open = true;
      return;
    }
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
  resultContainerElement.addEventListener("change", event => {
    const input = event.target;
    if (input.name !== "journey_applicability") return;
    journeyApplicabilityValue = input.value;
    renderJourneyHandoffOutcome();
  });
}

function renderDashboard() {
  document.getElementById("ruleTable")?.classList?.add(
    "ca-inner-border",
    "ca-outer-border",
    "ca-stripes",
  );
  const changed = activeChangedSourceIds();
  const statuses = RULES.map(rule => ({
    rule,
    st: ruleStatus(rule, changed),
    verification: effectiveRuleVerification(rule),
  }));
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
  const verificationCounts = {
    machine_linked: 0,
    human_reviewed: 0,
    jurisdiction_approved: 0,
  };
  statuses.forEach(({verification}) => {
    verificationCounts[verification.level] += 1;
  });
  const namedReview = verificationCounts.human_reviewed
    + verificationCounts.jurisdiction_approved;
  const verificationScore = document.getElementById("verificationScore");
  const verificationLine = document.getElementById("verificationLine");
  if (verificationScore)
    verificationScore.textContent = `${namedReview}/${total}`;
  if (verificationLine) {
    verificationLine.textContent = RULE_VERIFICATIONS
      ? `${verificationCounts.machine_linked} machine-linked; `
        + `${verificationCounts.human_reviewed} human-reviewed; `
        + `${verificationCounts.jurisdiction_approved} jurisdiction-approved.`
      : "The ledger is missing or invalid. All rules fail closed to "
        + "machine-linked; no named review is in force.";
  }
  document.querySelector("#ruleTable tbody").innerHTML = statuses.map(({
    rule,
    st,
    verification,
  }) => {
    const b = st === "verified"
      ? `<span class="badge ok"><span class="status-ico" aria-hidden="true">✓</span>within review window</span>`
      : st === "stale"
      ? `<span class="badge bad"><span class="status-ico" aria-hidden="true">✕</span>STALE: re-verify</span>`
      : `<span class="badge warn"><span class="status-ico" aria-hidden="true">⚠</span>no dated source record</span>`;
    const verificationLabel = verification.level === "jurisdiction_approved"
      ? "Jurisdiction-approved"
      : verification.level === "human_reviewed"
      ? "Human-reviewed"
      : verification.stale
      ? "Machine-linked · source/review hold"
      : "Machine-linked · no named review";
    const verificationClass = verification.level === "jurisdiction_approved"
      ? "ok" : verification.level === "human_reviewed" ? "ok" : "warn";
    const verificationIcon = verification.level === "machine_linked"
      ? "⚙" : "✓";
    const verificationBadge = `<span class="badge ${verificationClass}"
      ${verification.reason ? `title="${esc(verification.reason)}"` : ""}>
      <span class="status-ico" aria-hidden="true">${verificationIcon}</span>
      ${esc(verificationLabel)}</span>`;
    return `<tr><td data-label="Rule">${esc(rule.pathway)}</td>
      <td data-label="Scope" class="mutedtxt">${esc(rule.jurisdiction_scope)}</td>
      <td data-label="Source status">${b}</td>
      <td data-label="Interpretation review">${verificationBadge}</td></tr>`;
  }).join("");
  document.getElementById("simNote").classList.toggle("hidden", !simulating);
  document.getElementById("simBtn").classList.toggle("hidden", simulating);
  document.getElementById("resetBtn").classList.toggle("hidden", !simulating);
}

function sourceStateOperationalImpact(changedSourceIds) {
  const impact = sourceImpactLists(changedSourceIds, RULES, GOLDEN);
  const changed = new Set(changedSourceIds);
  const routeChanged = JOURNEY?.candidate_routes?.some(route =>
    route.source_dependencies.some(sourceId => changed.has(sourceId))
  ) || false;
  const readinessChanged = READINESS?.workflow?.source_bindings?.some(
    binding => changed.has(binding.source_id),
  ) || false;
  const surfaces = [];
  if (impact.affectedRules.length) {
    surfaces.push(
      `${impact.affectedRules.length} dependent rule card${impact.affectedRules.length === 1 ? "" : "s"} and the matching statewide orientation receipts`,
    );
  }
  if (impact.affectedCases.length) {
    surfaces.push(
      `${impact.affectedCases.length} structured regression scenario${impact.affectedCases.length === 1 ? "" : "s"} queued for replay`,
    );
  }
  if (routeChanged) surfaces.push("the Woodland route-to-packet handoff");
  if (readinessChanged) {
    surfaces.push(
      "the Woodland packet findings, draft actions, and print summary",
    );
  }
  return {...impact, surfaces};
}

function renderSourceState() {
  const summary = document.getElementById("sourceSnapshotSummary");
  const queue = document.getElementById("sourceImpactQueue");
  const runLink = document.getElementById("sourceSnapshotRun");
  if (!summary || !queue || !runLink || !SOURCE_STATE) return;
  const counts = {unchanged: 0, changed: 0, unverifiable: 0};
  SOURCE_STATE.observations.forEach(item => counts[item.status]++);
  summary.textContent = `Checked ${formatSourceDate(
    SOURCE_STATE.checked_at.slice(0, 10),
  )}: ${counts.unchanged} unchanged; ${counts.changed} changed; `
    + `${counts.unverifiable} could not be re-fetched. This repository-adopted `
    + "receipt is the source-state overlay used by the applicant guide.";
  runLink.href = SOURCE_STATE.receipt.run_url;
  const impact = sourceStateOperationalImpact(SOURCE_STATE.changed_source_ids);
  const queueParts = [];
  if (SOURCE_STATE.changed_source_ids.length) {
    queueParts.push(`<p><strong>Review queue open.</strong>
      ${SOURCE_STATE.changed_source_ids.length} changed source${SOURCE_STATE.changed_source_ids.length === 1 ? "" : "s"}
      affect ${impact.affectedRules.length} rule record${impact.affectedRules.length === 1 ? "" : "s"}
      and ${impact.affectedCases.length} structured scenario${impact.affectedCases.length === 1 ? "" : "s"}.</p>`);
    if (impact.surfaces.length) {
      queueParts.push(`<ul>${impact.surfaces.map(surface =>
        `<li>${esc(surface)}</li>`
      ).join("")}</ul>`);
    }
  } else {
    queueParts.push(
      "<p><strong>No source-triggered review queue is open.</strong> "
      + "No fetched source in this committed snapshot changed.</p>",
    );
  }
  if (SOURCE_STATE.unverifiable_source_ids.length) {
    const unverifiableCount = SOURCE_STATE.unverifiable_source_ids.length;
    const unavailableCopy = unverifiableCount === 1
      ? "1 source was not re-fetched. Its recorded date still controls"
      : `${unverifiableCount} sources were not re-fetched. Their recorded dates still control`;
    queueParts.push(`<p><strong>Watch warning.</strong>
      ${unavailableCopy}; no dependent was marked stale solely because a
      download failed.</p>`);
  }
  queue.innerHTML = queueParts.join("");
  queue.classList.remove("hidden");
}

function renderSources() {
  document.getElementById("sourceTable")?.classList?.add(
    "ca-inner-border",
    "ca-outer-border",
    "ca-stripes",
  );
  const observations = new Map(
    (SOURCE_STATE?.observations || []).map(item => [item.source_id, item]),
  );
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
      const observation = observations.get(metadata.source_id);
      let monitoring = `<span class="badge info">reference only</span>`;
      if (watched && observation?.status === "unchanged") {
        monitoring = `<span class="badge ok"><span class="status-ico"
          aria-hidden="true">✓</span>unchanged in snapshot</span>`;
      } else if (watched && observation?.status === "changed") {
        monitoring = `<span class="badge bad"><span class="status-ico"
          aria-hidden="true">✕</span>changed · review required</span>`;
      } else if (watched && observation?.status === "unverifiable") {
        monitoring = `<span class="badge warn"><span class="status-ico"
          aria-hidden="true">⚠</span>could not re-fetch</span>`;
      }
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
       <div class="notice ca-shout">${esc(s.jurisRequired)}</div></div>`;
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

function coverageRuleRecords(ruleIds) {
  const rulesById = new Map(RULES.map(rule => [rule.rule_id, rule]));
  return ruleIds.map(ruleId => rulesById.get(ruleId) || null);
}

function coverageRuleStatus(rule) {
  return rule ? ruleStatus(rule, activeChangedSourceIds()) : "unverified";
}

function profileSourceStatusMarkup(status) {
  if (status === "verified") return "";
  const s = STRINGS[lang];
  const stale = status === "stale";
  const label = stale ? s.stale : s.unverified;
  return `<span class="badge ${stale ? "bad" : "warn"}" lang="${lang}">
    <span class="status-ico" aria-hidden="true">${stale ? "✕" : "⚠"}</span>${esc(label)}</span>`;
}

function localCoverageRecordMarkup(ruleIds) {
  return `<ul class="jurisdiction-profile-local-records">${coverageRuleRecords(
    ruleIds,
  ).map((rule, index) => {
    const ruleId = rule?.rule_id || ruleIds[index];
    const sourceUrl = safeExternalUrl(rule?.citation?.url);
    const pathway = rule?.pathway || ruleId;
    const source = rule?.citation?.source || ruleId;
    const sourceStatus = coverageRuleStatus(rule);
    const sourceLink = sourceUrl
      ? `<a lang="en" href="${esc(sourceUrl)}" rel="noopener">${esc(pathway)}</a>`
      : `<strong lang="en">${esc(pathway)}</strong>`;
    const checked = rule?.citation?.verified_on
      ? formatSourceDate(rule.citation.verified_on) : "";
    return `<li data-rule-id="${esc(ruleId)}" data-source-status="${sourceStatus}">
      ${sourceLink}<span lang="en">${esc(source)}</span>${checked
      ? `<span lang="${lang}">${esc(checked)}</span>` : ""}
      ${profileSourceStatusMarkup(sourceStatus)}</li>`;
  }).join("")}</ul>`;
}

function hcdCoverageRecordMarkup(records, jurisdiction) {
  const s = STRINGS[lang];
  const jurisdictionLabel = jurisDisplay(jurisdiction);
  return `<details>
    <summary>${esc(s.profileHcdDetails(records.length))}</summary>
    <ul class="jurisdiction-profile-letter-list">${records.map(record => {
      const item = record && typeof record === "object" ? record : {};
      const date = formatSourceDate(item.date || "");
      const hasKind = nonBlank(item.kind);
      const kind = hasKind ? item.kind : s.profileHcdReference;
      const authority = nonBlank(item.authority) ? item.authority : "";
      const hauNumber = nonBlank(item.hau_number) ? item.hau_number : "";
      const recordUrl = safeExternalUrl(item.url);
      const label = kind;
      const accessibleLabel = [
        `HCD record for ${jurisdictionLabel}`,
        kind,
        item.date || "recorded date unavailable",
        authority,
        hauNumber,
      ].filter(Boolean).join("; ");
      const title = recordUrl
        ? `<a lang="${hasKind ? "en" : lang}" aria-label="${esc(accessibleLabel)}"
            href="${esc(recordUrl)}" rel="noopener">${esc(label)}</a>`
        : `<strong lang="${hasKind ? "en" : lang}">${esc(label)}</strong>`;
      const metadata = [authority, hauNumber].filter(Boolean).join(" · ");
      return `<li>${date ? `<span lang="${lang}">${esc(date)} · </span>` : ""}${title}${metadata
        ? `<span class="small" lang="en">${esc(metadata)}</span>` : ""}</li>`;
    }).join("")}</ul>
  </details>`;
}

function renderJurisdictionProfile(jurisdiction) {
  const output = document.getElementById("jurisdictionProfile");
  if (!output) return;
  if (!jurisdiction || !COVERAGE_INDEX) {
    output.open = false;
    output.hidden = true;
    output.innerHTML = "";
    delete output.dataset.jurisdiction;
    delete output.dataset.localLayer;
    delete output.dataset.hcdRecordCount;
    delete output.dataset.statewideReviewHold;
    delete output.dataset.localReviewHold;
    return;
  }
  const profile = COVERAGE_INDEX.profiles[jurisdiction.slug];
  if (!profile) {
    output.open = false;
    output.hidden = true;
    output.innerHTML = "";
    delete output.dataset.jurisdiction;
    delete output.dataset.localLayer;
    delete output.dataset.hcdRecordCount;
    delete output.dataset.statewideReviewHold;
    delete output.dataset.localReviewHold;
    return;
  }

  const s = STRINGS[lang];
  const localRuleIds = profile.local_rule_ids;
  const statewideRules = coverageRuleRecords(COVERAGE_INDEX.statewide_rule_ids);
  const statewideReviewHoldCount = statewideRules.filter(rule =>
    coverageRuleStatus(rule) !== "verified",
  ).length;
  const localReviewHoldCount = coverageRuleRecords(localRuleIds).filter(rule =>
    coverageRuleStatus(rule) !== "verified",
  ).length;
  const hcdRecords = LETTERS[jurisdiction.slug] || [];
  const hasLocalRecords = localRuleIds.length > 0;
  const hcdTitle = hcdRecords.length
    ? s.profileHcdPresentTitle(hcdRecords.length) : s.profileHcdNoneTitle;
  const hcdCopy = hcdRecords.length
    ? s.profileHcdPresentCopy(
      formatSourceDate(COVERAGE_INDEX.hcd_dataset.retrieved_on),
    )
    : s.profileHcdNoneCopy(
      formatSourceDate(COVERAGE_INDEX.hcd_dataset.retrieved_on),
    );
  const location = jurisdiction.kind === "county"
    ? jurisdiction.name : jurisdiction.county;
  const localTitle = hasLocalRecords
    ? localReviewHoldCount
      ? s.profileLocalReviewHoldTitle(localReviewHoldCount)
      : s.profileLocalPresentTitle(localRuleIds.length)
    : s.profileLocalMissingTitle;
  const localCopy = hasLocalRecords
    ? localReviewHoldCount
      ? s.profileLocalReviewHoldCopy
      : s.profileLocalPresentCopy
    : s.profileLocalMissingCopy(jurisDisplay(jurisdiction));
  const statewideTitle = statewideReviewHoldCount
    ? s.profileStatewideReviewHoldTitle(
      statewideReviewHoldCount,
      COVERAGE_INDEX.statewide_rule_ids.length,
    )
    : s.profileStatewideTitle(COVERAGE_INDEX.statewide_rule_ids.length);
  const statewideCopy = statewideReviewHoldCount
    ? s.profileStatewideReviewHoldCopy : s.profileStatewideCopy;

  if (output.dataset.jurisdiction !== jurisdiction.slug) output.open = false;
  output.lang = lang;
  output.dataset.jurisdiction = jurisdiction.slug;
  output.dataset.localLayer = hasLocalRecords ? "true" : "false";
  output.dataset.hcdRecordCount = String(hcdRecords.length);
  output.dataset.statewideReviewHold = String(statewideReviewHoldCount);
  output.dataset.localReviewHold = String(localReviewHoldCount);
  output.innerHTML = `<summary id="jurisdictionProfileHeading">
      <span class="jurisdiction-profile-kicker">${esc(s.profileKicker)}</span>
      <span class="jurisdiction-profile-summary-title">${esc(s.profileSummary(
        jurisDisplay(jurisdiction),
      ))}</span>
      <span class="jurisdiction-profile-summary-meta">${esc(statewideTitle)} · ${esc(localTitle)}</span>
    </summary>
    <div class="jurisdiction-profile-body">
      <div class="jurisdiction-profile-header">
        <h3>${esc(s.profileTitle)}</h3>
        <p class="jurisdiction-profile-location">${esc(location)}</p>
      </div>
      <p class="jurisdiction-profile-intro">${esc(s.profileIntro(
        jurisDisplay(jurisdiction),
      ))}</p>
      <dl class="jurisdiction-profile-ledger">
      <div>
        <dt>${esc(s.profileStatewideLabel)}</dt>
        <dd><strong>${esc(statewideTitle)}</strong><span class="small">${esc(statewideCopy)}</span></dd>
      </div>
      <div>
        <dt>${esc(s.profileLocalLabel)}</dt>
        <dd><strong>${esc(localTitle)}</strong><span class="small">${esc(localCopy)}</span>
          ${hasLocalRecords ? localCoverageRecordMarkup(localRuleIds) : ""}</dd>
      </div>
      <div>
        <dt>${esc(s.profileHcdLabel)}</dt>
        <dd><strong>${esc(hcdTitle)}</strong><span class="small">${esc(hcdCopy)}</span>
          ${hcdRecords.length
            ? hcdCoverageRecordMarkup(hcdRecords, jurisdiction) : ""}</dd>
      </div>
      </dl>
      <aside class="jurisdiction-profile-onboarding" role="note">
        <strong>${esc(s.profileOnboardingTitle)}</strong><br>
        ${esc(s.profileOnboarding)}
      </aside>
    </div>`;
  output.hidden = false;
}

function renderJurisStatus(showError = false) {
  const s = STRINGS[lang];
  const el = document.getElementById("jurisStatus");
  const input = document.getElementById("jurisInput");
  const raw = document.getElementById("jurisInput").value.trim();
  if (!raw) {
    renderJurisdictionProfile(null);
    if (el.textContent) el.textContent = "";
    input.removeAttribute("aria-invalid");
    return;
  }
  const j = resolveJurisdiction();
  if (!j) {
    renderJurisdictionProfile(null);
    if (el.textContent !== s.statusUnknown) el.textContent = s.statusUnknown;
    if (showError) input.setAttribute("aria-invalid", "true");
    return;
  }
  input.removeAttribute("aria-invalid");
  renderJurisdictionProfile(j);
  const localCount = JURIS.filter(x => x.has_local_layer).length;
  let html = j.has_local_layer
    ? `<strong>${esc(s.localMetadata)}.</strong> ${esc(s.statusLocal)}`
    : `${esc(s.statusBaseline)} (${esc(s.localCoverage(localCount, JURIS.length))})`;
  html += ` ${esc(s.profileAvailable)}`;
  const scanRec = SCANS[j.slug];
  if (scanRec) {
    const scanPath = safeLocalJsonPath(j.slug);
    const scanLink = scanPath
      ? `: <a href="${esc(scanPath)}" rel="noopener">${esc(s.viewScan)}</a>`
      : "";
    html += `<br><span class="badge info">${esc(s.scanned)}</span> ` +
      `${esc(s.scanRecord(scanRec.scanned_on, scanRec.findings))}${scanLink}.`;
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
    el.innerHTML = `<div class="notice ca-shout">No candidate provisions flagged.
      Presence-based screen only. This is <b>not</b> a certification of compliance.</div>`;
    status.textContent = "No candidate provisions were flagged. This is only a presence-based screen.";
    return;
  }
  el.innerHTML = findings.map(f => {
    const definite = f.check.severity === "definite";
    return `<div class="card ca-card ${definite ? "" : "unverified"}"
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
  el.innerHTML = `<section class="clock-output ca-box" aria-labelledby="clockOutputHeading">
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
  const committed = committedChangedSourceIds();
  const rehearsal = [...new Set([...committed, "ca-gov-66321"])];
  if (pageIs("evidence")) {
    return RULES.filter(rule =>
      ruleStatus(rule, committed) === "verified"
      && ruleStatus(rule, rehearsal) === "stale"
    ).length;
  }
  if (LAST_RESULTS === null) return 0;
  return LAST_RESULTS.filter(rule =>
    ruleStatus(rule, committed) === "verified"
    && ruleStatus(rule, rehearsal) === "stale"
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

const READINESS_INVENTORY_STATUSES = new Set([
  "present",
  "missing",
  "unknown",
  "conflicting",
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

const READINESS_APPLICABILITY_STATUSES = new Set([
  "applies",
  "unknown",
  "does_not_apply",
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
      || data.packet.jurisdiction !== data.workflow.jurisdiction
      || data.packet.project_type !== data.workflow.project_type
      || data.result.workflow_id !== data.workflow.workflow_id
      || data.result.packet_id !== data.packet.packet_id
      || !/^sha256:[0-9a-f]{64}$/.test(
        data.result.workflow_fingerprint || ""
      )
      || !/^sha256:[0-9a-f]{64}$/.test(
        data.result.packet_fingerprint || ""
      )
      || !validIsoDate(data.packet.evaluated_on)
      || !validIsoDate(data.result.evaluated_on)
      || data.result.evaluated_on !== data.packet.evaluated_on
      || !readinessReviewDueOn(data)
      || !readinessSourceStatusAsOf(data)
      || !READINESS_OVERALL_STATUSES.has(data.result.overall_status)
      || !READINESS_SOURCE_STATUSES.has(data.result.source_status)
      || !READINESS_APPLICABILITY_STATUSES.has(
        data.result.applicability_status
      )
      || data.evidence_manifest.applicability_status
        !== data.result.applicability_status
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
      || !Array.isArray(data.packet.inventory)
      || data.workflow.requirements.length !== data.packet.inventory.length
      || !Array.isArray(data.result.findings)
      || data.workflow.requirements.length !== data.result.findings.length
      || !Array.isArray(data.remedies.entries)
      || data.remedies.entries.length !== data.workflow.requirements.length
      || data.remedies.workflow_id !== data.workflow.workflow_id
      || !/^sha256:[0-9a-f]{64}$/.test(
        data.remedies.workflow_fingerprint || ""
      )
      || !/^\d+\.\d+\.\d+$/.test(data.remedies.version || "")
      || !/^sha256:[0-9a-f]{64}$/.test(
        data.remedies.content_fingerprint || ""
      )
      || !validIsoDate(data.remedies.updated_on)
      || data.remedies.updated_on > data.result.evaluated_on
      || data.remedies.drafted_by !== "ai_assisted"
      || !Array.isArray(data.result.staff_questions)
      || !data.result.staff_questions.every(nonBlank)
      || !nonBlank(data.result.boundary)) return false;
  const requirementIds = data.workflow.requirements.map(
    requirement => requirement.requirement_id
  );
  const factIds = data.workflow.facts.map(fact => fact.fact_id);
  const packetFactIds = data.packet.facts.map(fact => fact.fact_id);
  const inventoryIds = data.packet.inventory.map(
    item => item.requirement_id
  );
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
  const reviewDateValid = review?.status === "prototype_review_pending"
    || (
      dateIsNotFuture(review?.reviewed_on)
      && review.reviewed_on >= data.remedies.updated_on
      && review.reviewed_on <= data.result.evaluated_on
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
  const applicabilityMatchesFindings = data.result.source_status !== "current"
    || {
      applies: data.result.overall_status !== "outside_bounded_workflow",
      unknown: data.result.overall_status === "needs_review"
        && data.counts.not_evaluated === data.result.findings.length,
      does_not_apply:
        data.result.overall_status === "outside_bounded_workflow"
        && data.counts.not_evaluated === data.result.findings.length,
    }[data.result.applicability_status] === true;
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
    && inventoryIds.every(validStableId)
    && new Set(inventoryIds).size === inventoryIds.length
    && inventoryIds.every(id => requirementIds.includes(id))
    && data.packet.inventory.every(item =>
      READINESS_INVENTORY_STATUSES.has(item.status)
    )
    && findingIds.every((id, index) => id === requirementIds[index])
    && new Set(remedyIds).size === remedyIds.length
    && remedyIds.every(id => requirementIds.includes(id))
    && data.result.findings.every((finding, index) => {
      const requirement = data.workflow.requirements[index];
      return nonBlank(finding.reason)
        && READINESS_FINDING_STATUSES.has(finding.status)
        && finding.label === requirement.label
        && finding.category === requirement.category
        && finding.source_id === requirement.source_id
        && finding.source_locator === requirement.source_locator
        && finding.source_excerpt === requirement.source_excerpt;
    })
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
    && reviewDateValid
    && countsMatch
    && overallMatchesFindings
    && applicabilityMatchesFindings;
}

function readinessEvidenceManifest(data, workflowFingerprint, packetFingerprint) {
  const counts = {};
  for (const status of READINESS_FINDING_STATUSES) {
    counts[status] = data.result.findings.filter(
      finding => finding.status === status
    ).length;
  }
  return {
    applicability_status: data.result.applicability_status,
    boundary: data.result.boundary,
    counts,
    evaluated_on: data.result.evaluated_on,
    facts: data.packet.facts,
    findings: data.result.findings,
    inventory: data.packet.inventory,
    manifest_type: "prototype_packet_presence",
    overall_status: data.result.overall_status,
    packet_fingerprint: packetFingerprint,
    packet_id: data.result.packet_id,
    schema_version: 1,
    source_bindings: data.workflow.source_bindings,
    source_review_due_on: data.result.source_review_due_on,
    source_status: data.result.source_status,
    source_status_as_of: data.result.source_status_as_of,
    staff_questions: data.result.staff_questions,
    synthetic: data.packet.synthetic,
    workflow_fingerprint: workflowFingerprint,
    workflow_id: data.result.workflow_id,
  };
}

async function normalizeReadinessData(data) {
  try {
    if (data && typeof data === "object"
        && NORMALIZED_READINESS_DATA.has(data)
        && generatedDataIsDeeplyFrozen(data)) return data;
    if (!validReadinessData(data)) return null;
    const [workflowFingerprint, packetFingerprint] = await Promise.all([
      sha256Fingerprint(data.workflow),
      sha256Fingerprint(data.packet),
    ]);
    if (workflowFingerprint !== data.result.workflow_fingerprint
        || workflowFingerprint !== data.remedies.workflow_fingerprint
        || data.ai_trace?.output_workflow_fingerprint !== workflowFingerprint
        || data.ai_trace?.output_remedy_version !== data.remedies.version
        || packetFingerprint !== data.result.packet_fingerprint)
      return null;

    const requirementFingerprints = new Map(await Promise.all(
      data.workflow.requirements.map(async requirement => [
        requirement.requirement_id,
        await sha256Fingerprint(requirement),
      ])
    ));
    const remedyById = new Map(
      data.remedies.entries.map(entry => [entry.requirement_id, entry])
    );
    if (!data.result.findings.every(finding => {
      const fingerprint = requirementFingerprints.get(finding.requirement_id);
      return fingerprint === finding.requirement_fingerprint
        && fingerprint
          === remedyById.get(finding.requirement_id)?.requirement_fingerprint;
    })) return null;

    if (stableJson(data.evidence_manifest) !== stableJson(
      readinessEvidenceManifest(
        data,
        workflowFingerprint,
        packetFingerprint,
      )
    )) return null;

    const remedyContentFingerprint = await sha256Fingerprint({
      entries: data.remedies.entries,
      version: data.remedies.version,
      workflow_id: data.remedies.workflow_id,
    });
    if (data.remedies.content_fingerprint !== remedyContentFingerprint
        || data.ai_trace?.output_remedy_content_fingerprint
          !== remedyContentFingerprint)
      return null;
    const review = data.remedies.review;
    if (review.status !== "prototype_review_pending"
        && review.content_fingerprint !== remedyContentFingerprint)
      return null;
    deepFreezeGeneratedData(data);
    if (!generatedDataIsDeeplyFrozen(data)) return null;
    NORMALIZED_READINESS_DATA.add(data);
    return data;
  } catch {
    return null;
  }
}

function deepFreezeGeneratedData(value) {
  if (!value || typeof value !== "object" || Object.isFrozen(value))
    return value;
  for (const nested of Object.values(value)) deepFreezeGeneratedData(nested);
  return Object.freeze(value);
}

function generatedDataIsDeeplyFrozen(value) {
  if (!value || typeof value !== "object") return true;
  return Object.isFrozen(value)
    && Object.values(value).every(generatedDataIsDeeplyFrozen);
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
  return `<section class="packet-evidence ca-box"
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

function readinessSourceIsCurrent(
  data,
  changedSourceIds = [],
) {
  if (data.result.source_status !== "current") return false;
  const readinessSourceIds = data.workflow.source_bindings
    .map(binding => binding.source_id);
  if (changedSourceIds.some(sourceId =>
    readinessSourceIds.includes(sourceId)
  )) return false;
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
  return `<article class="packet-finding packet-finding-${tone} ca-card">
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
        "One or more dated source records bound to this packet changed or fell outside the recorded review window.",
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
  if (!NORMALIZED_READINESS_DATA.has(data)
      || !generatedDataIsDeeplyFrozen(data)
      || !validReadinessData(data))
    throw new Error("generated packet-presence data failed validation");
  const output = document.getElementById("readinessOutput");
  const remedyById = new Map(
    data.remedies.entries.map(entry => [entry.requirement_id, entry])
  );
  const current = readinessSourceIsCurrent(
    data,
    typeof activeChangedSourceIds === "function"
      ? activeChangedSourceIds() : [],
  );
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
    ? `<div class="staff-question-list ca-shout">
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
    : `<p class="source-review-hold ca-shout"><strong>Action copy is
        withheld.</strong> The dated source must be checked before this
        result can be used again.</p>`;
  const inventoryMarkup = current
    ? `<section class="packet-inventory ca-box" aria-labelledby="inventoryHeading">
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
    <section class="readiness-verdict ca-shout ${current ? "is-current" : "needs-source"}"
      aria-labelledby="readinessVerdictHeading">
      <div class="verdict-copy">
        <p class="section-kicker">Deterministic packet-presence result</p>
        <h2 id="readinessVerdictHeading">${esc(summary.headline)}</h2>
        <p>${esc(summary.intro)}</p>
      </div>
      ${countsMarkup}
    </section>

    ${readinessParcelEvidenceMarkup(data, current)}

    ${current && missing.length ? `<section class="packet-ledger ca-box"
      aria-labelledby="missingHeading">
      <div class="ledger-heading">
        <p class="section-kicker">Act before submission</p>
        <h2 id="missingHeading">Reported missing items</h2>
        <p>${esc(reviewLabel)}</p>
      </div>
      <div class="finding-list">${missingRows}</div>
    </section>` : ""}

    ${current && conflicts.length ? `<section class="packet-ledger ca-box"
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
    ? `<section class="packet-ledger ca-box" aria-labelledby="questionHeading">
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

    <section class="packet-evidence ca-box" aria-labelledby="packetEvidenceHeading">
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

function sameStringArray(left, right) {
  return Array.isArray(left) && Array.isArray(right)
    && left.length === right.length
    && left.every((value, index) => value === right[index]);
}

function countLetterContainer(value) {
  if (Array.isArray(value)) return value.length;
  if (!value || typeof value !== "object") return null;
  let total = 0;
  for (const records of Object.values(value)) {
    if (!Array.isArray(records)) return null;
    total += records.length;
  }
  return total;
}

function normalizeCoverageIndex(data, rules, jurisdictions, letterData) {
  const required = [
    "schema_version", "statewide_rule_ids", "hcd_dataset", "profiles",
  ];
  if (!hasExactKeys(data, required, required) || data.schema_version !== 1
      || !Array.isArray(data.statewide_rule_ids)
      || !data.statewide_rule_ids.every(validStableId)
      || new Set(data.statewide_rule_ids).size !== data.statewide_rule_ids.length
      || !sameStringArray(
        data.statewide_rule_ids,
        [...data.statewide_rule_ids].sort(),
      )
      || !data.profiles || typeof data.profiles !== "object"
      || Array.isArray(data.profiles)) {
    throw new Error("statewide coverage index failed validation");
  }

  const expectedStatewideRuleIds = rules
    .filter(rule => rule.jurisdiction_scope === "statewide")
    .map(rule => rule.rule_id)
    .sort();
  if (!sameStringArray(data.statewide_rule_ids, expectedStatewideRuleIds))
    throw new Error("statewide coverage index disagrees with the rule inventory");

  const hcdDatasetKeys = [
    "retrieved_on", "letter_count", "source", "statewide_record_count",
    "unmatched_record_count",
  ];
  const hcdDataset = data.hcd_dataset;
  if (!hasExactKeys(hcdDataset, hcdDatasetKeys, hcdDatasetKeys)
      || !dateIsNotFuture(hcdDataset.retrieved_on)
      || !nonBlank(hcdDataset.source)
      || ![
        hcdDataset.letter_count,
        hcdDataset.statewide_record_count,
        hcdDataset.unmatched_record_count,
      ].every(value => isRuleInteger(value) && value >= 0)) {
    throw new Error("statewide coverage index has invalid HCD metadata");
  }

  if (!letterData || typeof letterData !== "object"
      || !letterData.letters || typeof letterData.letters !== "object"
      || Array.isArray(letterData.letters)) {
    throw new Error("HCD letter data failed validation");
  }
  const letterMap = letterData.letters;
  const profiledRecordCount = countLetterContainer(letterMap);
  const statewideRecordCount = countLetterContainer(letterData._statewide);
  const unmatchedRecordCount = countLetterContainer(letterData._unmatched);
  if (profiledRecordCount == null || statewideRecordCount == null
      || unmatchedRecordCount == null
      || hcdDataset.letter_count !== (
        profiledRecordCount + statewideRecordCount + unmatchedRecordCount
      )
      || hcdDataset.statewide_record_count !== statewideRecordCount
      || hcdDataset.unmatched_record_count !== unmatchedRecordCount
      || hcdDataset.retrieved_on !== letterData.retrieved_on
      || hcdDataset.source !== letterData.source) {
    throw new Error("statewide coverage index disagrees with HCD letter data");
  }

  const expectedSlugs = jurisdictions.map(jurisdiction => jurisdiction.slug).sort();
  const suppliedSlugs = Object.keys(data.profiles).sort();
  if (!sameStringArray(suppliedSlugs, expectedSlugs))
    throw new Error("statewide coverage index does not cover the registry");

  for (const jurisdiction of jurisdictions) {
    const profile = data.profiles[jurisdiction.slug];
    const profileKeys = ["local_rule_ids", "hcd_record_count"];
    if (!hasExactKeys(profile, profileKeys, profileKeys)
        || !Array.isArray(profile.local_rule_ids)
        || !profile.local_rule_ids.every(validStableId)
        || new Set(profile.local_rule_ids).size !== profile.local_rule_ids.length
        || !sameStringArray(
          profile.local_rule_ids,
          [...profile.local_rule_ids].sort(),
        )
        || !isRuleInteger(profile.hcd_record_count)
        || profile.hcd_record_count < 0) {
      throw new Error("statewide coverage index has an invalid profile");
    }
    const expectedLocalRuleIds = rules
      .filter(rule => rule.jurisdiction_scope === jurisdiction.slug)
      .map(rule => rule.rule_id)
      .sort();
    if (!sameStringArray(profile.local_rule_ids, expectedLocalRuleIds)
        || profile.hcd_record_count !== (letterMap[jurisdiction.slug] || []).length) {
      throw new Error("statewide coverage index profile drifted from its sources");
    }
  }
  return data;
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
    if (data?._meta?.format_version !== 5
        || !Array.isArray(data.rules)
        || !validRuleManifest(data.rule_manifest)
        || !data.source_state || !data.coverage_index)
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
    fetchJson("data/jurisdictions/generated/coverage-index.json"),
    fetchOptionalJson("data/conformance/results/index.json", {}),
    fetchOptionalJson("data/explanations/plain-language.json",
                      {schema_version: 1, entries: []}),
    fetchJson("data/source-status/current.json"),
    fetchOptionalJson(
      "data/availability/woodland-preapproved-adu-program.json",
      null,
    ),
    fetchOptionalJson(
      "data/validation/rule-verification.json",
      null,
    ),
  ]).then(([ruleData, golden, sources,
            checks, registry, letters, coverageIndex, scans, plainLanguage,
            sourceState, programAvailability, ruleVerification]) => ({
    rules: ruleData.rules,
    rule_manifest: ruleData.rule_manifest,
    golden, sources, checks, registry, letters, coverage_index: coverageIndex,
    scans,
    plain_language: plainLanguage,
    source_state: sourceState,
    program_availability: programAvailability,
    rule_verification: ruleVerification,
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
      `<div class="notice ca-shout" lang="${lang}">${esc(message)}</div>`;
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
    SOURCE_STATE = normalizeSourceState(
      data.source_state,
      SOURCES,
      RULES,
      GOLDEN,
      data._meta?.generated_from || {},
    );
    if (!SOURCE_STATE)
      throw new Error("reviewed source-state snapshot failed validation");
    PROGRAM_AVAILABILITY = await normalizeProgramAvailability(
      data.program_availability,
    );
    RULE_VERIFICATIONS = await normalizeRuleVerifications(
      data.rule_verification,
      RULES,
    );
    READINESS = await normalizeReadinessData(data.readiness);
    JOURNEY = await normalizeJourney(
      data.journeys,
      READINESS,
      RULES,
      GOLDEN,
    );
    if (pageIs("readiness")) {
      if (!READINESS)
        throw new Error("generated packet-presence data failed validation");
      renderProgramAvailabilityNotice();
      renderReadinessEntry(READINESS);
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
    COVERAGE_INDEX = normalizeCoverageIndex(
      data.coverage_index,
      RULES,
      JURIS,
      data.letters,
    );
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
      renderSourceState();
      renderSources();
    }
  } catch (error) {
    showDataLoadError(error);
  }
}

initializeDemo();
