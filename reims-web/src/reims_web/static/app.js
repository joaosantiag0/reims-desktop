/* Reims Web SPA — vanilla JS, no build step.
 * Talks to the FastAPI backend (/api/*) with bearer-token auth and i18n
 * dictionaries served from the shared reims-gui locale files.
 */
"use strict";

// ---------------------------------------------------------------- state
const state = {
  lang: localStorage.getItem("reims.lang") || "pt_BR",
  dict: {},
  token: sessionStorage.getItem("reims.token") || null,
  authRequired: false,
  vms: [],
  statsHistory: { cpu: [], ram: [] },
  activeVm: null,
  ws: null,
  taskPoll: null,
};

// ---------------------------------------------------------------- i18n
function t(key, params) {
  const v = state.dict[key];
  let val = (v !== undefined && v !== null) ? v : key;
  if (params && typeof val === "string") {
    for (const [k, p] of Object.entries(params)) {
      val = val.split(`{${k}}`).join(String(p));
    }
  }
  return val;
}

function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const val = t(el.dataset.i18n);
    if (val) el.textContent = val;
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const val = t(el.dataset.i18nPlaceholder);
    if (val) el.placeholder = val;
  });
  document.documentElement.lang = state.lang.replace("_", "-");
}

async function loadI18n(lang) {
  state.lang = lang;
  localStorage.setItem("reims.lang", lang);
  const res = await fetch(`/api/i18n?lang=${encodeURIComponent(lang)}`);
  const data = await res.json();
  state.dict = data.translations || {};
  applyI18n();
}

// ---------------------------------------------------------------- api
function authHeaders() {
  const h = { "Content-Type": "application/json" };
  if (state.token) h.Authorization = `Bearer ${state.token}`;
  return h;
}

async function api(path, options = {}) {
  const res = await fetch(path, { headers: authHeaders(), ...options });
  if (res.status === 401) {
    showLogin();
    throw new Error(t("web.error.unauthorized"));
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.detail || `HTTP ${res.status}`);
  return data;
}

// ---------------------------------------------------------------- toasts
function toast(message, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  document.getElementById("toasts").appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ---------------------------------------------------------------- auth
function showLogin() {
  state.token = null;
  sessionStorage.removeItem("reims.token");
  document.getElementById("app").classList.add("hidden");
  document.getElementById("loginScreen").classList.remove("hidden");
  document.getElementById("logoutBtn").classList.add("hidden");
}

async function tryStart() {
  const status = await fetch("/api/auth/status").then((r) => r.json());
  state.authRequired = status.auth_required;
  if (state.authRequired) {
    if (!state.token) {
      showLogin();
      return false;
    }
    // Validate the stored token with a cheap call.
    try {
      await api("/api/vms");
    } catch (e) {
      return false;
    }
  }
  document.getElementById("loginScreen").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
  document.getElementById("logoutBtn").classList.toggle("hidden", !state.authRequired);
  return true;
}

document.getElementById("loginForm").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const err = document.getElementById("loginError");
  err.classList.add("hidden");
  try {
    const data = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ password: document.getElementById("loginPassword").value }),
    });
    state.token = data.token;
    sessionStorage.setItem("reims.token", data.token);
    document.getElementById("loginPassword").value = "";
    if (await tryStart()) await startPolling();
  } catch (e) {
    err.classList.remove("hidden");
  }
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  try { await api("/api/logout", { method: "POST" }); } catch (e) { /* ignore */ }
  state.token = null;
  sessionStorage.removeItem("reims.token");
  showLogin();
});

// ---------------------------------------------------------------- vms
function statusClass(status) {
  return { running: "status-running", stopped: "status-stopped" }[status] || "status-error";
}

