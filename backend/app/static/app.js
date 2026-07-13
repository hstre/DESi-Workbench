"use strict";

const $ = (id) => document.getElementById(id);

const roleLabels = {
  theorist: "Theoretiker",
  literature_scout: "Literatur-Scout",
  falsifier: "Falsifizierer",
  experimental_designer: "Versuchsplaner",
  method_reviewer: "Methodenprüfer",
  paper_builder: "Paper Builder",
  adversarial_reviewer: "Adversarial Reviewer",
};

let capabilities = null;
let currentRun = null;
let activeStage = null;
let selectedFile = null;
let finalResult = null;

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

function setMessage(node, text = "", kind = "") {
  node.textContent = text;
  node.className = `message ${kind}`.trim();
}

function setBusy(button, busy, busyText) {
  if (!button.dataset.label) button.dataset.label = button.textContent;
  button.disabled = busy;
  button.textContent = busy ? busyText : button.dataset.label;
}

function engineReady(engine) {
  return engine && (engine.available === true || engine.execution === "native-claim-audit");
}

async function loadCapabilities() {
  const status = $("system-status");
  try {
    capabilities = await api("/ui/api/capabilities");
    const engines = capabilities.engines || {};
    const native = engineReady(engines.desi) && engineReady(engines.kevin) && engineReady(engines.doktores);
    status.textContent = native ? "DESi · Kevin · Doktores bereit" : "Fallback-fähiger Betrieb";
    status.className = `status-pill ${native ? "good" : "warn"}`;
  } catch (error) {
    status.textContent = `Systemfehler: ${error.message}`;
    status.className = "status-pill bad";
  }
}

function bytesToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function selectFile(file) {
  if (!file) return;
  if (file.size > 10_000_000) {
    setMessage($("start-message"), "Die Datei überschreitet 10 MB.", "error");
    return;
  }
  selectedFile = file;
  $("file-name").textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`;
  $("manuscript").value = "";
  setMessage($("start-message"));
}

async function filePayload(file) {
  return {
    name: file.name,
    type: file.type || "",
    data_base64: bytesToBase64(await file.arrayBuffer()),
  };
}

function addTag(container, text) {
  const tag = document.createElement("span");
  tag.className = "tag";
  tag.textContent = text;
  container.appendChild(tag);
}

function renderTags(container, items) {
  container.replaceChildren();
  if (!items || items.length === 0) {
    addTag(container, "keine");
    return;
  }
  items.forEach((item) => addTag(container, String(item)));
}

function renderEngines(run) {
  const container = $("engine-list");
  container.replaceChildren();
  const engines = run.engines || {};
  for (const name of ["desi", "kevin", "doktores"]) {
    const engine = engines[name] || {};
    const row = document.createElement("div");
    row.className = "engine-row";

    const label = document.createElement("strong");
    label.textContent = name;

    const detail = document.createElement("span");
    const version = engine.package_version ? `v${engine.package_version}` : "ohne Paketversion";
    detail.textContent = `${version} · ${engine.execution || engine.adapter || engine.module || "unbekannt"}`;

    const state = document.createElement("span");
    const native = name === "desi" || engine.available === true;
    state.className = `engine-state ${native ? "" : "fallback"}`.trim();
    state.textContent = native ? "bereit" : "Fallback";

    row.append(label, detail, state);
    container.appendChild(row);
  }
}

function renderStages(run) {
  const list = $("stage-list");
  list.replaceChildren();
  const stages = run.stages || [];
  const complete = stages.filter((stage) => stage.status === "complete").length;
  $("progress-label").textContent = `${complete} / ${stages.length}`;

  stages.forEach((stage, index) => {
    const item = document.createElement("li");
    item.className = `stage-item ${stage.status}`;

    const number = document.createElement("span");
    number.className = "stage-index";
    number.textContent = stage.status === "complete" ? "✓" : String(index + 1);

    const name = document.createElement("span");
    name.className = "stage-name";
    name.textContent = roleLabels[stage.role] || stage.role;

    const state = document.createElement("span");
    state.className = "stage-state";
    state.textContent = ({ pending: "wartet", active: "aktiv", complete: "fertig" })[stage.status] || stage.status;

    item.append(number, name, state);
    list.appendChild(item);
  });
}

function renderRun(run) {
  currentRun = run;
  localStorage.setItem("desi_last_run", run.run_id);
  $("run-panel").classList.remove("hidden");
  $("run-title").textContent = run.title || "Unbenanntes Manuskript";
  $("run-id").textContent = run.run_id;

  const audit = run.audit || {};
  const blindspots = run.blindspots || {};
  $("metric-claims").textContent = (audit.claims || []).length;
  $("metric-unsupported").textContent = (audit.unsupported_claim_ids || []).length;
  $("metric-overclaims").textContent = (audit.overclaims || []).length;
  $("metric-blindspots").textContent = (blindspots.blindspot_axes || []).length;

  renderEngines(run);
  renderTags($("blindspot-tags"), blindspots.blindspot_axes);
  renderTags($("method-tags"), blindspots.selected_methods);
  renderStages(run);
  window.scrollTo({ top: $("run-panel").offsetTop - 90, behavior: "smooth" });
}

function hypothesisIds(packet) {
  const prior = packet.prior_stage_results || {};
  return (prior.theorist?.hypotheses || []).map((item) => item.id);
}

function survivingIds(packet) {
  const prior = packet.prior_stage_results || {};
  return prior.falsifier?.surviving_hypothesis_ids || hypothesisIds(packet);
}

function experimentIds(packet) {
  const prior = packet.prior_stage_results || {};
  return (prior.experimental_designer?.experiments || []).map((item) => item.id);
}

function templateFor(stage) {
  const packet = stage.packet;
  const claims = packet.claims || [];
  const claimIds = claims.slice(0, 2).map((claim) => claim.id);
  const hypotheses = hypothesisIds(packet);
  const survivors = survivingIds(packet);
  const experiments = experimentIds(packet);

  switch (stage.role) {
    case "theorist":
      return {
        hypotheses: [{
          id: "H1",
          claim_ids: claimIds.length ? claimIds : ["claim_1"],
          statement: "",
          assumptions: [],
          testable_consequence: "",
        }],
        unresolved_terms: [],
      };
    case "literature_scout":
      return {
        related_work: [],
        competing_explanations: [],
        known_counterexamples: [],
        datasets: [],
        evidence: [{
          target_hypothesis_ids: hypotheses.slice(0, 1),
          stance: "context",
          statement: "",
          reference: null,
          source_type: "unknown",
        }],
        search_limitations: [],
      };
    case "falsifier":
      return {
        attacks: [{
          hypothesis_id: hypotheses[0] || "H1",
          target_claim_ids: claimIds.length ? claimIds : ["claim_1"],
          attack_type: packet.blindspots?.transition_probe ? "boundary_change" : "missing_assumption",
          argument: "",
          fatal: false,
        }],
        surviving_hypothesis_ids: hypotheses,
        weakest_assumption: "",
      };
    case "experimental_designer":
      return {
        experiments: [{
          id: "EX1",
          target_hypothesis_ids: survivors.slice(0, 1),
          design: "",
          baselines: [],
          metrics: [],
          stop_criteria: "",
          reproducibility_requirements: [],
        }],
        unresolved_constraints: [],
        blocked_reason: null,
      };
    case "method_reviewer":
      return {
        assessments: experiments.map((id) => ({
          experiment_id: id,
          verdict: "repairable",
          concerns: [],
          required_controls: [],
          measurement_risks: [],
        })),
        cross_cutting_limitations: [],
        blocked_reason: experiments.length ? null : "",
      };
    case "paper_builder":
      return {
        publication_kind: "report",
        title: currentRun?.title || "Epistemic Review Report",
        markdown: "# Bericht\n\n",
        included_hypothesis_ids: survivors,
        included_experiment_ids: experiments,
        limitations: [],
        open_questions: [],
      };
    case "adversarial_reviewer":
      return {
        findings: [{
          target: survivors[0] || experiments[0] || "publication",
          verdict: "borderline",
          reason: "",
          required_revision: null,
          deterministic_check: null,
        }],
        overall: "revise",
        blocking_issues: [],
        limitations: [],
      };
    default:
      return {};
  }
}

function showStage(stage) {
  activeStage = stage;
  finalResult = null;
  $("complete-panel").classList.add("hidden");
  $("stage-panel").classList.remove("hidden");
  $("stage-position").textContent = `Rolle ${stage.packet.role_position} von ${stage.packet.role_count}`;
  $("stage-role").textContent = roleLabels[stage.role] || stage.role;
  $("stage-task").textContent = stage.packet.task || "";

  const forbidden = $("forbidden-list");
  forbidden.replaceChildren();
  (stage.packet.forbidden_actions || []).forEach((rule) => {
    const item = document.createElement("li");
    item.textContent = rule;
    forbidden.appendChild(item);
  });

  $("packet-json").textContent = JSON.stringify(stage.packet, null, 2);
  $("stage-result").value = JSON.stringify(templateFor(stage), null, 2);
  setMessage($("stage-message"));
  $("stage-panel").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function fetchSummary(runId) {
  const run = await api(`/ui/api/run/${encodeURIComponent(runId)}`);
  renderRun(run);
  return run;
}

async function openNext(runId) {
  const next = await api(`/ui/api/run/${encodeURIComponent(runId)}/next`, { method: "POST", body: "{}" });
  if (next.complete) {
    await finalizeRun(runId);
  } else {
    showStage(next);
  }
}

async function finalizeRun(runId) {
  const result = await api(`/ui/api/run/${encodeURIComponent(runId)}/finalize`, { method: "POST", body: "{}" });
  finalResult = result;
  activeStage = null;
  $("stage-panel").classList.add("hidden");
  $("complete-panel").classList.remove("hidden");
  $("report-markdown").textContent = result.markdown || "";
  $("report-json").textContent = JSON.stringify(result.report || result, null, 2);
  $("complete-panel").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function startReview(event) {
  event.preventDefault();
  const button = $("start-button");
  const message = $("start-message");
  setMessage(message);
  setBusy(button, true, "Review wird angelegt …");

  try {
    const text = $("manuscript").value.trim();
    if (!selectedFile && !text) throw new Error("Bitte Datei auswählen oder Manuskripttext einfügen.");
    if (selectedFile && text) throw new Error("Bitte entweder Datei oder Text verwenden.");

    const payload = {
      title: $("title").value.trim() || null,
      focus: $("focus").value.trim() || null,
      modes: ["audit", "extend", "adversarial"],
    };
    if (selectedFile) payload.file = await filePayload(selectedFile);
    else payload.text = text;

    const run = await api("/ui/api/start", { method: "POST", body: JSON.stringify(payload) });
    renderRun(run);
    setMessage(message, "Lauf angelegt.", "success");
    await openNext(run.run_id);
  } catch (error) {
    setMessage(message, error.message, "error");
  } finally {
    setBusy(button, false, "Review wird angelegt …");
  }
}

async function submitStage() {
  if (!currentRun || !activeStage) return;
  const button = $("submit-stage");
  const message = $("stage-message");
  setMessage(message);
  setBusy(button, true, "Wird geprüft …");
  try {
    const result = JSON.parse($("stage-result").value);
    const response = await api(
      `/ui/api/run/${encodeURIComponent(currentRun.run_id)}/stage/${encodeURIComponent(activeStage.stage_id)}`,
      { method: "POST", body: JSON.stringify({ result }) },
    );
    setMessage(message, "Rolle akzeptiert und hashverkettet.", "success");
    await fetchSummary(currentRun.run_id);
    if (response.next?.complete) await finalizeRun(currentRun.run_id);
    else if (response.next) showStage(response.next);
    else await openNext(currentRun.run_id);
  } catch (error) {
    setMessage(message, error instanceof SyntaxError ? `Ungültiges JSON: ${error.message}` : error.message, "error");
  } finally {
    setBusy(button, false, "Wird geprüft …");
  }
}

function formatJson() {
  const editor = $("stage-result");
  try {
    editor.value = JSON.stringify(JSON.parse(editor.value), null, 2);
    setMessage($("stage-message"), "JSON formatiert.", "success");
  } catch (error) {
    setMessage($("stage-message"), `Ungültiges JSON: ${error.message}`, "error");
  }
}

async function copyText(text, successNode, successText) {
  await navigator.clipboard.writeText(text);
  if (successNode) {
    setMessage(successNode, successText, "success");
    setTimeout(() => setMessage(successNode), 1800);
  }
}

function downloadMarkdown() {
  if (!finalResult) return;
  const blob = new Blob([finalResult.markdown || ""], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${(currentRun?.title || "epistemic-review").replace(/[^a-z0-9_-]+/gi, "-")}.md`;
  link.click();
  URL.revokeObjectURL(url);
}

