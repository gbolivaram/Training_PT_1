/* ── HMI Procedimientos — main.js ─────────────────────────────────────────── */

// ── Theme toggle ───────────────────────────────────────────────────────────
(function initTheme() {
  const saved = localStorage.getItem("colbun_theme") || "corporativo";
  document.documentElement.setAttribute("data-theme", saved);
  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("btn-theme");
    const lbl = document.getElementById("theme-label");
    const themes = ["corporativo", "oscuro", "verde"];
    const names  = { corporativo: "Corporativo", oscuro: "🌙 Oscuro", verde: "Verde Natural" };
    if (lbl) lbl.textContent = names[saved] || "Corporativo";
    if (btn) {
      btn.addEventListener("click", () => {
        const cur = document.documentElement.getAttribute("data-theme") || "corporativo";
        const next = themes[(themes.indexOf(cur) + 1) % themes.length];
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("colbun_theme", next);
        lbl.textContent = names[next];
      });
    }
  });
})();

const TYPE_LABEL = { task: "Tarea", decision: "Decisión", end: "Fin" };

// ── App config (se llena al seleccionar PRO) ───────────────────────────────
let appAreas = null;   // JSON completo de areas.json
let appPro   = null;   // config del PRO activo (de areas.pros)
let appArea  = null;   // config del área activa

// ── State (sesión activa) ──────────────────────────────────────────────────
const state = {
  nodos: {},
  session_id: null,
  current_node: null,
  history: [],
  decisiones: [],
  bloqueos: [],
  inputs: {},
  logs: [],
  estado: "EN_CURSO",
  is_blocked: false,
  block_ts: null
};

// Chat state
const chatHistory = [];

// Manuales state
let appManuales = null;   // JSON completo de manuales.json

// ── Breadcrumb navigation stack ─────────────────────────────────────────────
// Each entry: { label, fn }  where fn() re-shows that screen (without repushing)
const navStack  = [];
let   _navBack  = false;   // flag: true while restoring via breadcrumb

function navPush(label, fn) {
  if (_navBack) return;
  navStack.push({ label, fn });
  renderBreadcrumb();
}

function navGoTo(idx) {
  navStack.splice(idx + 1);
  _navBack = true;
  navStack[idx].fn();
  _navBack = false;
  renderBreadcrumb();
}

function renderBreadcrumb() {
  const bc = $("breadcrumb");
  if (!bc) return;
  if (navStack.length < 2) { bc.classList.add("hidden"); return; }
  bc.classList.remove("hidden");
  bc.innerHTML = navStack.map((item, i) => {
    const isLast = i === navStack.length - 1;
    return isLast
      ? `<span class="bc-current">${esc(item.label)}</span>`
      : `<span class="bc-link" data-idx="${i}">${esc(item.label)}</span><span class="bc-sep">›</span>`;
  }).join("");
  bc.querySelectorAll(".bc-link").forEach(el =>
    el.addEventListener("click", () => navGoTo(+el.dataset.idx))
  );
}

// ── DOM refs ───────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

// screens
const screenHome          = $("screen-home");
const screenIntent        = $("screen-intent");
const screenProSelect     = $("screen-pro-select");
const screenInformChoice  = $("screen-inform-choice");
const screenManual        = $("screen-manual");
const screenDiagnose      = $("screen-diagnose");
const screenAiChat        = $("screen-ai-chat");
const screenChecklist     = $("screen-checklist");
const screenFlow          = $("screen-flow");

// header
const elBtnHome        = $("btn-home");
const elHeaderCode     = $("header-code");
const elHeaderTitle    = $("header-title");
const elHeaderRight    = $("header-right-checklist");
const elBtnSideToggle  = $("btn-sidebar-toggle");

// checklist
const elHeader        = $("node-header");
const elBody          = $("node-body");
const elBlockPanel    = $("block-panel");
const elAlert         = $("alert");
const elProgress      = $("progress-bar");
const elStepMeta      = $("step-meta");
const elSummary       = $("summary-panel");
const elSummaryTbl    = $("summary-tables");
const elBtnSi         = $("btn-si");
const elBtnNo         = $("btn-no");
const elBtnBack       = $("btn-back");
const elBtnRehacer    = $("btn-rehacer");
const elBtnExport     = $("btn-export");
const elBtnReset      = $("btn-reset");
const elBlockMot      = $("block-motivos");
const elBlockDet      = $("block-detalle");
const elToast         = $("toast");
const elTimeline      = $("timeline");
const elSidebar       = $("sidebar");
const elOverlay       = $("sidebar-overlay");
const elSideSession   = $("sidebar-session");
const elStopBar       = $("stop-bar");
const elBtnStop       = $("btn-stop");
const elFlowBar       = $("flow-bar");
const elBtnVerFlujo   = $("btn-ver-flujo");
const elBtnFlowBack   = $("btn-flow-back");
const elFlowBody      = $("flow-viewer-body");
const elFlowTitle     = $("flow-viewer-title");