function renderVms() {
  const grid = document.getElementById("vmGrid");
  const list = document.getElementById("vmList");
  const empty = document.getElementById("vmEmpty");
  grid.innerHTML = "";
  list.innerHTML = "";
  empty.classList.toggle("hidden", state.vms.length > 0);

  for (const vm of state.vms) {
    // Sidebar entry
    const li = document.createElement("li");
    li.dataset.name = vm.name;
    if (state.activeVm === vm.name) li.classList.add("active");
    li.innerHTML = `<span class="vm-dot" style="background:${
      vm.status === "running" ? "var(--ok)" : "var(--muted)"
    }"></span><span>${vm.name}</span>`;
    li.addEventListener("click", () => {
      state.activeVm = vm.name;
      renderVms();
    });
    list.appendChild(li);

    // Card
    const card = document.createElement("div");
    card.className = "vm-card";
    card.innerHTML = `
      <div class="vm-card-head">
        <span class="vm-name">${vm.name}</span>
        <span class="status-pill ${statusClass(vm.status)}">${t(`vm.status.${vm.status}`)}</span>
      </div>
      <div class="vm-specs">
        <span>${t("vm.specs.vcpu")}: <strong>${vm.cpus}</strong></span>
        <span>${t("vm.specs.memory")}: <strong>${vm.memory_gib} GB</strong></span>
        <span>${t("vm.specs.disk")}: <strong>${vm.disk_size_gb ?? "?"} GB</strong></span>
        <span>${t("vm.specs.gpu")}: <strong>${vm.gpu_name || "Auto"}</strong></span>
        <span style="grid-column:1/-1">${vm.macos_version}</span>
      </div>
      <div class="vm-actions">
        ${vm.status !== "running"
          ? `<button class="btn btn-accent" data-act="start">${t("vm.actions.start")}</button>`
          : `<button class="btn" data-act="stop">${t("vm.actions.stop")}</button>
             <button class="btn btn-danger" data-act="force">${t("vm.actions.force_stop")}</button>`}
        <button class="btn" data-act="console">${t("vm.actions.view")}</button>
        <button class="btn btn-danger" data-act="delete">${t("vm.actions.delete")}</button>
      </div>`;
    card.querySelectorAll("[data-act]").forEach((btn) => {
      btn.addEventListener("click", () => vmAction(btn.dataset.act, vm, btn));
    });
    grid.appendChild(card);
  }
}

async function vmAction(action, vm, btn) {
  const base = `/api/vms/${encodeURIComponent(vm.name)}`;
  try {
    if (action === "start") {
      btn.disabled = true;
      await api(`${base}/start`, { method: "POST" });
      toast(t("web.toast.started", { name: vm.name }), "ok");
    } else if (action === "stop") {
      btn.disabled = true;
      await api(`${base}/stop`, { method: "POST" });
      toast(t("web.toast.stopped", { name: vm.name }), "ok");
    } else if (action === "force") {
      if (!confirm(t("dialog.confirm_force_stop", { name: vm.name }))) return;
      await api(`${base}/stop?force=true`, { method: "POST" });
      toast(t("web.toast.stopped", { name: vm.name }), "ok");
    } else if (action === "delete") {
      if (!confirm(t("dialog.confirm_delete", { name: vm.name }))) return;
      await api(base, { method: "DELETE" });
      toast(t("web.toast.deleted", { name: vm.name }), "ok");
    } else if (action === "console") {
      const info = await api(base + "/console");
      if (!info.available) {
        toast(t("web.console.unavailable"), "err");
        return;
      }
      openConsoleModal(vm.name, info);
      return;
    }
    await refreshVms();
  } catch (e) {
    toast(String(e.message || e), "err");
    await refreshVms().catch(() => {});
  }
}

async function refreshVms() {
  state.vms = await api("/api/vms");
  renderVms();
}

// ---------------------------------------------------------------- doctor
async function renderDoctor() {
  const d = await api("/api/doctor");
  const bar = document.getElementById("doctorBar");
  const checks = [
    { key: "doctor.kvm", ok: d.kvm_ok },
    { key: "doctor.udmabuf", ok: d.udmabuf_ok },
    { key: "doctor.vulkan", ok: d.vulkan_ok },
    { key: "doctor.qemu", ok: d.qemu_ok },
  ];
  bar.innerHTML =
    checks
      .map(
        (c) =>
          `<span class="doctor-item ${c.ok ? "ok" : "fail"}">${c.ok ? "✓" : "✗"} ${t(c.key)}</span>`
      )
      .join("") +
    (d.all_ok
      ? `<span class="doctor-summary ok">${t("doctor.all_good")}</span>`
      : `<span class="doctor-summary fail">${t("doctor.needs_attention")}</span>`);
}

// ---------------------------------------------------------------- charts
function drawChart(canvasId, values, color) {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = "#2B303B";
  ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
  if (!values.length) return;
  const max = Math.max(100, ...values);
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = (i / Math.max(values.length - 1, 1)) * (w - 10) + 5;
    const y = h - 5 - (v / max) * (h - 10);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();
}

