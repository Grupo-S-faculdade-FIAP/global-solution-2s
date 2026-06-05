import { on } from "./events.js";
import { $, clearSectionError } from "./dom.js";
import { SEL } from "./selectors.js";
import { loadWeatherData, loadRiskData } from "../sections/climate.js";
import { loadAlertsBundle } from "../sections/alerts.js";
import { syncWeatherToML } from "../sections/ml.js";
import { loadRegionMap } from "../maps/region.js";
import { refreshWindyMap } from "../maps/windy.js";

async function reloadLocationDependentData() {
  clearSectionError(SEL.weatherContainer);
  clearSectionError(SEL.riskContainer);
  const badge = $(SEL.riskBadge);
  if (badge) {
    badge.classList.add("is-loading");
    badge.textContent = "—";
  }
  await Promise.all([loadWeatherData(), loadRiskData(), loadRegionMap()]);
  refreshWindyMap();
}

async function reloadAfterStormSimulate() {
  await Promise.all([loadAlertsBundle(), loadRegionMap()]);
}

export function initOrchestrator() {
  on("location:changed", reloadLocationDependentData);
  on("weather:loaded", (data) => syncWeatherToML(data));
  on("dashboard:reload", async (detail) => {
    if (detail?.scope === "post-storm-simulate") {
      await reloadAfterStormSimulate();
    }
  });
}
