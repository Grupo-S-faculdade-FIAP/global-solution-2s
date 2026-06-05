/**
 * Entry point do dashboard — Global Solutions FIAP 2026.
 * Módulos em js/{core,maps,sections}/.
 */
import { on } from "./core/events.js";
import { initOrchestrator } from "./core/orchestrator.js";
import { initTheme, initChartDefaults } from "./theme.js";
import {
  loadStoredLocation,
  ensureLocationPickerMap,
  initLocationBarUX,
  bindLocationControls,
} from "./maps/location.js";
import { lazyLoadWindy } from "./maps/windy.js";
import { lazyInitRegionMap, refreshRegionMapTiles, refreshLocationPickerTiles } from "./maps/region.js";
import { refreshWindyMap } from "./maps/windy.js";
import { bootstrapDashboard } from "./bootstrap.js";
import { finalizeDashboardLoad, setDataSourceChip } from "./core/ui.js";
import { bindYoloActions } from "./sections/yolo.js";
import { updateChartDefaults, refreshAllCharts, refreshHeatmapColors } from "./charts.js";

function initThemeSubscribers() {
  on("theme:changed", () => {
    requestAnimationFrame(() => {
      updateChartDefaults();
      refreshAllCharts();
      refreshHeatmapColors();
      refreshRegionMapTiles();
      refreshLocationPickerTiles();
      refreshWindyMap();
    });
  });
}

async function initDashboard() {
  try {
    initOrchestrator();
    initThemeSubscribers();
    initTheme();
    initChartDefaults();
    loadStoredLocation();
    ensureLocationPickerMap();
    initLocationBarUX();
    bindLocationControls();
    bindYoloActions();
    await bootstrapDashboard();
  } catch (err) {
    console.error("Dashboard: falha ao inicializar", err);
    finalizeDashboardLoad();
    setDataSourceChip("offline");
  } finally {
    lazyLoadWindy();
    lazyInitRegionMap();
  }
}

initDashboard();