// chat
const elChatMessages  = $("chat-messages");
const elChatInput     = $("chat-input");
const elBtnChatSend   = $("btn-chat-send");

// ── Screen management ──────────────────────────────────────────────────────
const ALL_SCREENS = [screenHome, screenIntent, screenProSelect, screenInformChoice, screenManual, screenDiagnose, screenAiChat, screenChecklist, screenFlow];

function showScreen(target) {
  ALL_SCREENS.forEach(s => s.classList.add("hidden"));
  target.classList.remove("hidden");

  const isChecklist = target === screenChecklist;
  elBtnSideToggle.classList.toggle("hidden", !isChecklist);
  elHeaderRight.style.display = isChecklist ? "flex" : "none";

  if (target === screenHome) {
    elHeaderCode.classList.add("hidden");
    elHeaderTitle.textContent = "Guía de Procedimientos Operativos";
  }
}

// ── Init ───────────────────────────────────────────────────────────────────
async function init() {
  const [resAreas, resManuales] = await Promise.all([
    fetch("/api/areas"),
    fetch("/api/manuales")
  ]);
  appAreas    = await resAreas.json();
  appManuales = await resManuales.json();
  renderHome();
  showScreen(screenHome);
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 1: HOME
// ══════════════════════════════════════════════════════════════════════════
// ── Area metadata: icon + description per area id ─────────────────────────
const AREA_META = {
  bodega:        { icon: "🏭", desc: "Compras, abastecimiento y recepción de materiales." },
  fallas:        { icon: "⚡", desc: "Respuesta ante fallas, emergencias y crisis operacionales." },
  inventario:    { icon: "📦", desc: "Control de stock, almacén, obsolescencia y despacho." },
  mantenimiento: { icon: "🔧", desc: "Mantenimiento preventivo, correctivo y operación de equipos." },
  ma_suspel:     { icon: "🌿", desc: "Manuales de Medio Ambiente y Suspensiones Eléctricas." },
  seguridad:     { icon: "🛡️", desc: "Seguridad operacional, riesgos y normativa de planta." },
};

function renderHome() {
  navStack.length = 0;
  navStack.push({ label: "Inicio", fn: () => {
    elHeaderCode.classList.add("hidden");
    elHeaderTitle.textContent = "Guía de Procedimientos Operativos";
    showScreen(screenHome);
    renderBreadcrumb();
  }});
  renderBreadcrumb();

  const areaList  = $("home-area-list");
  const proPanel  = $("home-pro-panel");
  if (!areaList || !proPanel || !appAreas) return;

  // ── Render area list items ──────────────────────────────────────
  const items = appAreas.areas.map(area => {
    const hasPros    = area.pros.length > 0;
    const soloManual = area.solo_informarme === true;
    const isActive   = hasPros || soloManual;
    const meta       = AREA_META[area.id] || { icon: "📋" };
    let countTxt;
    if (hasPros)         countTxt = `${area.pros.length} procedimiento${area.pros.length > 1 ? "s" : ""}`;
    else if (soloManual) countTxt = "Manuales disponibles";
    else                 countTxt = "Próximamente";

    return `
      <button class="home-area-item ${isActive ? "" : "home-area-item-disabled"}"
              data-area-id="${esc(area.id)}" ${isActive ? "" : "disabled"}>
        <span class="home-area-item-icon">${meta.icon}</span>
        <span class="home-area-item-info">
          <span class="home-area-item-name">${esc(area.nombre)}</span>
          <span class="home-area-item-count">${countTxt}</span>
        </span>
      </button>`;
  }).join("");

  // Re-render only the items (keep the header)
  const header = areaList.querySelector(".home-area-list-header");
  areaList.innerHTML = "";
  if (header) areaList.appendChild(header);
  areaList.insertAdjacentHTML("beforeend", items);

  // ── Show procedures panel for an area ──────────────────────────
  function showProPanel(area) {
    const meta    = AREA_META[area.id] || { icon: "📋", desc: "" };
    const hasPros = area.pros.length > 0;

    // Active state on list
    areaList.querySelectorAll(".home-area-item").forEach(el =>
      el.classList.toggle("active", el.dataset.areaId === area.id));

    if (area.solo_informarme) {
      // Manuales-only area
      proPanel.innerHTML = `
        <div class="home-pro-panel-content">
          <div class="home-pro-panel-header">
            <span class="home-pro-panel-icon">${meta.icon}</span>
            <div>
              <div class="home-pro-panel-title">${esc(area.nombre)}</div>
              <div class="home-pro-panel-sub">Manuales y documentación disponible</div>
            </div>
          </div>
          <div class="home-manual-cta">
            <div class="home-manual-cta-desc">${esc(meta.desc)}</div>
            <button class="home-manual-btn" id="btn-ver-manuales">
              📄 Ver manuales y documentación →
            </button>
          </div>
        </div>`;
      $("btn-ver-manuales").addEventListener("click", () => {
        navPush(area.nombre, () => { appArea = appAreas.areas.find(a => a.id === area.id); showInformChoice(appArea); });
        showInformChoice(area);
      });
      return;
    }

    if (!hasPros) {
      proPanel.innerHTML = `
        <div class="home-pro-panel-content home-pro-empty">
          <div class="home-pro-empty-icon">🔒</div>
          <div class="home-pro-empty-text">Próximamente — contenido en preparación</div>
        </div>`;
      return;
    }

    // Build PRO cards
    const proCards = area.pros.map(proId => {
      const pro = appAreas.pros[proId];
      if (!pro) return "";
      const desc = (pro.descripcion || "").slice(0, 90) + (pro.descripcion?.length > 90 ? "…" : "");
      return `
        <button class="home-pro-card" data-pro-id="${esc(proId)}" data-area-id="${esc(area.id)}">
          <span class="home-pro-card-badge">${esc(proId)}</span>
          <span class="home-pro-card-body">
            <span class="home-pro-card-name">${esc(pro.nombre || proId)}</span>
            <span class="home-pro-card-desc">${esc(desc)}</span>
          </span>
        </button>`;
    }).join("");

    proPanel.innerHTML = `
      <div class="home-pro-panel-content">
        <div class="home-pro-panel-header">
          <span class="home-pro-panel-icon">${meta.icon}</span>
          <div>
            <div class="home-pro-panel-title">${esc(area.nombre)}</div>
            <div class="home-pro-panel-sub">${area.pros.length} procedimiento${area.pros.length > 1 ? "s" : ""} disponible${area.pros.length > 1 ? "s" : ""}</div>
          </div>
        </div>
        <div class="home-pro-grid">${proCards}</div>
      </div>`;

    // Click on a PRO card → go to intent (with pre-selected PRO)
    proPanel.querySelectorAll(".home-pro-card").forEach(btn => {
      btn.addEventListener("click", () => {
        const proId  = btn.dataset.proId;
        const areaId = btn.dataset.areaId;
        appArea = appAreas.areas.find(a => a.id === areaId);
        appPro  = appAreas.pros[proId];
        // Store selected proId so handleIntent can skip the PRO select screen
        appArea._selectedProId = proId;
        showIntent(appArea);
      });
    });
  }

  // ── Area item click ─────────────────────────────────────────────
  areaList.querySelectorAll(".home-area-item:not([disabled])").forEach(btn => {
    btn.addEventListener("click", () => {
      const area = appAreas.areas.find(a => a.id === btn.dataset.areaId);
      if (area) showProPanel(area);
    });
  });

  // Auto-select first active area
  const firstActive = appAreas.areas.find(a => a.pros.length > 0 || a.solo_informarme);
  if (firstActive) showProPanel(firstActive);
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 2: INTENT
// ══════════════════════════════════════════════════════════════════════════
function showIntent(area) {
  appArea = area;
  navPush(area.nombre, () => showIntent(area));
  $("intent-area-badge").textContent = area.nombre;
  elHeaderTitle.textContent = area.nombre;
  screenIntent.querySelectorAll(".intent-btn").forEach(btn => {
    btn.onclick = () => handleIntent(area, btn.dataset.intent);
  });
  showScreen(screenIntent);
}

function handleIntent(area, intent) {
  // If a specific PRO was pre-selected from the home panel, skip PRO select screen
  const preselected = area._selectedProId;
  delete area._selectedProId;

  if (intent === "ejecutar") {
    if (preselected) {
      startPro(preselected, area.id);
    } else if (area.pros.length === 1) {
      startPro(area.pros[0], area.id);
    } else {
      showProSelect(area);
    }
  } else if (intent === "informarme") {
    showInformChoice(area);
  } else if (intent === "resolver") {
    showDiagnose(area);
  } else {
    // Reportar → IA chat
    if (preselected) {
      startAiChat(preselected, area.id, intent);
    } else if (area.pros.length === 1) {
      startAiChat(area.pros[0], area.id, intent);
    } else {
      showProSelectForChat(area, intent);
    }
  }
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 3b: INFORM CHOICE
// ══════════════════════════════════════════════════════════════════════════
function showInformChoice(area) {
  navPush("Informarme", () => showInformChoice(area));
  $("inform-choice-badge").textContent = area.nombre;
  elHeaderTitle.textContent = area.nombre;

  const manualIds = appManuales?.por_area?.[area.id] || [];
  const manuales  = manualIds.map(id => appManuales.manuales[id]).filter(Boolean);

  const grid = $("inform-choice-grid");
  let html = `
    <button class="intent-btn" id="ic-btn-ia">
      <span class="intent-icon">🤖</span>
      <span class="intent-label">Preguntar a la IA</span>
      <span class="intent-desc">Consultar dudas con el asistente inteligente</span>
    </button>`;

  manuales.forEach(m => {
    html += `
      <button class="intent-btn ic-btn-manual" data-manual-id="${esc(m.id)}">
        <span class="intent-icon">📖</span>
        <span class="intent-label">Ver manual</span>
        <span class="intent-desc">${esc(m.codigo)} — ${esc(m.nombre)}</span>
      </button>`;
  });

  if (!manuales.length) {
    html += `
      <div class="intent-btn" style="opacity:.5;cursor:default;">
        <span class="intent-icon">📖</span>
        <span class="intent-label">Ver manual</span>
        <span class="intent-desc">No hay manuales disponibles para esta área aún</span>
      </div>`;
  }

  grid.innerHTML = html;

  $("ic-btn-ia").onclick = () => {
    if (area.pros.length === 1) {
      startAiChat(area.pros[0], area.id, "informarme");
    } else {
      showProSelectForChat(area, "informarme");
    }
  };

  grid.querySelectorAll(".ic-btn-manual").forEach(btn => {
    btn.addEventListener("click", () => {
      const manual = appManuales.manuales[btn.dataset.manualId];
      if (manual) showManual(manual, area.nombre);
    });
  });

  showScreen(screenInformChoice);
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 3c: MANUAL VIEWER
// ══════════════════════════════════════════════════════════════════════════
const SECCION_ICONS = {
  stop:     "⛔",
  conexion: "🔗",
  pasos:    "📋",
  lista:    "👥",
  texto:    "ℹ"
};

function showManual(manual, areaNombre) {
  const lbl = manual.codigo + " — " + (manual.nombre.length > 28 ? manual.nombre.slice(0, 28) + "…" : manual.nombre);
  navPush(lbl, () => showManual(manual, areaNombre));
  elHeaderTitle.textContent = manual.nombre;

  $("manual-header").innerHTML = `
    <div class="manual-codigo-badge">${esc(manual.codigo)}</div>
    <div class="manual-nombre">${esc(manual.nombre)}</div>
    <div class="manual-foco">${esc(manual.foco)}</div>
    <div class="manual-area-tag">${esc(areaNombre)}</div>`;

  const body = $("manual-body");
  body.innerHTML = manual.secciones.map(sec => {
    const icon = SECCION_ICONS[sec.tipo] || "ℹ";
    const isStop = sec.tipo === "stop";
    const sectionClass = isStop ? "manual-section manual-section-stop" : "manual-section";

    let contenidoHtml = "";
    if (sec.contenido) {
      contenidoHtml = `<p class="manual-text">${esc(sec.contenido)}</p>`;
    }
    if (sec.items?.length) {
      const liItems = sec.items.map(item => `<li>${esc(item)}</li>`).join("");
      contenidoHtml += `<ul class="manual-list">${liItems}</ul>`;
    }

    return `
      <div class="${sectionClass}">
        <div class="manual-section-header">
          <span class="manual-section-icon">${icon}</span>
          <span class="manual-section-title">${esc(sec.titulo)}</span>
        </div>
        <div class="manual-section-body">${contenidoHtml}</div>
      </div>`;
  }).join("");

  showScreen(screenManual);
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 3: PRO SELECT
// ══════════════════════════════════════════════════════════════════════════
function showProSelect(area) {
  navPush("Seleccionar procedimiento", () => showProSelect(area));
  $("pro-select-badge").textContent = area.nombre;

  const list = $("pro-list");
  list.innerHTML = area.pros.map(proId => {
    const pro = appAreas.pros[proId];
    return `
      <button class="pro-card" data-pro-id="${esc(proId)}">
        <span class="pro-id-badge">${esc(proId)}</span>
        <div class="pro-card-body">
          <div class="pro-card-nombre">${esc(pro.nombre)}</div>
          <div class="pro-card-desc">${esc(pro.descripcion)}</div>
        </div>
        <span class="pro-card-arrow">›</span>
      </button>`;
  }).join("");

  list.querySelectorAll(".pro-card").forEach(btn => {
    btn.addEventListener("click", () => startPro(btn.dataset.proId, area.id));
  });

  showScreen(screenProSelect);
}

function showProSelectForChat(area, intent) {
  navPush("Seleccionar procedimiento", () => showProSelectForChat(area, intent));
  $("pro-select-badge").textContent = area.nombre;

  const list = $("pro-list");
  list.innerHTML = area.pros.map(proId => {
    const pro = appAreas.pros[proId];
    return `
      <button class="pro-card" data-pro-id="${esc(proId)}" data-intent="${esc(intent)}">
        <span class="pro-id-badge">${esc(proId)}</span>
        <div class="pro-card-body">
          <div class="pro-card-nombre">${esc(pro.nombre)}</div>
          <div class="pro-card-desc">${esc(pro.descripcion)}</div>
        </div>
        <span class="pro-card-arrow">›</span>
      </button>`;
  }).join("");

  list.querySelectorAll(".pro-card").forEach(btn => {
    btn.addEventListener("click", () => startAiChat(btn.dataset.proId, area.id, btn.dataset.intent));
  });

  showScreen(screenProSelect);
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 4: AI CHAT
// ══════════════════════════════════════════════════════════════════════════
const INTENT_LABELS = {
  informarme: "Informarme sobre el procedimiento",
  resolver:   "Resolver un problema",
  reportar:   "Reportar / cerrar"
};

function startAiChat(proId, areaId, intent) {
  navPush("Asistente IA", () => startAiChat(proId, areaId, intent));
  appPro = appAreas.pros[proId];
  chatHistory.length = 0;

  const intentLabel = INTENT_LABELS[intent] || intent;
  $("chat-pro-badge").innerHTML = `
    <span class="pro-id-badge">${esc(proId)}</span>
    <span>${esc(appPro.nombre)}</span>
    <span class="chat-intent-tag">${esc(intentLabel)}</span>`;

  elChatMessages.innerHTML = `
    <div class="chat-bubble assistant">
      <strong>Asistente</strong>
      <p>Hola, estoy aquí para ayudarte con <strong>${esc(appPro.nombre)}</strong>.<br>
      ¿Cuál es tu consulta?</p>
    </div>`;

  elHeaderCode.textContent = proId;
  elHeaderCode.classList.remove("hidden");
  elHeaderTitle.textContent = appPro.nombre;

  showScreen(screenAiChat);

  elChatInput.value = "";
  elChatInput.focus();

  elBtnChatSend.onclick = () => sendChatMessage(proId, areaId);
  elChatInput.onkeydown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChatMessage(proId, areaId); }
  };
}

async function sendChatMessage(proId, areaId) {
  const text = elChatInput.value.trim();
  if (!text) return;

  elChatInput.value = "";
  appendChatBubble("user", text);
  chatHistory.push({ role: "user", content: text });

  const typingEl = appendChatBubble("assistant", "…");

  try {
    const res = await fetch("/api/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: chatHistory, pro_id: proId, area_id: areaId })
    });
    const data = await res.json();
    const reply = data.reply || "Sin respuesta.";
    typingEl.querySelector("p").textContent = reply;
    chatHistory.push({ role: "assistant", content: reply });
  } catch (e) {
    typingEl.querySelector("p").textContent = "Error de conexión. Intenta nuevamente.";
  }
  elChatMessages.scrollTop = elChatMessages.scrollHeight;
}

function appendChatBubble(role, text) {
  const div = document.createElement("div");
  div.className = `chat-bubble ${role}`;
  div.innerHTML = `<strong>${role === "user" ? "Tú" : "Asistente"}</strong><p>${esc(text)}</p>`;
  elChatMessages.appendChild(div);
  elChatMessages.scrollTop = elChatMessages.scrollHeight;
  return div;
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 5: CHECKLIST
// ══════════════════════════════════════════════════════════════════════════
async function startPro(proId, areaId) {
  appPro = appAreas.pros[proId];
  navPush(proId, () => startPro(proId, areaId));

  const res = await fetch(`/api/pro/${proId}/nodos`);
  state.nodos = await res.json();

  // Try to restore saved session for this PRO
  const savedKey = `hmi_session_${proId}`;
  const saved = localStorage.getItem(savedKey);
  if (saved) {
    try {
      const r = await fetch(`/api/session/${saved}`);
      if (r.ok) {
        const s = await r.json();
        if (s.pro_id === proId) {
          restoreState(s);
          setupChecklistUI(proId, areaId);
          render();
          return;
        }
      }
    } catch(_) {}
  }
  await newSession(proId, areaId);
}

function restoreState(s) {
  state.session_id   = s.session_id;
  state.current_node = s.current_node;
  state.history      = s.history;
  state.decisiones   = s.decisiones;
  state.bloqueos     = s.bloqueos;
  state.inputs       = s.inputs;
  state.logs         = s.logs;
  state.estado       = s.estado;
  state.is_blocked   = false;
  state.block_ts     = null;
}

async function newSession(proId, areaId) {
  const r = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pro_id: proId, area_id: areaId })
  });
  const s = await r.json();
  state.session_id   = s.session_id;
  state.current_node = s.current_node;
  state.history      = [];
  state.decisiones   = [];
  state.bloqueos     = [];
  state.inputs       = {};
  state.logs         = [];
  state.estado       = "EN_CURSO";
  state.is_blocked   = false;
  state.block_ts     = null;
  localStorage.setItem(`hmi_session_${proId}`, s.session_id);
  setupChecklistUI(proId, areaId);
  render();
}

