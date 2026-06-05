/** Helpers de DOM e layouts injetáveis. */

export const $ = (id) => document.getElementById(id);

export const WEATHER_GRID_HTML = `
  <div><span class="stat-label">Temperatura</span><br><span class="stat-value is-loading" id="weather-temp">—</span></div>
  <div><span class="stat-label">Umidade</span><br><span class="stat-value is-loading" id="weather-humidity">—</span></div>
  <div><span class="stat-label">Pressão</span><br><span class="stat-value is-loading" id="weather-pressure">—</span></div>
  <div><span class="stat-label">Vento</span><br><span class="stat-value is-loading" id="weather-wind">—</span></div>`;

export const RISK_PANEL_HTML = `
  <div class="risk-score-wrap">
    <div class="risk-score is-loading" id="risk-badge" aria-busy="true">—</div>
    <div class="risk-category" id="risk-category">—</div>
  </div>
  <div class="risk-recommendation" id="risk-recommendation">—</div>`;

export function ensureWeatherLayout() {
  const el = $("weather-container");
  if (!el || $("weather-temp")) return;
  el.innerHTML = WEATHER_GRID_HTML;
}

export function ensureRiskLayout() {
  const el = $("risk-container");
  if (!el || $("risk-badge")) return;
  el.innerHTML = RISK_PANEL_HTML;
}

export function clearKpiLoading() {
  ["kpi-total", "kpi-avg", "kpi-day", "kpi-hour"].forEach((id) => $(id)?.classList.remove("is-loading"));
}

export function clearStatLoading() {
  ["weather-temp", "weather-humidity", "weather-pressure", "weather-wind", "risk-badge"].forEach((id) =>
    $(id)?.classList.remove("is-loading")
  );
}

export function clearIotLoading() {
  ["iot-temp", "iot-umid", "iot-cidade", "iot-ts"].forEach((id) => $(id)?.classList.remove("is-loading"));
}

export function clearSectionError(containerId) {
  const el = $(containerId);
  if (!el) return;
  el.classList.remove("has-error");
  el.querySelector(":scope > .section-error")?.remove();
}

export function showSectionError(containerId, message) {
  const el = $(containerId);
  if (!el) return;
  if (containerId === "weather-container") ensureWeatherLayout();
  if (containerId === "risk-container") ensureRiskLayout();
  el.classList.add("has-error");
  let err = el.querySelector(":scope > .section-error");
  if (!err) {
    err = document.createElement("div");
    err.className = "section-error";
    el.prepend(err);
  }
  err.innerHTML = `<i class="bi bi-exclamation-circle"></i>${message}`;
}

export function showChartError(canvasId, message) {
  const canvas = $(canvasId);
  if (!canvas) return;
  canvas.style.display = "none";
  let err = canvas.parentElement?.querySelector(".chart-error-msg");
  if (!err) {
    err = document.createElement("div");
    err.className = "section-error chart-error-msg";
    canvas.insertAdjacentElement("afterend", err);
  }
  err.innerHTML = `<i class="bi bi-exclamation-circle"></i>${message}`;
}
