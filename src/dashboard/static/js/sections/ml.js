import { state } from "../core/state.js";
import { ml } from "../core/api/endpoints.js";

export function syncSlidersFromWeather(data) {
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

export async function updateMLPredictor() {
  const temp = parseFloat(document.getElementById("sl-temp").value);
  const umid = parseFloat(document.getElementById("sl-umid").value);
  const prec = parseFloat(document.getElementById("sl-prec").value);
  const vento = parseFloat(document.getElementById("sl-vento").value);

  document.getElementById("lbl-temp").textContent = `${temp}°C`;
  document.getElementById("lbl-umid").textContent = `${umid}%`;
  document.getElementById("lbl-prec").textContent = `${prec} mm/h`;
  document.getElementById("lbl-vento").textContent = `${vento} km/h`;

  clearTimeout(state.mlDebounce);
  state.mlDebounce = setTimeout(async () => {
    try {
      const r = await ml.agriculturalRisk({
        temperatura: temp,
        umidade: umid,
        precipitacao: prec,
        vento_kmh: vento,
      });
      if (!r.ok) throw new Error();
      const d = await r.json();

      const riskClasses = { LOW: "risk-low", MEDIUM: "risk-moderate", HIGH: "risk-high" };
      const traduz = { LOW: "BAIXO", MEDIUM: "MÉDIO", HIGH: "ALTO" };
      const cls = riskClasses[d.classe] || "";

      document.getElementById("ml-score").textContent = `${Math.round(d.score * 100)}%`;
      document.getElementById("ml-score").className = cls;
      document.getElementById("ml-classe").textContent = `Risco ${traduz[d.classe] || d.classe}`;
      document.getElementById("ml-classe").className = cls;
      document.getElementById("ml-rec").textContent = d.recomendacao || "—";

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

      const p = d.probabilidades || {};
      document.getElementById("ml-probas").innerHTML =
        `<span class="risk-low">Baixo</span> ${Math.round((p.LOW || 0) * 100)}%<br>` +
        `<span class="risk-moderate">Médio</span> ${Math.round((p.MEDIUM || 0) * 100)}%<br>` +
        `<span class="risk-high">Alto</span> ${Math.round((p.HIGH || 0) * 100)}%`;
    } catch {
      document.getElementById("ml-score").textContent = "—";
      document.getElementById("ml-rec").textContent = "Backend indisponível";
    }
  }, 400);
}

export function bindMLSliders() {
  ["sl-temp", "sl-umid", "sl-prec", "sl-vento"].forEach((id) => {
    document.getElementById(id)?.addEventListener("input", updateMLPredictor);
  });
}
