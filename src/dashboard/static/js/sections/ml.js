import { state } from "../core/state.js";
import { ml } from "../core/api/endpoints.js";

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

  if (temp == null || umid == null || prec == null || ventoKmh == null) return;

  updateMLPredictor({ temperatura: temp, umidade: umid, precipitacao: prec, vento_kmh: ventoKmh });
}

function setMLText(id, text, className) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  if (className != null) el.className = className;
}

export async function updateMLPredictor(inputs) {
  if (!document.getElementById("ml-score")) return;

  clearTimeout(state.mlDebounce);
  state.mlDebounce = setTimeout(async () => {
    try {
      const r = await ml.agriculturalRisk(inputs);
      if (!r.ok) throw new Error();
      const d = await r.json();

      const riskClasses = { LOW: "risk-low", MEDIUM: "risk-moderate", HIGH: "risk-high" };
      const traduz = { LOW: "BAIXO", MEDIUM: "MÉDIO", HIGH: "ALTO" };
      const cls = riskClasses[d.classe] || "";

      setMLText("ml-score", `${Math.round(d.score * 100)}%`, cls);
      setMLText("ml-classe", `Risco ${traduz[d.classe] || d.classe}`, cls);
      setMLText("ml-rec", d.recomendacao || "—");

      const chip = document.getElementById("ml-source-chip");
      const setupHint = document.getElementById("ml-setup-hint");
      if (chip) {
        const src = d.dataset_source || "";
        const label = src.includes("inmet")
          ? "INMET BDMEP"
          : src.includes("openmeteo")
            ? "Open-Meteo"
            : src.includes("synthetic")
              ? "Sintético"
              : src || "—";
        chip.textContent = `Modelo: ${label}`;
        chip.hidden = !src;
        const needsSetup = src.includes("synthetic") || src.includes("openmeteo") || !src;
        if (setupHint) setupHint.hidden = !needsSetup;
      }

      const probasEl = document.getElementById("ml-probas");
      const p = d.probabilidades || {};
      if (probasEl) {
        probasEl.innerHTML =
          `<span class="risk-low">Baixo</span> ${Math.round((p.LOW || 0) * 100)}%<br>` +
          `<span class="risk-moderate">Médio</span> ${Math.round((p.MEDIUM || 0) * 100)}%<br>` +
          `<span class="risk-high">Alto</span> ${Math.round((p.HIGH || 0) * 100)}%`;
      }
    } catch {
      setMLText("ml-score", "—");
      setMLText("ml-rec", "Backend indisponível");
    }
  }, 400);
}