function setupChecklistUI(proId, areaId) {
  elHeaderCode.textContent = proId;
  elHeaderCode.classList.remove("hidden");
  elHeaderTitle.textContent = appPro.nombre;

  // STOP button visibility
  if (appPro.has_stop) {
    elStopBar.classList.remove("hidden");
  } else {
    elStopBar.classList.add("hidden");
  }

  // Flow button — siempre visible en el checklist
  elFlowBar.classList.remove("hidden");

  showScreen(screenChecklist);
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
  const flowOrder = appPro?.flow_order || [];
  const idx = flowOrder.indexOf(state.current_node);
  const pct = idx < 0 ? 0 : Math.round(((idx + 1) / flowOrder.length) * 100);
  elProgress.style.width = pct + "%";
  const step = idx < 0 ? "—" : `Paso ${idx + 1} / ${flowOrder.length}`;
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
      </div>`;
  }).join("");

  requestAnimationFrame(() => {
    const active = elTimeline.querySelector(".tl-current");
    if (active) active.scrollIntoView({ block: "nearest", behavior: "smooth" });
  });
}

// ── Sidebar toggle (mobile) ────────────────────────────────────────────────
function openSidebar()  { elSidebar.classList.add("open");    elOverlay.classList.add("visible"); }
function closeSidebar() { elSidebar.classList.remove("open"); elOverlay.classList.remove("visible"); }
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
  if (n.type === "task")            renderTaskBody(n);
  else if (n.type === "decision")   renderDecisionBody(n);
  else if (n.type === "end")        renderEndBody(n);
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
  const isStop    = state.current_node === "END_STOP";
  const isRechazo = state.current_node === "END_RECHAZO";
  const boxClass  = isStop || isRechazo ? "end-box end-box-danger" : "end-box";

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

  const icon = isStop ? "⛔" : isRechazo ? "⚠" : "🏁";

  const irAProHtml = n.ir_a_pro
    ? `<button class="btn btn-si btn-ir-a-pro" id="btn-ir-a-pro" style="margin-top:16px;width:100%;">
        ➡ Ir a ${esc(n.ir_a_pro.pro_id)}
       </button>`
    : "";

  elBody.innerHTML = `
    <div class="${boxClass}">
      <div class="end-icon">${icon}</div>
      <div class="end-titulo">${esc(n.titulo)}</div>
      <div class="end-mensaje">${esc(n.mensaje || n.descripcion || "")}</div>
      <div class="end-estado">${esc(n.estado_final || "FINALIZADO")}</div>
      ${inputsHtml}
      ${irAProHtml}
      <button class="btn-download" id="btn-download-inline">
        ⬇ Descargar trazabilidad JSON
      </button>
    </div>`;

  requestAnimationFrame(() => {
    $("btn-download-inline")?.addEventListener("click", () => triggerExport());
    if (n.ir_a_pro) {
      $("btn-ir-a-pro")?.addEventListener("click", () => {
        startPro(n.ir_a_pro.pro_id, n.ir_a_pro.area_id);
      });
    }
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
  const motivos = appPro?.motivos_bloqueo || ["Otro"];
  elBlockMot.innerHTML = motivos.map((m, i) => `
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

elBtnStop?.addEventListener("click", async () => {
  if (!confirm("¿Detener el proceso? Esto registrará un STOP en la trazabilidad.")) return;
  log("STOP", { nodo: state.current_node });
  state.history.push(state.current_node);
  state.current_node = "END_STOP";
  state.estado = "DETENIDO";
  await persist();
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
    ts_fin:    new Date().toISOString(),
    nodo:      state.current_node,
    titulo:    state.nodos[state.current_node]?.titulo || "",
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

elBtnExport?.addEventListener("click", () => triggerExport());

elBtnReset?.addEventListener("click", async () => {
  if (!confirm("¿Reiniciar sesión? Se perderá el progreso actual.")) return;
  const proId = appPro?.id;
  if (proId) localStorage.removeItem(`hmi_session_${proId}`);
  await newSession(appPro.id, appArea?.id || "");
  showToast("Sesión reiniciada");
});

// ── Home button ────────────────────────────────────────────────────────────
elBtnHome?.addEventListener("click", () => {
  appPro  = null;
  appArea = null;
  chatHistory.length = 0;
  elHeaderCode.classList.add("hidden");
  elHeaderTitle.textContent = "Guía de Procedimientos Operativos";
  navStack.length = 0;
  renderBreadcrumb();
  showScreen(screenHome);
  renderHome();
});

// ── Export ─────────────────────────────────────────────────────────────────
async function triggerExport() {
  await persist();
  try {
    const r    = await fetch(`/api/session/${state.session_id}/export`);
    const blob = await r.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `${appPro?.id || "PRO"}_${state.session_id.slice(0,8)}.json`;
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

// ══════════════════════════════════════════════════════════════════════════
// FEEDBACK WIDGET
// ══════════════════════════════════════════════════════════════════════════

(function initFeedback() {
  const tab      = $("fb-tab");
  const panel    = $("fb-panel");
  const closeBtn = $("fb-close");
  const textarea = $("fb-textarea");
  const submitBtn = $("fb-submit");
  const charCount = $("fb-char-count");
  const success  = $("fb-success");
  const locEl    = $("fb-location");

  if (!tab || !panel) return;

  function currentPath() {
    if (!navStack.length) return "Inicio";
    let path = navStack.map(s => s.label).join(" › ");
    // Si hay un nodo activo dentro de un PRO, añadir el paso exacto
    if (state.current_node && state.nodos && state.nodos[state.current_node]) {
      const flowOrder = appPro?.flow_order || [];
      const idx = flowOrder.indexOf(state.current_node);
      const stepNum = idx >= 0 ? `Paso ${idx + 1}` : state.current_node;
      const stepTitle = state.nodos[state.current_node].titulo || state.current_node;
      path += ` › ${stepNum}: ${stepTitle}`;
    }
    return path;
  }

  function getCurrentProId() {
    if (!appPro || !appAreas) return "";
    return Object.keys(appAreas.pros).find(k => appAreas.pros[k] === appPro) || "";
  }

  function openPanel() {
    if (locEl) locEl.textContent = "📍 " + currentPath();
    if (textarea) textarea.value = "";
    if (charCount) charCount.textContent = "0 / 500";
    if (success) success.classList.add("hidden");
    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Enviar"; }
    panel.classList.remove("hidden");
    setTimeout(() => panel.classList.add("fb-panel-open"), 10);
    if (textarea) textarea.focus();
  }

  function closePanel() {
    panel.classList.remove("fb-panel-open");
    setTimeout(() => panel.classList.add("hidden"), 200);
  }

  tab.addEventListener("click", () => {
    panel.classList.contains("hidden") ? openPanel() : closePanel();
  });
  closeBtn?.addEventListener("click", closePanel);

  textarea?.addEventListener("input", () => {
    if (charCount) charCount.textContent = `${textarea.value.length} / 500`;
  });

  submitBtn?.addEventListener("click", async () => {
    const comentario = (textarea?.value || "").trim();
    if (!comentario) { textarea?.focus(); return; }

    submitBtn.disabled = true;
    submitBtn.textContent = "Enviando…";

    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          comentario,
          pantalla: currentPath(),
          area_id:  appArea?.id || "",
          pro_id:   getCurrentProId()
        })
      });
      if (!res.ok) throw new Error("Error " + res.status);
      if (success) success.classList.remove("hidden");
      if (textarea) textarea.value = "";
      if (charCount) charCount.textContent = "0 / 500";
      setTimeout(closePanel, 1800);
    } catch (e) {
      submitBtn.disabled = false;
      submitBtn.textContent = "Enviar";
      showToast("Error al enviar el comentario. Intenta de nuevo.", true);
    }
  });

  document.addEventListener("click", (e) => {
    if (!panel.classList.contains("hidden") &&
        !panel.contains(e.target) && !tab.contains(e.target)) {
      closePanel();
    }
  });
})();

