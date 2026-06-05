import { state } from "./core/state.js";
import { safeLoad, finalizeDashboardLoad, setLastUpdated } from "./core/ui.js";
import { loadDashboardConfig } from "./sections/config.js";
import { loadKPIs, loadTrend, loadWeekly, loadHourly, loadHeatmap } from "./sections/alerts.js";
import { loadWeatherData, loadRiskData } from "./sections/climate.js";
import { loadIoTReadings } from "./sections/iot.js";
import { loadYOLOStatus, loadRecentStorms } from "./sections/yolo.js";
import { loadNASAGallery } from "./sections/nasa.js";
import { loadRegionMap } from "./maps/region.js";

/** Aquece a Lambda antes do burst de /api/* (cold start pode levar 60–90 s). */
async function warmBackend() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120_000);
  try {
    await fetch("/health", { cache: "no-store", signal: controller.signal });
  } catch {
    /* segue — loaders individuais tratam falha */
  } finally {
    clearTimeout(timer);
  }
}

export async function bootstrapDashboard() {
  await warmBackend();
  await Promise.allSettled([
    loadDashboardConfig(),
    safeLoad("kpis", loadKPIs),
    safeLoad("trend", loadTrend),
    safeLoad("weekly", loadWeekly),
    safeLoad("hourly", loadHourly),
    safeLoad("heatmap", loadHeatmap),
    safeLoad("weather", loadWeatherData),
    safeLoad("risk", loadRiskData),
    safeLoad("iot", loadIoTReadings),
    safeLoad("yolo", loadYOLOStatus),
    safeLoad("storms", loadRecentStorms),
    safeLoad("nasa", loadNASAGallery),
    safeLoad("region-map", loadRegionMap),
  ]);
  finalizeDashboardLoad();
  setLastUpdated(new Date());
  state.hasAppliedLocationOnce = true;
}
