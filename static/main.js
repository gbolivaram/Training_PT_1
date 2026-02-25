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

// Ordered list of all node keys for progress tracking
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
const elHeader    = $("node-header");
const elBody      = $("node-body");
const elBlockPanel= $("block-panel");
const elAlert     = $("alert");
const elFooter    = $("card-footer");
const elProgress  = $("progress-bar");
const elStepMeta  = $("step-meta");
const elSummary   = $("summary-panel");
const elSummaryTbl= $("summary-tables");
const elBtnSi     = $("btn-si");
const elBtnNo     = $("btn-no");
const elBtnBack   = $("btn-back");
const elBtnRehacer= $("btn-rehacer");
const elBtnExport = $("btn-export");
const elBtnReset  = $("btn-reset");
const elBlockMot  = $("block-motivos");
const elBlockDet  = $("block-detalle");
const elToast     = $("toast");

// ── Init ───────────────────────────────────────────────────────────────────
async function init() {
  // Load nodos
  const res = await fetch("/api/nodos");
  state.nodos = await res.json();

  // Restore or create session
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

// ── Logging ────────────────────────────────────────────────────────────────
function log(tipo, data = {}) {
  state.logs.push({ ts: new Date().toISOString(), tipo, nodo: state.current_node, estado: state.estado, data });
}

// ── Progress ───────────────────────────────────────────────────────────────
function updateProgress() {
  const idx = FLOW_ORDER.indexOf(state.current_node);
  const pct = idx < 0 ? 0 : Math.round(((idx + 1) / FLOW_ORDER.length) * 100);
  elProgress.style.width = pct + "%";
  const step = idx < 0 ? "—" : `Paso ${idx + 1} de ${FLOW_ORDER.length}`;
  elStepMeta.textContent = `${step}  ·  Sesión ${state.session_id.slice(0,8)}`;
}

// ── Render ─────────────────────────────────────────────────────────────────
function render() {
  clearAlert();
  updateProgress();

  const n = state.nodos[state.current_node];
  if (!n) { showAlert("Error: nodo no encontrado — " + state.current_node); return; }

  renderHeader(n);
  renderBody(n);
  renderFooterState(n);

  // Summary panel: show only on end nodes
  if (n.type === "end") {
    elSummary.classList.remove("hidden");
    renderSummary();
  } else {
    elSummary.classList.add("hidden");
  }

  // Block panel
  if (state.is_blocked) {
    elBlockPanel.classList.remove("hidden");
    renderBlockPanel();
  } else {
    elBlockPanel.classList.add("hidden");
  }
}

function renderHeader(n) {
  const badgeClass = { task: "badge-task", decision: "badge-decision", end: "badge-end" }[n.type] || "badge-task";
  const badgeLabel = { task: "Tarea", decision: "Decisión", end: "Fin" }[n.type] || n.type;

  elHeader.innerHTML = `
    <div class="node-type-badge ${badgeClass}">${badgeLabel}</div>
    <div class="node-titulo">${esc(n.titulo)}</div>
    <div class="node-rol">Rol: <span class="rol-value">${esc(n.rol)}</span></div>
    ${n.descripcion ? `<div class="node-desc">${esc(n.descripcion)}</div>` : ""}
  `;
}

function renderBody(n) {
  elBody.innerHTML = "";

  if (n.type === "task") {
    renderTaskBody(n);
  } else if (n.type === "decision") {
    renderDecisionBody(n);
  } else if (n.type === "end") {
    renderEndBody(n);
  }
}

function renderTaskBody(n) {
  const frags = [];

  // Actions
  if (n.acciones && n.acciones.length) {
    const lis = n.acciones.map(a => `<li>${esc(a)}</li>`).join("");
    frags.push(`
      <div class="section-box">
        <div class="section-box-header">Acción a ejecutar</div>
        <div class="section-box-body">
          <ul class="actions-list">${lis}</ul>
        </div>
      </div>
    `);
  }

  // Inputs
  if (n.inputs && n.inputs.length) {
    const inputFields = n.inputs.map(spec => `
      <div class="input-group">
        <label class="input-label" for="inp_${spec.key}">
          ${esc(spec.label)}${spec.required ? ' <span class="required">*</span>' : ""}
        </label>
        <input
          type="text"
          id="inp_${spec.key}"
          class="text-input"
          placeholder="${esc(spec.placeholder || "")}"
          data-key="${esc(spec.key)}"
          data-required="${spec.required ? "1" : "0"}"
          value="${esc(state.inputs[spec.key] || "")}"
        />
      </div>
    `).join("");
    frags.push(`
      <div class="section-box">
        <div class="section-box-header">Registro</div>
        <div class="section-box-body" style="display:flex;flex-direction:column;gap:12px;">
          ${inputFields}
        </div>
      </div>
    `);
  }

  // Checklist
  if (n.checklist && n.checklist.length) {
    const items = n.checklist.map((item, i) => `
      <div class="checklist-item" id="cli_wrap_${i}">
        <input type="checkbox" id="cli_${i}" />
        <label for="cli_${i}">${esc(item)}</label>
      </div>
    `).join("");
    frags.push(`
      <div class="section-box">
        <div class="section-box-header">Checklist — marque al completar</div>
        <div class="section-box-body">
          <div class="checklist">${items}</div>
        </div>
      </div>
    `);
    // Bind checkbox visual state
    requestAnimationFrame(() => {
      document.querySelectorAll(".checklist-item input[type='checkbox']").forEach((cb, i) => {
        cb.addEventListener("change", () => {
          cb.closest(".checklist-item").classList.toggle("checked", cb.checked);
        });
      });
    });
  }

  // Validation
  if (n.validacion) {
    frags.push(`
      <div class="validation-box">
        <div class="validation-label">Validación</div>
        <div class="validation-question">${esc(n.validacion)}</div>
        <div class="validation-hint">
          Confirme con <strong>SÍ / Avanzar</strong> para continuar.
          Si selecciona <strong>NO</strong>, el paso quedará bloqueado.
        </div>
      </div>
    `);
  }

  elBody.innerHTML = frags.join("");
}

function renderDecisionBody(n) {
  const opts = (n.opciones || []).map((o, i) => `
    <label class="decision-option" id="dopt_${i}">
      <input type="radio" name="decision" value="${esc(o.next)}" data-label="${esc(o.label)}" />
      <span class="decision-option-label">${esc(o.label)}</span>
    </label>
  `).join("");

  elBody.innerHTML = `
    <div class="section-box">
      <div class="section-box-header">Selección</div>
      <div class="section-box-body">
        <div class="decision-options">${opts}</div>
        ${n.ayuda ? `<div class="ayuda-text">${esc(n.ayuda)}</div>` : ""}
      </div>
    </div>
  `;

  // Highlight selected radio
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
  if (n.inputs && n.inputs.length) {
    inputsHtml = n.inputs.map(spec => `
      <div class="input-group" style="margin-top:12px;">
        <label class="input-label" for="end_inp_${spec.key}">
          ${esc(spec.label)}${spec.required ? ' <span class="required">*</span>' : ""}
        </label>
        <input
          type="text"
          id="end_inp_${spec.key}"
          class="text-input"
          placeholder="${esc(spec.placeholder || "")}"
          data-key="${esc(spec.key)}"
          data-required="${spec.required ? "1" : "0"}"
          value="${esc(state.inputs[spec.key] || "")}"
        />
      </div>
    `).join("");
  }

  elBody.innerHTML = `
    <div class="end-box">
      <div class="end-icon">🏁</div>
      <div class="end-titulo">${esc(n.titulo)}</div>
      <div class="end-mensaje">${esc(n.mensaje || n.descripcion || "")}</div>
      <div class="end-estado">${esc(n.estado_final || "FINALIZADO")}</div>
      ${inputsHtml}
    </div>
  `;
}

function renderFooterState(n) {
  const isEnd = n.type === "end";

  elBtnBack.disabled = state.history.length === 0 || state.is_blocked;
  elBtnNo.classList.toggle("hidden", isEnd);
  elBtnNo.disabled = state.is_blocked;

  if (isEnd) {
    elBtnSi.textContent = "Exportar y cerrar";
  } else if (n.type === "decision") {
    elBtnSi.textContent = "Confirmar selección";
  } else {
    elBtnSi.textContent = "SÍ / Avanzar";
  }
  elBtnSi.disabled = state.is_blocked && !isEnd;
}

function renderBlockPanel() {
  elBlockMot.innerHTML = MOTIVOS_BLOQUEO.map((m, i) => `
    <label class="block-motivo-item">
      <input type="checkbox" id="bm_${i}" value="${esc(m)}" />
      ${esc(m)}
    </label>
  `).join("");
  elBlockDet.value = "";
}

function renderSummary() {
  // Inputs table
  const inputEntries = Object.entries(state.inputs);
  const inputRows = inputEntries.length
    ? inputEntries.map(([k,v]) => `<tr><td><b>${esc(k)}</b></td><td>${esc(v)}</td></tr>`).join("")
    : `<tr><td colspan="2">(sin datos)</td></tr>`;

  // Decisions table
  const decRows = state.decisiones.length
    ? state.decisiones.map(d => `
        <tr>
          <td>${esc(d.ts || "")}</td>
          <td>${esc(d.titulo || "")}</td>
          <td>${esc(d.seleccion || "")}</td>
        </tr>`).join("")
    : `<tr><td colspan="3">(sin decisiones)</td></tr>`;

  // Bloqueos table
  const bloqRows = state.bloqueos.length
    ? state.bloqueos.map(b => `
        <tr>
          <td>${esc(b.ts_inicio || "")}</td>
          <td>${esc(b.titulo || "")}</td>
          <td>${esc((b.motivos || []).join(", "))}</td>
          <td>${esc(b.detalle || "")}</td>
        </tr>`).join("")
    : `<tr><td colspan="4">(sin bloqueos)</td></tr>`;

  elSummaryTbl.innerHTML = `
    <table>
      <thead><tr><th>Campo</th><th>Valor</th></tr></thead>
      <tbody>${inputRows}</tbody>
    </table>
    <br>
    <table>
      <thead><tr><th>Timestamp</th><th>Nodo decisión</th><th>Selección</th></tr></thead>
      <tbody>${decRows}</tbody>
    </table>
    <br>
    <table>
      <thead><tr><th>Timestamp</th><th>Paso</th><th>Motivo(s)</th><th>Detalle</th></tr></thead>
      <tbody>${bloqRows}</tbody>
    </table>
  `;
}

// ── Validation helpers ─────────────────────────────────────────────────────
function collectInputs() {
  const fields = document.querySelectorAll(".text-input, [id^='end_inp_']");
  let ok = true;
  let missingLabel = "";
  fields.forEach(f => {
    const key = f.dataset.key;
    const val = f.value.trim();
    if (key) state.inputs[key] = val;
    if (f.dataset.required === "1" && !val) {
      ok = false;
      missingLabel = f.previousElementSibling?.textContent?.replace("*","").trim() || key;
    }
  });
  return { ok, missingLabel };
}

function checkChecklist() {
  const cbs = document.querySelectorAll(".checklist-item input[type='checkbox']");
  const labels = document.querySelectorAll(".checklist-item label");
  const required = [...cbs].filter((cb, i) => {
    const label = labels[i]?.textContent?.toLowerCase() || "";
    return !label.includes("si aplica") && !label.includes("(si aplica)");
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

  // Collect inputs first (always)
  const { ok: inputsOk, missingLabel } = collectInputs();
  if (!inputsOk) {
    showAlert(`Campo obligatorio: "${missingLabel}"`);
    return;
  }

  if (n.type === "end") {
    await persist();
    triggerExport();
    return;
  }

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
    if (!sel) {
      showAlert("Seleccione una opción antes de continuar.");
      return;
    }
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

  if (!motivos.length) {
    showAlert("Seleccione al menos un motivo de bloqueo.");
    return;
  }
  if (motivos.includes("Otro") && !detalle) {
    showAlert("Ingrese un detalle cuando selecciona 'Otro'.");
    return;
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

// ── Export ─────────────────────────────────────────────────────────────────
async function triggerExport() {
  await persist();
  window.location.href = `/api/session/${state.session_id}/export`;
  showToast("Exportando JSON de trazabilidad...");
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
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;");
}

// ── Start ──────────────────────────────────────────────────────────────────
init();
