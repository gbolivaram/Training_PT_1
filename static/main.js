/* ── PRO141 HMI — main.js ──────────────────────────────────────────────── */

const MOTIVOS_BLOQUEO = [
  "Falta información mínima para formulario / reporte",
  "Aprobación rechazada / falta firma",
  "No se puede ejecutar transacción SAP",
  "Material no segregado / riesgo de mezcla",
  "Discrepancia stock físico vs sistema",
  "Falta respuesta de otra central",
  "Otro"
];

const FLOW_ORDER = [
  "S0_alcance",
  "AN1_inicio","AN2_crear_reporte","AN3_enviar_reporte",
  "AN4_registrar_provision","AN5_recepcion_listado","AN6_coordinar_revision","AN7_tratamiento_subproceso",
  "TR0_inicio",
  "TR_A1_identificacion","TR_A2_informar_almacen",
  "TR_B1_solicitar_inspeccion","TR_B2_definir_inspector",
  "TR_C1_recepcion_masiva","TR_C2_definir_inspeccion",
  "TR_I1_analizar_obsolescencia",
  "TR_F1_formulario","TR_F2_solicitar_aprobacion","TR_F3_revisar_firmar","TR_F4_firmar_formulario",
  "TR_L1_traspasar_AL00","TR_L2_modificar_ubicacion","TR_L3_etiquetar","TR_L4_trasladar",
  "TR_L5_analizar_utilidad_otras","TR_L6_informar_utilidad",
  "TR_D1_util","TR_D3_TRASLADO_A_OTRA_PLANTA",
  "TR_L7_inicio_desguace","TR_L8_comercial","TR_D2_comercial",
  "END_TRASLADO","END_VENTAS","END_DISPOSICION"
];

const TYPE_LABEL = { task: "Tarea", decision: "Decisión", end: "Fin" };

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  nodos: {},
  session_id: null,
  current_node: "S0_alcance",
  history: [],
  decisiones: [],
  bloqueos: [],
  inputs: {},
  logs: [],
  estado: "EN_CURSO",
  is_blocked: false,
  block_ts: null
};

// ── DOM refs ───────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const elHeader       = $("node-header");
const elBody         = $("node-body");
const elBlockPanel   = $("block-panel");
const elAlert        = $("alert");
const elProgress     = $("progress-bar");
const elStepMeta     = $("step-meta");
const elSummary      = $("summary-panel");
const elSummaryTbl   = $("summary-tables");
const elBtnSi        = $("btn-si");
const elBtnNo        = $("btn-no");
const elBtnBack      = $("btn-back");
const elBtnRehacer   = $("btn-rehacer");
const elBtnExport    = $("btn-export");
const elBtnReset     = $("btn-reset");
const elBlockMot     = $("block-motivos");
const elBlockDet     = $("block-detalle");
const elToast        = $("toast");
const elTimeline     = $("timeline");
const elSidebar      = $("sidebar");
const elOverlay      = $("sidebar-overlay");
const elBtnSideToggle= $("btn-sidebar-toggle");
const elSideSession  = $("sidebar-session");

// ── Init ───────────────────────────────────────────────────────────────────
async function init() {
  const res = await fetch("/api/nodos");
  state.nodos = await res.json();

  const saved = localStorage.getItem("pro141_session_id");
  if (saved) {
    try {
      const r = await fetch(`/api/session/${saved}`);
      if (r.ok) {
        const s = await r.json();
        state.session_id   = s.session_id;
        state.current_node = s.current_node;
        state.history      = s.history;
        state.decisiones   = s.decisiones;
        state.bloqueos     = s.bloqueos;
        state.inputs       = s.inputs;
        state.logs         = s.logs;
        state.estado       = s.estado;
        render();
        return;
      }
    } catch(_) {}
  }
  await newSession();
}

async function newSession() {
  const r = await fetch("/api/session", { method: "POST" });
  const s = await r.json();
  state.session_id   = s.session_id;
  state.current_node = "S0_alcance";
  state.history      = [];
  state.decisiones   = [];
  state.bloqueos     = [];
  state.inputs       = {};
  state.logs         = [];
  state.estado       = "EN_CURSO";
  state.is_blocked   = false;
  localStorage.setItem("pro141_session_id", s.session_id);
  render();
}

