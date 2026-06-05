/**
 * Entry point do dashboard — Global Solutions FIAP 2026.
 * Módulos em js/{core,maps,sections}/.
 */
import { initTheme, initChartDefaults } from "./theme.js";
import {
  loadStoredLocation,
  ensureLocationPickerMap,
  initLocationBarUX,
  bindLocationControls,
} from "./maps/location.js";
import { lazyLoadWindy } from "./maps/windy.js";
import { lazyInitRegionMap } from "./maps/region.js";
import { bootstrapDashboard } from "./bootstrap.js";
import { bindMLSliders } from "./sections/ml.js";
import { bindYoloActions } from "./sections/yolo.js";

async function initDashboard() {
  initTheme();
  initChartDefaults();
  loadStoredLocation();
  ensureLocationPickerMap();
  initLocationBarUX();
  bindLocationControls();
  bindMLSliders();
  bindYoloActions();
  await bootstrapDashboard();
  lazyLoadWindy();
  lazyInitRegionMap();
}

initDashboard();
