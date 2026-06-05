/** Estado mutável compartilhado do dashboard (runtime handles + dados). */

import { DEFAULT_LOC } from "./constants.js";

export const state = {
  dashboardConfig: { demo_mode: true, default_lat: DEFAULT_LOC.lat, default_lon: DEFAULT_LOC.lon },
  userLocation: { ...DEFAULT_LOC },
  lastDataSource: "pending",
  locationReloading: false,
  hasAppliedLocationOnce: false,
  mapApplyTimer: null,
  locationPickerMap: null,
  locationPickerMarker: null,
  locationPickerRadius: null,
  regionMap: null,
  regionAlertsLayer: null,
  regionTileLayer: null,
  trendChartInstance: null,
  weeklyChartInstance: null,
  hourlyChartInstance: null,
  lastTrendData: null,
  lastWeeklyData: null,
  lastHourlyData: null,
  lastHeatmapData: null,
  lastHeatmapMax: 1,
  mlDebounce: null,
};