function renderStats(sample) {
  state.statsHistory.cpu.push(sample.cpu_percent);
  state.statsHistory.ram.push(sample.ram_percent);
  for (const key of ["cpu", "ram"]) {
    if (state.statsHistory[key].length > 60) state.statsHistory[key].shift();
  }
  document.getElementById("hostCpu").textContent = `${sample.cpu_percent.toFixed(0)}%`;
  document.getElementById("hostRam").textContent = `${sample.ram_percent.toFixed(0)}%`;
  document.getElementById("cpuNow").textContent = `${sample.cpu_percent.toFixed(0)}%`;
  document.getElementById("ramNow").textContent = `${sample.ram_percent.toFixed(0)}%`;
  drawChart("cpuChart", state.statsHistory.cpu, "#3B82F6");
  drawChart("ramChart", state.statsHistory.ram, "#22C55E");
}

function connectStats() {
  if (state.ws) { try { state.ws.close(); } catch (e) {} }
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const tokenParam = state.token ? `?token=${encodeURIComponent(state.token)}` : "";
  const ws = new WebSocket(`${proto}://${location.host}/api/ws/stats${tokenParam}`);
  state.ws = ws;
  ws.onmessage = (ev) => {
    try { renderStats(JSON.parse(ev.data)); } catch (e) {}
  };
  ws.onclose = () => setTimeout(connectStats, 5000); // reconnect
}

// ---------------------------------------------------------------- wizard
async function openWizard() {
  document.getElementById("wizardModal").classList.remove("hidden");
  const gpus = await api("/api/gpus");
  const select = document.getElementById("wzGpu");
  select.innerHTML = `<option value="">${t("wizard.gpu.auto")}</option>` +
    gpus.map((g) => `<option value="${g.name}">${g.name}</option>`).join("");
}

document.getElementById("newVmBtn").addEventListener("click", openWizard);
document.getElementById("wzCancel").addEventListener("click", () => {
  document.getElementById("wizardModal").classList.add("hidden");
});

document.getElementById("wizardForm").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const body = {
    name: document.getElementById("wzName").value,
    macos_release: document.getElementById("wzRelease").value,
    cpus: Number(document.getElementById("wzCpus").value),
    memory_mib: Number(document.getElementById("wzMemory").value),
    disk_size_gb: Number(document.getElementById("wzDisk").value),
    gpu_name: document.getElementById("wzGpu").value || null,
  };
  try {
    const { task_id } = await api("/api/vms", { method: "POST", body: JSON.stringify(body) });
    document.getElementById("wizardModal").classList.add("hidden");
    openTaskModal(task_id);
  } catch (e) {
    toast(String(e.message || e), "err");
  }
});

// ---------------------------------------------------------------- task progress
function openTaskModal(taskId) {
  const modal = document.getElementById("taskModal");
  const fill = document.getElementById("taskProgress");
  const msg = document.getElementById("taskMessage");
  const log = document.getElementById("taskLog");
  modal.classList.remove("hidden");
  fill.style.width = "0%";
  msg.textContent = "";
  log.textContent = "";
  if (state.taskPoll) clearInterval(state.taskPoll);
  state.taskPoll = setInterval(async () => {
    try {
      const task = await api(`/api/tasks/${encodeURIComponent(taskId)}`);
      fill.style.width = `${task.progress}%`;
      msg.textContent = task.message;
      log.textContent = task.log.join("\n");
      log.scrollTop = log.scrollHeight;
      if (task.done) {
        clearInterval(state.taskPoll);
        state.taskPoll = null;
        toast(
          task.ok ? t("wizard.creation.step_done") : t("wizard.creation.step_error", { err: "" }),
          task.ok ? "ok" : "err"
        );
        await refreshVms().catch(() => {});
        setTimeout(() => modal.classList.add("hidden"), 1200);
      }
    } catch (e) {
      clearInterval(state.taskPoll);
      state.taskPoll = null;
      modal.classList.add("hidden");
      toast(String(e.message || e), "err");
    }
  }, 1000);
}

document.getElementById("taskClose").addEventListener("click", () => {
  document.getElementById("taskModal").classList.add("hidden");
});