// ══════════════════════════════════════════════════════════════════════════
// SCREEN: DIAGNOSE — Resolver problema con búsqueda por palabras clave
// ══════════════════════════════════════════════════════════════════════════
const DIAGNOSE_CHIPS = [
  "material", "repuesto", "EPP", "stock", "inventario",
  "devolución", "recepción", "falla", "emergencia", "bloqueo",
  "servicio", "consumo", "creación", "bodega"
];

function showDiagnose(area) {
  navPush("Resolver problema", () => showDiagnose(area));
  elHeaderTitle.textContent = "Resolver problema";

  const badge = $("diagnose-area-badge");
  if (badge) badge.textContent = area ? area.nombre : "Todas las áreas";

  // Chips de palabras clave
  const chipsEl = $("diagnose-chips");
  if (chipsEl) {
    chipsEl.innerHTML = DIAGNOSE_CHIPS.map(k =>
      `<span class="diagnose-chip" data-kw="${esc(k)}">${esc(k)}</span>`
    ).join("");
    chipsEl.querySelectorAll(".diagnose-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const inp = $("diagnose-input");
        if (!inp) return;
        inp.value = chip.dataset.kw;
        chipsEl.querySelectorAll(".diagnose-chip").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        runDiagnoseSearch(area, chip.dataset.kw);
      });
    });
  }

  // Input de búsqueda — clonar para limpiar listeners previos
  const oldInp = $("diagnose-input");
  if (oldInp) {
    const inp = oldInp.cloneNode(true);
    oldInp.parentNode.replaceChild(inp, oldInp);
    inp.value = "";
    inp.focus();
    inp.addEventListener("input", () => {
      chipsEl?.querySelectorAll(".diagnose-chip").forEach(c => c.classList.remove("active"));
      runDiagnoseSearch(area, inp.value.trim());
    });
  }

  runDiagnoseSearch(area, "");
  showScreen(screenDiagnose);
}

