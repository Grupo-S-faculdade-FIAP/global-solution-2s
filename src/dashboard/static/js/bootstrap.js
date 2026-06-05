import { state } from "./core/state.js";
import { safeLoad, finalizeDashboardLoad, setLastUpdated } from "./core/ui.js";
import { loadDashboardConfig } from "./sections/config.js";
import { loadKPIs, loadTrend, loadWeekly, loadHourly, loadHeatmap } from "./sections/alerts.js";
import { loadWeatherData, loadRiskData } from "./sections/climate.js";
import { loadIoTReadings } from "./sections/iot.js";
import { loadYOLOStatus, loadRecentStorms } from "./sections/yolo.js";
import { loadNASAGallery } from "./sections/nasa.js";
import { loadRegionMap } from "./maps/region.js";

export async function bootstrapDashboard() {
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