// ---------------------------------------------------------------- live console
const consoleState = {
  inputUrl: null,
  lastMove: 0,
};

function openConsoleModal(vmName, info) {
  const modal = document.getElementById("consoleModal");
  const img = document.getElementById("consoleScreen");
  document.getElementById("consoleVmName").textContent = vmName;
  document.getElementById("consoleRes").textContent =
    info.width && info.height ? `${info.width}×${info.height}` : "";
  consoleState.inputUrl = info.input_url;
  const sep = info.stream_url.includes("?") ? "&" : "?";
  const tokenQ = state.token ? `${sep}token=${encodeURIComponent(state.token)}` : "";
  img.src = `${info.stream_url}${tokenQ}`;
  modal.classList.remove("hidden");
  img.focus();
}

function closeConsoleModal() {
  const modal = document.getElementById("consoleModal");
  const img = document.getElementById("consoleScreen");
  img.src = "";
  consoleState.inputUrl = null;
  modal.classList.add("hidden");
}

function sendConsoleInput(payload) {
  if (!consoleState.inputUrl) return;
  fetch(consoleState.inputUrl, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  }).catch(() => {});
}

function normalizedCoords(ev, img) {
  const rect = img.getBoundingClientRect();
  if (!rect.width || !rect.height) return { x: 0.5, y: 0.5 };
  const x = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
  const y = Math.max(0, Math.min(1, (ev.clientY - rect.top) / rect.height));
  return { x, y };
}

(() => {
  const img = document.getElementById("consoleScreen");
  img.addEventListener("contextmenu", (ev) => ev.preventDefault());
  img.addEventListener("mousedown", (ev) => {
    ev.preventDefault();
    img.focus();
    const { x, y } = normalizedCoords(ev, img);
    const btn = ev.button === 2 ? 3 : ev.button === 1 ? 2 : 1;
    sendConsoleInput({ type: "mousedown", x, y, button: btn });
  });
  img.addEventListener("mouseup", (ev) => {
    ev.preventDefault();
    const { x, y } = normalizedCoords(ev, img);
    const btn = ev.button === 2 ? 3 : ev.button === 1 ? 2 : 1;
    sendConsoleInput({ type: "mouseup", x, y, button: btn });
  });
  img.addEventListener("mousemove", (ev) => {
    const now = performance.now();
    if (now - consoleState.lastMove < 50) return;
    consoleState.lastMove = now;
    const { x, y } = normalizedCoords(ev, img);
    sendConsoleInput({ type: "mousemove", x, y });
  });
  img.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    const { x, y } = normalizedCoords(ev, img);
    sendConsoleInput({ type: "wheel", x, y, deltaY: ev.deltaY });
  }, { passive: false });
  img.addEventListener("keydown", (ev) => {
    ev.preventDefault();
    sendConsoleInput({ type: "keydown", key: ev.key });
  });
  img.addEventListener("keyup", (ev) => {
    ev.preventDefault();
    sendConsoleInput({ type: "keyup", key: ev.key });
  });
})();

document.getElementById("consoleTextForm").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const input = document.getElementById("consoleTextInput");
  const text = input.value;
  if (!text) return;
  sendConsoleInput({ type: "text", text });
  input.value = "";
  document.getElementById("consoleScreen").focus();
});

document.getElementById("consoleFullscreen").addEventListener("click", () => {
  const stage = document.getElementById("consoleStage");
  if (document.fullscreenElement) {
    document.exitFullscreen().catch(() => {});
  } else {
    stage.requestFullscreen().catch(() => {});
  }
});

document.getElementById("consoleClose").addEventListener("click", closeConsoleModal);

// ---------------------------------------------------------------- language
document.getElementById("langSelect").value = state.lang;
document.getElementById("langSelect").addEventListener("change", async (ev) => {
  await loadI18n(ev.target.value);
  renderVms();
});

// ---------------------------------------------------------------- boot
(async function boot() {
  await loadI18n(state.lang);
  if (!(await tryStart())) return;
  await startPolling();
})();

async function startPolling() {
  await refreshVms().catch((e) => toast(String(e.message || e), "err"));
  await renderDoctor().catch(() => {});
  connectStats();
  setInterval(() => refreshVms().catch(() => {}), 5000);
  setInterval(() => renderDoctor().catch(() => {}), 30000);
}