function runDiagnoseSearch(area, query) {
  const results = $("diagnose-results");
  if (!results || !appAreas) return;

  const lq = query.toLowerCase().trim();

  // Recopilar todos los PROs de todas las áreas
  let candidates = [];
  appAreas.areas.forEach(a => {
    a.pros.forEach(proId => {
      const pro = appAreas.pros[proId];
      if (pro) candidates.push({ pro, proId, areaNombre: a.nombre, areaId: a.id });
    });
  });

  // Filtrar por query (todas las palabras deben aparecer)
  if (lq) {
    candidates = candidates.filter(c => {
      const haystack = [
        c.pro.nombre, c.pro.descripcion, c.areaNombre,
        ...(c.pro.motivos_bloqueo || [])
      ].join(" ").toLowerCase();
      return lq.split(/\s+/).every(w => haystack.includes(w));
    });
  }

  if (!candidates.length) {
    results.innerHTML = `
      <div class="diagnose-empty">
        No se encontraron procedimientos para <strong>"${esc(query)}"</strong>.<br>
        Intenta con otras palabras clave o usa el asistente IA.
      </div>`;
    return;
  }

  results.innerHTML = candidates.map(c => `
    <div class="diagnose-card">
      <div class="diagnose-card-top">
        <span class="pro-id-badge">${esc(c.proId)}</span>
        <span class="diagnose-area-tag">${esc(c.areaNombre)}</span>
      </div>
      <div class="diagnose-card-nombre">${esc(c.pro.nombre)}</div>
      <div class="diagnose-card-desc">${esc(c.pro.descripcion)}</div>
      <div class="diagnose-card-actions">
        <button class="btn btn-si diagnose-exec"
          data-pro-id="${esc(c.proId)}" data-area-id="${esc(c.areaId)}">
          ▶ Ejecutar
        </button>
        <button class="btn btn-back diagnose-chat"
          data-pro-id="${esc(c.proId)}" data-area-id="${esc(c.areaId)}">
          🤖 Consultar IA
        </button>
      </div>
    </div>`).join("");

  results.querySelectorAll(".diagnose-exec").forEach(btn =>
    btn.addEventListener("click", () => startPro(btn.dataset.proId, btn.dataset.areaId))
  );
  results.querySelectorAll(".diagnose-chat").forEach(btn =>
    btn.addEventListener("click", () => startAiChat(btn.dataset.proId, btn.dataset.areaId, "resolver"))
  );
}

