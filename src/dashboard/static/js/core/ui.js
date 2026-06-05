import { state } from "./state.js";
import { clearIotLoading, clearKpiLoading, clearStatLoading } from "./dom.js";

export function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const icons = {
    success: "bi-check-circle-fill",
    error: "bi-exclamation-circle-fill",
    info: "bi-info-circle-fill",
  };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.setAttribute("role", "status");
  toast.innerHTML = `<i class="bi ${icons[type] || icons.info}" aria-hidden="true"></i><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

export function setDataSourceChip(source) {
  if (source === "live") state.lastDataSource = "live";
  else if (source === "demo") state.lastDataSource = state.lastDataSource === "live" ? "live" : "demo";
  else if (source === "unavailable") state.lastDataSource = "offline";
  else if (source === "pending") state.lastDataSource = "pending";

  const chip = document.getElementById("data-source-chip");
  if (!chip) return;

  const labels = {
    pending: ["Carregando…", "demo"],
    demo: ["Demonstração", "demo"],
    live: ["Dados reais", "live"],
    offline: ["Offline", "offline"],
  };
  const mode =
    state.lastDataSource === "offline" ? "offline" :
    state.lastDataSource === "demo" ? "demo" :
    state.lastDataSource === "live" ? "live" : "pending";
  const [text, cls] = labels[mode];
  chip.textContent = text;
  chip.className = `data-source-chip ${cls}`;

  const footerHint = document.getElementById("footer-storage-hint");
  if (footerHint) {
    footerHint.textContent =
      mode === "live" ? "dados via AWS DynamoDB" :
      mode === "demo" ? "dados de demonstração (JSON local)" :
      "sem conexão com o servidor";
  }
}

export function noteResponseSource(response) {
  const src = response.headers.get("X-Data-Source");
  if (src) setDataSourceChip(src);
}

export function setLastUpdated(date) {
  const el = document.getElementById("data-source-updated");
  if (!el) return;
  const ts =
    date instanceof Date && !isNaN(date)
      ? date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
      : new Date().toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  el.textContent = `Atualizado: ${ts}`;
}

export function finalizeDashboardLoad() {
  clearKpiLoading();
  clearStatLoading();
  clearIotLoading();
  if (state.lastDataSource !== "pending") return;
  if (state.dashboardConfig.storage === "dynamodb") setDataSourceChip("live");
  else if (state.dashboardConfig.demo_mode) setDataSourceChip("demo");
  else setDataSourceChip("offline");
}

import { showChartError } from "./dom.js";

const CHART_ERROR_MSG = "Dados indisponíveis";

export async function safeLoad(name, fn) {
  try {
    await fn();
  } catch (err) {
    console.warn(`Dashboard: falha em ${name}`, err);
    if (name === "trend") showChartError("trendChart", CHART_ERROR_MSG);
    if (name === "weekly") showChartError("weeklyChart", CHART_ERROR_MSG);
    if (name === "hourly") showChartError("hourlyChart", CHART_ERROR_MSG);
  }
}