async function restoreRun() {
  const runId = localStorage.getItem("desi_last_run");
  if (!runId) return;
  const button = $("restore-run");
  setBusy(button, true, "Wird geöffnet …");
  try {
    const run = await fetchSummary(runId);
    if (run.status === "complete" || run.status === "ready") await finalizeRun(runId);
    else await openNext(runId);
  } catch (error) {
    localStorage.removeItem("desi_last_run");
    setMessage($("start-message"), `Lauf konnte nicht geöffnet werden: ${error.message}`, "error");
    button.classList.add("hidden");
  } finally {
    setBusy(button, false, "Wird geöffnet …");
  }
}

function resetRun() {
  currentRun = null;
  activeStage = null;
  finalResult = null;
  selectedFile = null;
  localStorage.removeItem("desi_last_run");
  $("run-panel").classList.add("hidden");
  $("stage-panel").classList.add("hidden");
  $("complete-panel").classList.add("hidden");
  $("file").value = "";
  $("file-name").textContent = "";
  $("manuscript").value = "";
  $("restore-run").classList.add("hidden");
  window.scrollTo({ top: $("start-panel").offsetTop - 90, behavior: "smooth" });
}

function wireEvents() {
  $("review-form").addEventListener("submit", startReview);
  $("file").addEventListener("change", (event) => selectFile(event.target.files[0]));
  $("manuscript").addEventListener("input", () => {
    if ($("manuscript").value.trim()) {
      selectedFile = null;
      $("file").value = "";
      $("file-name").textContent = "";
    }
  });

  const drop = $("file-drop");
  ["dragenter", "dragover"].forEach((name) => drop.addEventListener(name, (event) => {
    event.preventDefault();
    drop.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach((name) => drop.addEventListener(name, (event) => {
    event.preventDefault();
    drop.classList.remove("dragging");
  }));
  drop.addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0]));

  $("submit-stage").addEventListener("click", submitStage);
  $("format-json").addEventListener("click", formatJson);
  $("copy-packet").addEventListener("click", () => activeStage && copyText(JSON.stringify(activeStage.packet, null, 2), $("stage-message"), "Rollenpaket kopiert."));
  $("copy-run").addEventListener("click", () => currentRun && copyText(currentRun.run_id, null, ""));
  $("copy-report").addEventListener("click", () => finalResult && copyText(finalResult.markdown || "", null, ""));
  $("download-report").addEventListener("click", downloadMarkdown);
  $("restore-run").addEventListener("click", restoreRun);
  $("new-run").addEventListener("click", resetRun);
}

async function init() {
  wireEvents();
  if (localStorage.getItem("desi_last_run")) $("restore-run").classList.remove("hidden");
  await loadCapabilities();
}

init();
