import { state } from "../core/state.js";
import { weather, risk } from "../core/api/endpoints.js";
import { emit } from "../core/events.js";
import { $, clearSectionError, showSectionError, clearStatLoading } from "../core/dom.js";
import { SEL } from "../core/selectors.js";
import {
  noteResponseSource,
  setDataSourceChip,
  setLastUpdated,
} from "../core/ui.js";

export async function loadWeatherData() {
  clearSectionError(SEL.weatherContainer);
  try {
    const r = await weather.current(state.userLocation.lat, state.userLocation.lon);
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();

    const tempEl = $(SEL.weatherTemp);
    const humEl = $(SEL.weatherHumidity);
    const pressEl = $(SEL.weatherPressure);
    const windEl = $(SEL.weatherWind);
    if (tempEl) tempEl.textContent = `${data.temperature}°C`;
    if (humEl) humEl.textContent = `${data.humidity}%`;
    if (pressEl) pressEl.textContent = `${data.pressure} hPa`;
    if (windEl) windEl.textContent = `${data.wind_speed} m/s`;
    clearStatLoading();

    const ts = new Date(data.timestamp);
    const tsEl = $(SEL.weatherTimestamp);
    if (tsEl) {
      tsEl.textContent = `Clima: ${ts.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}`;
    }
    setLastUpdated(ts);
    setDataSourceChip("live");
    emit("weather:loaded", data);
  } catch {
    clearStatLoading();
    showSectionError(SEL.weatherContainer, "Clima indisponível — verifique se a API está rodando");
    setDataSourceChip("unavailable");
  }
}

export async function loadRiskData() {
  clearSectionError(SEL.riskContainer);
  try {
    const r = await risk.forecast(state.userLocation.lat, state.userLocation.lon);
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();

    const categoryClasses = {
      LOW: { cls: "risk-low", text: "BAIXO" },
      MEDIUM: { cls: "risk-moderate", text: "MÉDIO" },
      HIGH: { cls: "risk-high", text: "ALTO" },
    };

    const colorSet = categoryClasses[data.risk_category] || categoryClasses.LOW;
    const badge = $(SEL.riskBadge);
    const category = $(SEL.riskCategory);

    if (badge) {
      badge.textContent = `${(data.risk_score * 100).toFixed(0)}%`;
      badge.className = "risk-score " + colorSet.cls;
      badge.classList.remove("is-loading");
    }

    if (category) {
      category.textContent = `Risco ${colorSet.text}`;
      category.className = "risk-category " + colorSet.cls;
    }

    const recEl = $(SEL.riskRecommendation);
    if (recEl) recEl.textContent = data.recommendation;
  } catch {
    clearStatLoading();
    const badge = $(SEL.riskBadge);
    if (badge) {
      badge.classList.remove("is-loading");
      badge.textContent = "—";
    }
    showSectionError(SEL.riskContainer, "Risco indisponível no momento");
  }
}