// ── Persist ────────────────────────────────────────────────────────────────
async function persist() {
  await fetch(`/api/session/${state.session_id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      estado:       state.estado,
      current_node: state.current_node,
      history:      state.history,
      decisiones:   state.decisiones,
      bloqueos:     state.bloqueos,
      inputs:       state.inputs,
      logs:         state.logs
    })
  });
}

function log(tipo, data = {}) {
  state.logs.push({ ts: new Date().toISOString(), tipo, nodo: state.current_node, estado: state.estado, data });
}

// ── Progress ───────────────────────────────────────────────────────────────
function updateProgress() {
  const idx = FLOW_ORDER.indexOf(state.current_node);
  const pct = idx < 0 ? 0 : Math.round(((idx + 1) / FLOW_ORDER.length) * 100);
  elProgress.style.width = pct + "%";
  const step = idx < 0 ? "—" : `Paso ${idx + 1} / ${FLOW_ORDER.length}`;
  elStepMeta.textContent = `${step}  ·  ID ${state.session_id?.slice(0,8) ?? ""}`;
  if (elSideSession) elSideSession.textContent = state.session_id?.slice(0,8) ?? "";
}

// ── Timeline ───────────────────────────────────────────────────────────────
function renderTimeline() {
  if (!elTimeline) return;

  const path = [...state.history, state.current_node];

  elTimeline.innerHTML = path.map((nodeId, idx) => {
    const n = state.nodos[nodeId];
    if (!n) return "";

    const isCurrent  = nodeId === state.current_node;
    const wasBlocked = state.bloqueos.some(b => b.nodo === nodeId);
    const isLast     = idx === path.length - 1;

    const dotClass  = isCurrent
      ? (wasBlocked ? "blocked" : "current")
      : wasBlocked ? "blocked done" : "done";
    const itemClass = isCurrent ? "tl-item tl-current" : "tl-item tl-done";

    const maxLen = 42;
    const label  = n.titulo.length > maxLen ? n.titulo.slice(0, maxLen - 1) + "…" : n.titulo;
    const typeTag = TYPE_LABEL[n.type] || n.type;

    return `
      <div class="${itemClass}">
        <div class="tl-left">
          <div class="tl-dot ${dotClass}"></div>
          ${!isLast ? '<div class="tl-line"></div>' : ""}
        </div>
        <div class="tl-content">
          <div class="tl-num">${idx + 1} · ${typeTag}</div>
          <div class="tl-label">${esc(label)}</div>
          ${wasBlocked ? '<div class="tl-blocked-badge">Bloqueado</div>' : ""}
        </div>
      </div>
    `;
  }).join("");

  // Auto-scroll current item into view inside sidebar
  requestAnimationFrame(() => {
    const active = elTimeline.querySelector(".tl-current");
    if (active) active.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
}

// ── Sidebar toggle (mobile) ────────────────────────────────────────────────
function openSidebar() {
  elSidebar.classList.add("open");
  elOverlay.classList.add("visible");
}
function closeSidebar() {
  elSidebar.classList.remove("open");
  elOverlay.classList.remove("visible");
}
elBtnSideToggle?.addEventListener("click", () =>
  elSidebar.classList.contains("open") ? closeSidebar() : openSidebar()
);
elOverlay?.addEventListener("click", closeSidebar);

// ── Render ─────────────────────────────────────────────────────────────────
function render() {
  clearAlert();
  updateProgress();
  renderTimeline();

  const n = state.nodos[state.current_node];
  if (!n) { showAlert("Error: nodo no encontrado — " + state.current_node); return; }

  renderHeader(n);
  renderBody(n);
  renderFooterState(n);

  if (n.type === "end") {
    elSummary.classList.remove("hidden");
    renderSummary();
  } else {
    elSummary.classList.add("hidden");
  }

  if (state.is_blocked) {
    elBlockPanel.classList.remove("hidden");
    renderBlockPanel();
  } else {
    elBlockPanel.classList.add("hidden");
  }
}

function renderHeader(n) {
  const badgeClass = { task: "badge-task", decision: "badge-decision", end: "badge-end" }[n.type] || "badge-task";
  const badgeLabel = TYPE_LABEL[n.type] || n.type;
  elHeader.innerHTML = `
    <div class="node-type-badge ${badgeClass}">${badgeLabel}</div>
    <div class="node-titulo">${esc(n.titulo)}</div>
    <div class="node-rol">Rol: <span class="rol-value">${esc(n.rol)}</span></div>
    ${n.descripcion ? `<div class="node-desc">${esc(n.descripcion)}</div>` : ""}
  `;
}

function renderBody(n) {
  elBody.innerHTML = "";
  if (n.type === "task")     renderTaskBody(n);
  else if (n.type === "decision") renderDecisionBody(n);
  else if (n.type === "end") renderEndBody(n);
}

function renderTaskBody(n) {
  const frags = [];

  if (n.acciones?.length) {
    const lis = n.acciones.map(a => `<li>${esc(a)}</li>`).join("");
    frags.push(`
      <div class="section-box">
        <div class="section-box-header">Acción a ejecutar</div>
        <div class="section-box-body"><ul class="actions-list">${lis}</ul></div>
      </div>`);
  }

  if (n.inputs?.length) {
    const fields = n.inputs.map(spec => `
      <div class="input-group">
        <label class="input-label" for="inp_${spec.key}">
          ${esc(spec.label)}${spec.required ? ' <span class="required">*</span>' : ""}
        </label>
        <input type="text" id="inp_${spec.key}" class="text-input"
          placeholder="${esc(spec.placeholder || "")}"
          data-key="${esc(spec.key)}"
          data-required="${spec.required ? "1" : "0"}"
          value="${esc(state.inputs[spec.key] || "")}" />
      </div>`).join("");
    frags.push(`
      <div class="section-box">
        <div class="section-box-header">Registro</div>
        <div class="section-box-body" style="display:flex;flex-direction:column;gap:12px;">${fields}</div>
      </div>`);
  }

  if (n.checklist?.length) {
    const items = n.checklist.map((item, i) => `
      <div class="checklist-item">
        <input type="checkbox" id="cli_${i}" />
        <label for="cli_${i}">${esc(item)}</label>
      </div>`).join("");
    frags.push(`
      <div class="section-box">
        <div class="section-box-header">Checklist — marque al completar</div>
        <div class="section-box-body"><div class="checklist">${items}</div></div>
      </div>`);
    requestAnimationFrame(() => {
      document.querySelectorAll(".checklist-item input[type='checkbox']").forEach(cb => {
        cb.addEventListener("change", () =>
          cb.closest(".checklist-item").classList.toggle("checked", cb.checked));
      });
    });
  }

  if (n.validacion) {
    frags.push(`
      <div class="validation-box">
        <div class="validation-label">Validación</div>
        <div class="validation-question">${esc(n.validacion)}</div>
        <div class="validation-hint">
          Confirme con <strong>SÍ / Avanzar</strong> para continuar.
          Si selecciona <strong>NO</strong>, el paso quedará bloqueado.
        </div>
      </div>`);
  }

  elBody.innerHTML = frags.join("");
}

function renderDecisionBody(n) {
  const opts = (n.opciones || []).map(o => `
    <label class="decision-option">
      <input type="radio" name="decision" value="${esc(o.next)}" data-label="${esc(o.label)}" />
      <span class="decision-option-label">${esc(o.label)}</span>
    </label>`).join("");

  elBody.innerHTML = `
    <div class="section-box">
      <div class="section-box-header">Selección</div>
      <div class="section-box-body">
        <div class="decision-options">${opts}</div>
        ${n.ayuda ? `<div class="ayuda-text">${esc(n.ayuda)}</div>` : ""}
      </div>
    </div>`;

  requestAnimationFrame(() => {
    document.querySelectorAll('input[name="decision"]').forEach(r => {
      r.addEventListener("change", () => {
        document.querySelectorAll(".decision-option").forEach(el => el.classList.remove("selected"));
        r.closest(".decision-option").classList.add("selected");
      });
    });
  });
}

function renderEndBody(n) {
  let inputsHtml = "";
  if (n.inputs?.length) {
    inputsHtml = n.inputs.map(spec => `
      <div class="input-group" style="margin-top:12px;">
        <label class="input-label" for="end_inp_${spec.key}">
          ${esc(spec.label)}${spec.required ? ' <span class="required">*</span>' : ""}
        </label>
        <input type="text" id="end_inp_${spec.key}" class="text-input"
          placeholder="${esc(spec.placeholder || "")}"
          data-key="${esc(spec.key)}"
          data-required="${spec.required ? "1" : "0"}"
          value="${esc(state.inputs[spec.key] || "")}" />
      </div>`).join("");
  }

  elBody.innerHTML = `
    <div class="end-box">
      <div class="end-icon">🏁</div>
      <div class="end-titulo">${esc(n.titulo)}</div>
      <div class="end-mensaje">${esc(n.mensaje || n.descripcion || "")}</div>
      <div class="end-estado">${esc(n.estado_final || "FINALIZADO")}</div>
      ${inputsHtml}
      <button class="btn-download" id="btn-download-inline">
        ⬇ Descargar trazabilidad JSON
      </button>
    </div>`;

  requestAnimationFrame(() => {
    $("btn-download-inline")?.addEventListener("click", () => triggerExport());
  });
}

function renderFooterState(n) {
  const isEnd = n.type === "end";
  elBtnBack.disabled = state.history.length === 0 || state.is_blocked;
  elBtnNo.classList.toggle("hidden", isEnd);
  elBtnNo.disabled = state.is_blocked;
  elBtnSi.textContent = isEnd
    ? "Descargar JSON"
    : n.type === "decision"
      ? "Confirmar selección"
      : "SÍ / Avanzar";
  elBtnSi.disabled = state.is_blocked && !isEnd;
}

function renderBlockPanel() {
  elBlockMot.innerHTML = MOTIVOS_BLOQUEO.map((m, i) => `
    <label class="block-motivo-item">
      <input type="checkbox" id="bm_${i}" value="${esc(m)}" />
      ${esc(m)}
    </label>`).join("");
  elBlockDet.value = "";
}

function renderSummary() {
  const inputEntries = Object.entries(state.inputs);
  const inputRows = inputEntries.length
    ? inputEntries.map(([k,v]) => `<tr><td><b>${esc(k)}</b></td><td>${esc(v)}</td></tr>`).join("")
    : `<tr><td colspan="2">(sin datos)</td></tr>`;

  const decRows = state.decisiones.length
    ? state.decisiones.map(d => `
        <tr>
          <td>${esc(d.ts||"")}</td>
          <td>${esc(d.titulo||"")}</td>
          <td>${esc(d.seleccion||"")}</td>
        </tr>`).join("")
    : `<tr><td colspan="3">(sin decisiones)</td></tr>`;

  const bloqRows = state.bloqueos.length
    ? state.bloqueos.map(b => `
        <tr>
          <td>${esc(b.ts_inicio||"")}</td>
          <td>${esc(b.titulo||"")}</td>
          <td>${esc((b.motivos||[]).join(", "))}</td>
          <td>${esc(b.detalle||"")}</td>
        </tr>`).join("")
    : `<tr><td colspan="4">(sin bloqueos)</td></tr>`;

  elSummaryTbl.innerHTML = `
    <table>
      <thead><tr><th>Campo</th><th>Valor registrado</th></tr></thead>
      <tbody>${inputRows}</tbody>
    </table><br>
    <table>
      <thead><tr><th>Timestamp</th><th>Decisión</th><th>Selección</th></tr></thead>
      <tbody>${decRows}</tbody>
    </table><br>
    <table>
      <thead><tr><th>Timestamp</th><th>Paso bloqueado</th><th>Motivo(s)</th><th>Detalle</th></tr></thead>
      <tbody>${bloqRows}</tbody>
    </table>`;
}

// ── Validation helpers ─────────────────────────────────────────────────────
function collectInputs() {
  const fields = document.querySelectorAll(".text-input");
  let ok = true, missingLabel = "";
  fields.forEach(f => {
    const key = f.dataset.key;
    const val = f.value.trim();
    if (key) state.inputs[key] = val;
    if (f.dataset.required === "1" && !val) {
      ok = false;
      missingLabel = missingLabel || (f.previousElementSibling?.textContent?.replace("*","").trim() || key);
    }
  });
  return { ok, missingLabel };
}

function checkChecklist() {
  const cbs    = [...document.querySelectorAll(".checklist-item input[type='checkbox']")];
  const labels = [...document.querySelectorAll(".checklist-item label")];
  const required = cbs.filter((_, i) => {
    const t = labels[i]?.textContent?.toLowerCase() || "";
    return !t.includes("si aplica") && !t.includes("(si aplica)");
  });
  return required.every(cb => cb.checked);
}

function getSelectedDecision() {
  const r = document.querySelector('input[name="decision"]:checked');
  return r ? { next: r.value, label: r.dataset.label } : null;
}

// ── Button handlers ────────────────────────────────────────────────────────
elBtnSi.addEventListener("click", async () => {
  const n = state.nodos[state.current_node];
  if (!n) return;

  const { ok: inputsOk, missingLabel } = collectInputs();
  if (!inputsOk) { showAlert(`Campo obligatorio: "${missingLabel}"`); return; }

  if (n.type === "end") { await persist(); triggerExport(); return; }

  if (n.type === "task") {
    if (!checkChecklist()) {
      showAlert("Complete todos los ítems del checklist antes de avanzar.");
      return;
    }
    log("AVANZA", { next: n.next });
    state.history.push(state.current_node);
    state.current_node = n.next;
    await persist();
    render();
    return;
  }

  if (n.type === "decision") {
    const sel = getSelectedDecision();
    if (!sel) { showAlert("Seleccione una opción antes de continuar."); return; }
    state.decisiones.push({
      ts: new Date().toISOString(),
      nodo: state.current_node,
      titulo: n.titulo,
      seleccion: sel.label,
      next: sel.next
    });
    log("DECISION", { seleccion: sel.label, next: sel.next });
    state.history.push(state.current_node);
    state.current_node = sel.next;
    await persist();
    render();
  }
});

elBtnNo.addEventListener("click", () => {
  if (state.is_blocked) return;
  state.is_blocked = true;
  state.block_ts   = new Date().toISOString();
  state.estado     = "BLOQUEADO";
  log("BLOQUEADO_INICIO");
  render();
});

elBtnRehacer.addEventListener("click", async () => {
  const motivos = [...document.querySelectorAll("#block-motivos input[type='checkbox']:checked")]
    .map(cb => cb.value);
  const detalle = elBlockDet.value.trim();

  if (!motivos.length) { showAlert("Seleccione al menos un motivo de bloqueo."); return; }
  if (motivos.includes("Otro") && !detalle) {
    showAlert("Ingrese un detalle cuando selecciona 'Otro'."); return;
  }

  state.bloqueos.push({
    ts_inicio: state.block_ts,
    ts_fin: new Date().toISOString(),
    nodo: state.current_node,
    titulo: state.nodos[state.current_node]?.titulo || "",
    motivos,
    detalle
  });
  log("BLOQUEADO_FIN", { motivos, detalle });
  state.is_blocked = false;
  state.estado     = "EN_CURSO";
  log("REHACER_PASO");
  await persist();
  render();
});

elBtnBack.addEventListener("click", async () => {
  if (state.is_blocked || state.history.length === 0) return;
  const prev = state.history.pop();
  log("VOLVER", { to: prev });
  state.current_node = prev;
  await persist();
  render();
});

elBtnExport.addEventListener("click", () => triggerExport());

elBtnReset.addEventListener("click", async () => {
  if (!confirm("¿Reiniciar sesión? Se perderá el progreso actual.")) return;
  localStorage.removeItem("pro141_session_id");
  await newSession();
  showToast("Sesión reiniciada");
});

// ── Export — fetch + blob download ─────────────────────────────────────────
async function triggerExport() {
  await persist();
  try {
    const r = await fetch(`/api/session/${state.session_id}/export`);
    const blob = await r.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `PRO141_${state.session_id.slice(0,8)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    showToast("JSON descargado correctamente");
  } catch(e) {
    showAlert("Error al exportar. Intente nuevamente.");
  }
}

// ── UI helpers ─────────────────────────────────────────────────────────────
function showAlert(msg, type = "error") {
  elAlert.textContent = msg;
  elAlert.className   = "alert" + (type === "success" ? " success" : "");
  elAlert.classList.remove("hidden");
  elAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
function clearAlert() {
  elAlert.classList.add("hidden");
  elAlert.textContent = "";
}

let toastTimer;
function showToast(msg) {
  elToast.textContent = msg;
  elToast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => elToast.classList.add("hidden"), 3000);
}

function esc(str) {
  return String(str ?? "")
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// ── Start ──────────────────────────────────────────────────────────────────
init();
