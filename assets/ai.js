// Optional runtime AI assistance for the project-check page (ADR 0004).
//
// This module adds nothing to the page until the applicant asks for it. The
// static experience in demo.js is unchanged: with no service configured or
// reachable, the page makes no request beyond its own origin and the
// structured form behaves exactly as before. When the applicant presses
// "Use AI assistance", the page probes the service once; only then does it
// render the free-text field, and only on the applicant's next action does
// it send anything. Drafted answers go into the ordinary form for the
// applicant to confirm; the deterministic matcher in demo.js is the only
// thing that ever produces a result. Explanations come back with citations
// the service has already verified against the committed corpus, and the
// number of withheld statements is shown beside them.
(() => {
  "use strict";
  if (typeof pageIs !== "function" || !pageIs("project")) return;
  const serviceMeta = document.querySelector('meta[name="permit-ai-service"]');
  // One or more candidate origins, comma-separated, probed in order: the
  // local development service first, then a hosted one. The first that
  // answers /health is used for the rest of the page's life.
  const SERVICE_CANDIDATES = (serviceMeta?.content || "")
    .split(",").map(url => url.trim().replace(/\/+$/, "")).filter(Boolean);
  const panel = document.getElementById("aiAssist");
  if (!SERVICE_CANDIDATES.length || !panel) return;

  const REQUEST_TIMEOUT_MS = 120000;
  const PROBE_TIMEOUT_MS = 4000;
  let SERVICE_URL = null;
  let serviceHealth = null;
  let lastDraft = null;

  const t = () => STRINGS[lang].ai;

  function fetchJsonWithTimeout(url, init, timeoutMs = REQUEST_TIMEOUT_MS) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    return fetch(url, {...init, signal: controller.signal, credentials: "omit"})
      .then(async response => {
        const body = await response.json().catch(() => null);
        return {ok: response.ok, status: response.status, body};
      })
      .finally(() => clearTimeout(timer));
  }

  function post(path, payload) {
    return fetchJsonWithTimeout(`${SERVICE_URL}${path}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
  }

  function failureMessage(result) {
    if (result.status === 429) return t().budgetExhausted;
    if (result.status === 409) return t().matcherDisagreement;
    return t().serviceError;
  }

  function sourceLink(citation) {
    if (!citation.url) return "";
    const isHtml = !/\.pdf(?:$|[?#])/i.test(citation.url);
    const words = citation.quote.split(/\s+/).slice(0, 8).join(" ");
    const href = isHtml ? `${citation.url}#:~:text=${encodeURIComponent(words)}` : citation.url;
    const label = isHtml ? t().openSourceAt : t().openSource;
    return ` <a href="${esc(href)}" rel="noopener noreferrer" target="_blank">${esc(label)}</a>`;
  }

  function valueLabel(name, value) {
    const s = STRINGS[lang];
    const lists = {
      project_type: s.types,
      primary_dwelling_status: s.primaryOptions,
      adu_project_form: s.aduFormOptions,
    };
    const options = lists[name] || s.tri;
    const found = options.find(([v]) => v === value);
    return found ? found[1] : value;
  }

  function renderPanelShell() {
    panel.lang = lang;
    panel.innerHTML = `<details class="ai-assist ca-box" id="aiAssistDetails">
      <summary id="aiAssistHeading">${esc(t().panelHeading)}</summary>
      <p class="small">${esc(t().panelIntro)}</p>
      <p class="ai-actions"><button class="ca-button ca-button-outline" type="button"
        id="aiEnable">${esc(t().enable)}</button></p>
      <p class="small" id="aiStatus" role="status" aria-live="polite"></p>
      <div id="aiIntake"></div>
      <div id="aiDraft" aria-live="polite"></div>
    </details>`;
    document.getElementById("aiEnable").addEventListener("click", enableAssistance);
  }

  async function enableAssistance() {
    const status = document.getElementById("aiStatus");
    const button = document.getElementById("aiEnable");
    button.disabled = true;
    status.textContent = t().checking;
    serviceHealth = null;
    for (const candidate of SERVICE_CANDIDATES) {
      try {
        const health = await fetchJsonWithTimeout(`${candidate}/health`, {method: "GET"}, PROBE_TIMEOUT_MS);
        if (health.ok && health.body?.status === "ok") {
          serviceHealth = health.body;
          SERVICE_URL = candidate;
          break;
        }
      } catch {
        // try the next candidate
      }
    }
    if (!serviceHealth) {
      status.textContent = t().unavailable;
      button.disabled = false;
      return;
    }
    status.textContent = t().available(serviceHealth.model);
    button.hidden = true;
    renderIntakeField();
  }

  function renderIntakeField() {
    const container = document.getElementById("aiIntake");
    container.lang = lang;
    container.innerHTML = `<ca-field>
        <label for="aiDescription">${esc(t().describeLabel)}</label>
        <p class="small" id="aiDescriptionHelp">${esc(t().describeHelp)}</p>
        <textarea id="aiDescription" rows="5" maxlength="4000"
          aria-describedby="aiDescriptionHelp"></textarea>
      </ca-field>
      <p class="ai-actions"><button class="ca-button" type="button" id="aiDraftButton">${esc(t().draft)}</button></p>
      <p class="small" id="aiDraftStatus" role="status" aria-live="polite"></p>`;
    document.getElementById("aiDraftButton").addEventListener("click", draftAnswers);
  }

  async function draftAnswers() {
    const text = document.getElementById("aiDescription").value.trim();
    const status = document.getElementById("aiDraftStatus");
    const button = document.getElementById("aiDraftButton");
    if (!text) { document.getElementById("aiDescription").focus(); return; }
    button.disabled = true;
    status.textContent = t().drafting;
    let result;
    try {
      result = await post("/intake/extract", {text, language: lang});
    } catch {
      result = {ok: false};
    }
    button.disabled = false;
    if (!result.ok) {
      status.textContent = failureMessage(result);
      return;
    }
    status.textContent = "";
    lastDraft = result.body;
    applyDraftToForm(result.body);
    renderDraftReview(result.body);
  }

  function applyDraftToForm(draft) {
    const values = {...draft.draft_intake};
    if (typeof deactivateProjectSample === "function") deactivateProjectSample();
    intakeDraft = {};
    if (values.project_type && values.project_type !== "unknown") {
      intakeDraft.project_type = values.project_type;
    }
    for (const [name, value] of Object.entries(values)) {
      if (name === "project_type" || name === "jurisdiction") continue;
      intakeDraft[name] = value;
    }
    const jurisInput = document.getElementById("jurisInput");
    if (draft.jurisdiction?.slug) {
      const entry = JURIS.find(j => j.slug === draft.jurisdiction.slug);
      if (entry) jurisInput.value = jurisDisplay(entry);
    }
    renderForm();
    renderJurisStatus();
    if (typeof invalidateRenderedProjectResult === "function") invalidateRenderedProjectResult("");
  }

  function renderDraftReview(draft) {
    const out = document.getElementById("aiDraft");
    out.lang = lang;
    const rows = [];
    const typeField = draft.project_type;
    if (typeField.status === "extracted") {
      rows.push(fieldRow(STRINGS[lang].project, valueLabel("project_type", typeField.value), typeField.quote));
    }
    if (draft.jurisdiction?.slug) {
      rows.push(fieldRow(STRINGS[lang].juris, draft.jurisdiction.name, draft.jurisdiction.quote));
    }
    for (const field of draft.fields) {
      if (field.status !== "extracted") continue;
      rows.push(fieldRow(questionLabel(field.name, typeField.value), valueLabel(field.name, field.value), field.quote));
    }
    const unanswered = draft.unanswered.filter(name => name !== "jurisdiction");
    const unansweredMarkup = unanswered.length
      ? `<p class="small"><strong>${esc(t().couldNotTell)}.</strong> ${esc(t().couldNotTellList)}</p>
         <ul class="small">${unanswered.map(name => `<li>${esc(name === "project_type" ? STRINGS[lang].project : questionLabel(name, typeField.value))}</li>`).join("")}</ul>`
      : "";
    const jurisdictionNote = draft.jurisdiction?.text && !draft.jurisdiction.slug
      ? `<p class="small">${esc(t().jurisdictionUnresolved(draft.jurisdiction.text))}</p>`
      : "";
    const unmapped = draft.unmapped_details.length
      ? `<h4>${esc(t().unmappedHeading)}</h4><p class="small">${esc(t().unmappedIntro)}</p>
         <ul class="small">${draft.unmapped_details.map(d => `<li>“${esc(d)}”</li>`).join("")}</ul>`
      : "";
    out.innerHTML = `<div class="ai-draft ca-box" role="region" aria-labelledby="aiDraftHeading">
        <h3 id="aiDraftHeading">${esc(t().draftHeading)}</h3>
        <p class="small">${esc(t().draftIntro)}</p>
        <dl class="ai-draft-fields">${rows.join("")}</dl>
        ${unansweredMarkup}${jurisdictionNote}${unmapped}
        <p class="small"><strong>${esc(t().reviewForm)}</strong></p>
        <p class="small">${esc(t().modelLine(draft.model, draft.prompt_version))}</p>
      </div>`;
    document.getElementById("aiDraftHeading").setAttribute("tabindex", "-1");
    document.getElementById("aiDraftHeading").focus();
  }

  function fieldRow(label, value, quote) {
    return `<div class="ai-draft-field"><dt>${esc(label)}</dt>
      <dd><strong>${esc(value)}</strong>${quote ? ` <span class="small">${esc(t().draftFrom(quote))}</span>` : ""}</dd></div>`;
  }

  function resultPanelMarkup(unresolvedOnly) {
    const label = unresolvedOnly ? t().questionsOnly : t().explain;
    return `<div class="ai-result ca-box" id="aiResultPanel" lang="${lang}">
        <p class="ai-actions"><button class="ca-button ca-button-outline" type="button"
          id="aiExplainButton">${esc(label)}</button></p>
        <p class="small" id="aiExplainStatus" role="status" aria-live="polite"></p>
        <div id="aiExplanation"></div>
        <div id="aiQuestions"></div>
        <div id="aiAsk"></div>
      </div>`;
  }

  function attachResultControls() {
    if (!serviceHealth) return;
    const results = document.getElementById("results");
    if (!results || document.getElementById("aiResultPanel")) return;
    if (!LAST_INTAKE || !results.querySelector("#resultsHeading")) return;
    const unresolvedOnly = !Array.isArray(LAST_RESULTS);
    results.insertAdjacentHTML("beforeend", resultPanelMarkup(unresolvedOnly));
    document.getElementById("aiExplainButton").addEventListener(
      "click", unresolvedOnly ? draftQuestionsOnly : explainResult);
  }

  async function draftQuestionsOnly() {
    const button = document.getElementById("aiExplainButton");
    const status = document.getElementById("aiExplainStatus");
    button.disabled = true;
    status.textContent = t().questionsLoading;
    let questions;
    try {
      questions = await post("/staff-questions", {intake: {...LAST_INTAKE}, language: lang});
    } catch {
      questions = {ok: false};
    }
    if (!questions.ok) {
      status.textContent = failureMessage(questions);
      button.disabled = false;
      return;
    }
    status.textContent = "";
    renderQuestions(questions.body);
    button.hidden = true;
  }

  async function explainResult() {
    const button = document.getElementById("aiExplainButton");
    const status = document.getElementById("aiExplainStatus");
    const intake = {...LAST_INTAKE};
    const matchedIds = Array.isArray(LAST_RESULTS) ? LAST_RESULTS.map(rule => rule.rule_id) : null;
    button.disabled = true;
    status.textContent = t().explaining;
    let explanation;
    try {
      explanation = await post("/explain", {intake, language: lang, matched_rule_ids: matchedIds});
    } catch {
      explanation = {ok: false};
    }
    if (!explanation.ok) {
      status.textContent = failureMessage(explanation);
      button.disabled = false;
      return;
    }
    renderExplanation(explanation.body);
    status.textContent = t().questionsLoading;
    let questions;
    try {
      questions = await post("/staff-questions", {intake, language: lang, matched_rule_ids: matchedIds});
    } catch {
      questions = {ok: false};
    }
    status.textContent = questions.ok ? "" : failureMessage(questions);
    if (questions.ok) renderQuestions(questions.body);
    button.hidden = true;
    renderAskBox();
  }

  function renderAskBox() {
    const out = document.getElementById("aiAsk");
    if (!out) return;
    out.lang = lang;
    out.innerHTML = `<ca-field>
        <label for="aiQuestion">${esc(t().askLabel)}</label>
        <p class="small" id="aiQuestionHelp">${esc(t().askHelp)}</p>
        <input id="aiQuestion" type="text" maxlength="500" aria-describedby="aiQuestionHelp">
      </ca-field>
      <p class="ai-actions"><button class="ca-button ca-button-outline" type="button" id="aiAskButton">${esc(t().ask)}</button></p>
      <p class="small" id="aiAskStatus" role="status" aria-live="polite"></p>
      <div id="aiAnswer"></div>`;
    document.getElementById("aiAskButton").addEventListener("click", askQuestion);
    document.getElementById("aiQuestion").addEventListener("keydown", event => {
      if (event.key === "Enter") { event.preventDefault(); askQuestion(); }
    });
  }

  async function askQuestion() {
    const input = document.getElementById("aiQuestion");
    const button = document.getElementById("aiAskButton");
    const status = document.getElementById("aiAskStatus");
    const question = input.value.trim();
    if (!question) { input.focus(); return; }
    button.disabled = true;
    status.textContent = t().asking;
    const matchedIds = Array.isArray(LAST_RESULTS) ? LAST_RESULTS.map(rule => rule.rule_id) : null;
    let answer;
    try {
      answer = await post("/ask", {intake: {...LAST_INTAKE}, language: lang, matched_rule_ids: matchedIds, question});
    } catch {
      answer = {ok: false};
    }
    button.disabled = false;
    if (!answer.ok) {
      status.textContent = failureMessage(answer);
      return;
    }
    status.textContent = "";
    renderAnswer(answer.body);
  }

  function renderAnswer(body) {
    const out = document.getElementById("aiAnswer");
    const claims = body.claims.map(claim => {
      const citations = claim.citations.map(c => `<li class="small">
          <span class="ai-citation-label">${esc(t().citationSource)}</span>
          ${esc(c.source_label || c.source_id)} (${esc(c.passage_id)}):
          <q>${esc(c.quote)}</q>${sourceLink(c)}
        </li>`).join("");
      return `<li><p>${esc(claim.text)}</p><ul class="ai-citations">${citations}</ul></li>`;
    }).join("");
    const staffQuestion = body.staff_question
      ? `<p><strong>${esc(t().askStaffQuestion)}</strong> ${esc(body.staff_question)}</p>` : "";
    const body_ = body.abstained
      ? `<p class="small ai-withheld">${esc(t().askAbstained)}</p>${staffQuestion}`
      : `<ol class="ai-claims">${claims}</ol>${body.withheld_count
          ? `<p class="small ai-withheld">${esc(t().withheld(body.withheld_count))}</p>` : ""}${staffQuestion}`;
    out.innerHTML = `<h4 id="aiAnswerHeading" tabindex="-1">${esc(t().askHeading)}</h4>
      <p class="small"><q>${esc(body.question)}</q></p>
      <p class="small ai-label">${esc(body.label)}</p>
      ${body_}
      <p class="small">${esc(t().modelLine(body.model, body.prompt_version))}</p>`;
    document.getElementById("aiAnswerHeading").focus();
  }

  function renderExplanation(body) {
    const out = document.getElementById("aiExplanation");
    const claims = body.claims.map(claim => {
      const citations = claim.citations.map(c => `<li class="small">
          <span class="ai-citation-label">${esc(t().citationSource)}</span>
          ${esc(c.source_label || c.source_id)} (${esc(c.passage_id)}):
          <q>${esc(c.quote)}</q>${sourceLink(c)}
        </li>`).join("");
      return `<li><p>${esc(claim.text)}</p><ul class="ai-citations">${citations}</ul></li>`;
    }).join("");
    const withheld = body.withheld_count
      ? `<p class="small ai-withheld">${esc(t().withheld(body.withheld_count))}</p>` : "";
    const intro = body.claims.length
      ? `<p class="small">${esc(t().explainCitedIntro(body.claims.length))}</p>`
      : `<p class="small">${esc(t().noClaims)}</p>`;
    out.innerHTML = `<h3 id="aiExplanationHeading" tabindex="-1">${esc(t().explainHeading)}</h3>
      <p class="small ai-label">${esc(body.label)}</p>
      ${intro}<ol class="ai-claims">${claims}</ol>${withheld}
      <p class="small">${esc(t().modelLine(body.model, body.prompt_version))}</p>`;
    document.getElementById("aiExplanationHeading").focus();
  }

  function renderQuestions(body) {
    const out = document.getElementById("aiQuestions");
    const items = body.questions.map(q => {
      const relates = q.rule_id || q.fact
        ? `<span class="small">${esc(t().questionRelates(q.rule_id, q.fact ? questionLabel(q.fact, LAST_INTAKE?.project_type) : null))}</span>` : "";
      return `<li><p>${esc(q.question)}</p>${q.why ? `<p class="small">${esc(q.why)}</p>` : ""}${relates}</li>`;
    }).join("");
    out.innerHTML = `<h3>${esc(t().questionsHeading)}</h3>
      <p class="small ai-label">${esc(body.label)}</p>
      ${items ? `<ol class="ai-questions">${items}</ol>` : `<p class="small">${esc(t().questionsNone)}</p>`}
      <p class="small">${esc(t().modelLine(body.model, body.prompt_version))}</p>`;
  }

  function rerenderOnLanguageChange() {
    const details = document.getElementById("aiAssistDetails");
    const wasOpen = details ? details.open : false;
    renderPanelShell();
    const shell = document.getElementById("aiAssistDetails");
    shell.open = wasOpen;
    if (serviceHealth) {
      document.getElementById("aiEnable").hidden = true;
      document.getElementById("aiStatus").textContent = t().available(serviceHealth.model);
      renderIntakeField();
      if (lastDraft) renderDraftReview(lastDraft);
    }
  }

  renderPanelShell();
  document.getElementById("langToggle")?.addEventListener("click", () => {
    // demo.js flips `lang` and re-renders synchronously in its own listener,
    // which was registered first; re-render this panel afterwards.
    setTimeout(rerenderOnLanguageChange, 0);
  });
  const results = document.getElementById("results");
  if (results) {
    new MutationObserver(attachResultControls).observe(results, {childList: true});
  }
})();