// ══════════════════════════════════════════════════════════════════════════
// SCREEN 6: FLOW VIEWER
// ══════════════════════════════════════════════════════════════════════════
function showFlow() {
  const proId   = appPro?.id || "";
  const pdfUrl  = appPro?.flow_pdf || null;

  elFlowTitle.textContent = `Flujo — ${proId}: ${appPro?.nombre || ""}`;
  elFlowBody.innerHTML    = "";

  if (pdfUrl) {
    const iframe = document.createElement("iframe");
    iframe.className = "flow-pdf-iframe";
    iframe.src       = pdfUrl;
    iframe.title     = `Flujo ${proId}`;
    elFlowBody.appendChild(iframe);
  } else {
    elFlowBody.innerHTML = `
      <div class="flow-placeholder">
        <div class="flow-placeholder-icon">📋</div>
        <div class="flow-placeholder-title">Flujo no disponible aún</div>
        <div class="flow-placeholder-sub">El diagrama de flujo para <strong>${esc(proId)}</strong> será publicado próximamente.</div>
      </div>`;
  }

  showScreen(screenFlow);
}

// Wire up flow buttons
document.addEventListener("DOMContentLoaded", () => {
  if (elBtnVerFlujo)  elBtnVerFlujo.addEventListener("click", showFlow);
  if (elBtnFlowBack)  elBtnFlowBack.addEventListener("click", () => showScreen(screenChecklist));
});

// ── Start ──────────────────────────────────────────────────────────────────
init();
