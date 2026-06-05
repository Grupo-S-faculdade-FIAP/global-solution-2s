import { state } from "../core/state.js";
import { risk } from "../core/api/endpoints.js";

function setLabel(id, text, loading = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.classList.toggle("is-loading", loading);
}

export function syncWeatherToML(data) {
  const temp = data.temperature ?? null;
  const umid = data.humidity ?? null;
  const prec = data.precipitation ?? null;
  const ventoKmh =
    data.wind_speed != null ? Math.round(data.wind_speed * 3.6) : null;

  if (temp != null) setLabel("lbl-temp", `${temp}°C`);
  if (umid != null) setLabel("lbl-umid", `${Math.round(umid)}%`);
  if (prec != null) setLabel("lbl-prec", `${prec} mm/h`);
  if (ventoKmh != null) setLabel("lbl-vento", `${ventoKmh} km/h`);

  updateEnsembleRisk();
}

function setMLText(id, text, className) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  if (className != null) el.className = className;
}

function renderBreakdown(detalhes) {
  const el = document.getElementById("ml-breakdown");
  if (!el || !detalhes) return;

  const comp = detalhes.components || {};
  const pesos = detalhes.pesos || {};
  const pct = (v) => `${Math.round((v || 0) * 100)}%`;

  el.innerHTML =
    `<div class="ml-breakdown-row"><span>Clima</span><span>${pct(comp.clima)} <small>(${Math.round((pesos.clima || 0) * 100)}% peso)</small></span></div>` +
    `<div class="ml-breakdown-row"><span>Satélite (YOLO)</span><span>${pct(comp.cv)} <small>(${Math.round((pesos.cv || 0) * 100)}% peso)</small></span></div>` +
    `<div class="ml-breakdown-row"><span>ML agrícola</span><span>${pct(comp.ml_agricola)} <small>(${Math.round((pesos.ml_agricola || 0) * 100)}% peso)</small></span></div>`;
}

function syncRiskBadge(score, category, recommendation) {
  const riskClasses = { LOW: "risk-low", MEDIUM: "risk-moderate", HIGH: "risk-high" };
  const traduz = { LOW: "BAIXO", MEDIUM: "MÉDIO", HIGH: "ALTO" };
  const colorSet = { cls: riskClasses[category] || "risk-low", text: traduz[category] || category };

  const badge = document.getElementById("risk-badge");
  const catEl = document.getElementById("risk-category");
  const recEl = document.getElementById("risk-recommendation");

  if (badge) {
    badge.textContent = `${Math.round(score * 100)}%`;
    badge.className = "risk-score " + colorSet.cls;
    badge.classList.remove("is-loading");
  }
  if (catEl) {
    catEl.textContent = `Risco ${colorSet.text}`;
    catEl.className = "risk-category " + colorSet.cls;
  }
  if (recEl) recEl.textContent = recommendation || "—";
}

export async function updateEnsembleRisk() {
  if (!document.getElementById("ml-score")) return;

  clearTimeout(state.mlDebounce);
  state.mlDebounce = setTimeout(async () => {
    try {
      const r = await risk.forecast(state.userLocation.lat, state.userLocation.lon);
      if (!r.ok) throw new Error();
      const d = await r.json();

      const riskClasses = { LOW: "risk-low", MEDIUM: "risk-moderate", HIGH: "risk-high" };
      const traduz = { LOW: "BAIXO", MEDIUM: "MÉDIO", HIGH: "ALTO" };
      const cls = riskClasses[d.risk_category] || "";

      setMLText("ml-score", `${Math.round(d.risk_score * 100)}%`, cls);
      setMLText("ml-classe", `Risco ${traduz[d.risk_category] || d.risk_category}`, cls);
      setMLText("ml-rec", d.recommendation || "—");

      syncRiskBadge(d.risk_score, d.risk_category, d.recommendation);
      renderBreakdown(d.detalhes);

      const chip = document.getElementById("ml-source-chip");
      const setupHint = document.getElementById("ml-setup-hint");
      if (chip) {
        const mlSrc = d.detalhes?.ml_agricola?.score != null ? "ensemble" : "";
        const ds = d.detalhes?.ml_agricola?.dataset_source || "";
        const label = ds.includes("inmet")
          ? "Ensemble · INMET BDMEP"
          : ds.includes("openmeteo")
            ? "Ensemble · Open-Meteo"
            : mlSrc
              ? "Ensemble (clima + satélite + ML)"
              : "Ensemble";
        chip.textContent = label;
        chip.hidden = false;
        if (setupHint) setupHint.hidden = true;
      }

      const probasEl = document.getElementById("ml-probas");
      const comp = d.detalhes?.components || {};
      if (probasEl) {
        const pct = (v) => Math.round((v || 0) * 100);
        probasEl.innerHTML =
          `<span class="risk-low">Clima</span> ${pct(comp.clima)}%<br>` +
          `<span class="risk-moderate">Satélite</span> ${pct(comp.cv)}%<br>` +
          `<span class="risk-high">ML</span> ${pct(comp.ml_agricola)}%`;
      }
    } catch {
      setMLText("ml-score", "—");
      setMLText("ml-rec", "Backend indisponível");
    }
  }, 400);
}

/** @deprecated use updateEnsembleRisk — mantido para compatibilidade interna */
export async function updateMLPredictor() {
  return updateEnsembleRisk();
}
