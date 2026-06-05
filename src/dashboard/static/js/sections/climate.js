import { state } from "../core/state.js";
import { fetchApi } from "../core/api.js";
import {
  ensureWeatherLayout,
  ensureRiskLayout,
  clearSectionError,
  showSectionError,
  clearStatLoading,
} from "../core/dom.js";
import {
  noteResponseSource,
  setDataSourceChip,
  setLastUpdated,
} from "../core/ui.js";
import { loadRegionMap } from "../maps/region.js";
import { refreshWindyMap } from "../maps/windy.js";
import { updateMLPredictor } from "./ml.js";

function syncSlidersFromWeather(data) {
  const slTemp = document.getElementById("sl-temp");
  const slUmid = document.getElementById("sl-umid");
  const slPrec = document.getElementById("sl-prec");
  const slVento = document.getElementById("sl-vento");
  if (data.temperature != null && slTemp) slTemp.value = Math.min(45, Math.max(5, data.temperature));
  if (data.humidity != null && slUmid) slUmid.value = Math.round(data.humidity);
  if (data.precipitation != null && slPrec) slPrec.value = Math.min(50, Math.max(0, data.precipitation));
  if (data.wind_speed != null && slVento) {
    slVento.value = Math.round(Math.min(120, Math.max(0, data.wind_speed * 3.6)));
  }
  updateMLPredictor();
}

export async function loadWeatherData() {
  ensureWeatherLayout();
  clearSectionError("weather-container");
  try {
    const q = `lat=${state.userLocation.lat}&lon=${state.userLocation.lon}`;
    const r = await fetchApi(`/api/weather/current?${q}`);
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();

    document.getElementById("weather-temp").textContent = `${data.temperature}°C`;
    document.getElementById("weather-humidity").textContent = `${data.humidity}%`;
    document.getElementById("weather-pressure").textContent = `${data.pressure} hPa`;
    document.getElementById("weather-wind").textContent = `${data.wind_speed} m/s`;
    clearStatLoading();

    const ts = new Date(data.timestamp);
    document.getElementById("weather-timestamp").textContent =
      `Clima: ${ts.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}`;
    setLastUpdated(ts);
    setDataSourceChip("live");
    syncSlidersFromWeather(data);
  } catch {
    clearStatLoading();
    showSectionError("weather-container", "Clima indisponível — verifique se a API está rodando");
    setDataSourceChip("unavailable");
  }
}

export async function loadRiskData() {
  ensureRiskLayout();
  clearSectionError("risk-container");
  try {
    const q = `lat=${state.userLocation.lat}&lon=${state.userLocation.lon}`;
    const r = await fetchApi(`/api/risk/forecast?${q}`);
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();

    const categoryClasses = {
      LOW: { cls: "risk-low", text: "BAIXO" },
      MEDIUM: { cls: "risk-moderate", text: "MÉDIO" },
      HIGH: { cls: "risk-high", text: "ALTO" },
    };

    const colorSet = categoryClasses[data.risk_category] || categoryClasses.LOW;
    const badge = document.getElementById("risk-badge");
    const category = document.getElementById("risk-category");

    badge.textContent = `${(data.risk_score * 100).toFixed(0)}%`;
    badge.className = "risk-score " + colorSet.cls;
    badge.classList.remove("is-loading");

    category.textContent = `Risco ${colorSet.text}`;
    category.className = "risk-category " + colorSet.cls;

    document.getElementById("risk-recommendation").textContent = data.recommendation;
  } catch {
    clearStatLoading();
    const badge = document.getElementById("risk-badge");
    if (badge) {
      badge.classList.remove("is-loading");
      badge.textContent = "—";
    }
    showSectionError("risk-container", "Risco indisponível no momento");
  }
}

export async function reloadLocationDependentData() {
  ensureWeatherLayout();
  ensureRiskLayout();
  clearSectionError("weather-container");
  clearSectionError("risk-container");
  const badge = document.getElementById("risk-badge");
  if (badge) {
    badge.classList.add("is-loading");
    badge.textContent = "—";
  }
  await Promise.all([loadWeatherData(), loadRiskData(), loadRegionMap()]);
  refreshWindyMap();
}
