/** Helpers de DOM — markup estrutural vive nos partials Jinja. */

import { SEL } from "./selectors.js";

export const $ = (id) => document.getElementById(id);

const KPI_IDS = [SEL.kpiTotal, SEL.kpiAvg, SEL.kpiDay, SEL.kpiHour];
const STAT_IDS = [SEL.weatherTemp, SEL.weatherHumidity, SEL.weatherPressure, SEL.weatherWind, SEL.riskBadge];
const IOT_IDS = ["iot-temp", "iot-umid", "iot-cidade", "iot-ts"];

export function clearKpiLoading() {
  KPI_IDS.forEach((id) => $(id)?.classList.remove("is-loading"));
}

export function clearStatLoading() {
  STAT_IDS.forEach((id) => $(id)?.classList.remove("is-loading"));
}

export function clearIotLoading() {
  IOT_IDS.forEach((id) => $(id)?.classList.remove("is-loading"));
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
