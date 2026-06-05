// ── Theme Management ─────────────────────────────────────────────────────
const THEME_KEY = "dashboard-theme";

function resolveInitialTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "dark" || saved === "light") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function getCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function updateMetaThemeColor(theme) {
  const meta = document.getElementById("meta-theme-color");
  if (meta) meta.content = theme === "dark" ? "#0d1117" : "#ffffff";
}

function updateThemeIcon(theme) {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  const isDark = theme === "dark";
  btn.innerHTML = isDark
    ? '<i class="bi bi-sun-fill" aria-hidden="true"></i>'
    : '<i class="bi bi-moon-stars-fill" aria-hidden="true"></i>';
  btn.setAttribute("aria-pressed", String(isDark));
  btn.setAttribute("aria-label", isDark ? "Ativar modo claro" : "Ativar modo escuro");
  btn.title = isDark ? "Modo escuro — clique para claro" : "Modo claro — clique para escuro";
}

function updateThemeLabel(theme) {
  const label = document.getElementById("theme-mode-label");
  if (label) label.textContent = theme === "dark" ? "Escuro" : "Claro";
}

function applyTheme(theme) {
  if (theme !== "dark" && theme !== "light") theme = "dark";
  const html = document.documentElement;
  html.setAttribute("data-theme", theme);
  html.classList.remove("theme-dark", "theme-light");
  html.classList.add(theme === "dark" ? "theme-dark" : "theme-light");
  html.style.colorScheme = theme;
  localStorage.setItem(THEME_KEY, theme);
  updateMetaThemeColor(theme);
  updateThemeIcon(theme);
  updateThemeLabel(theme);

  requestAnimationFrame(() => {
    updateChartDefaults();
    refreshAllCharts();
    refreshHeatmapColors();
    if (typeof refreshRegionMapTiles === "function") refreshRegionMapTiles();
    if (typeof refreshLocationPickerTiles === "function") refreshLocationPickerTiles();
    if (typeof refreshWindyMap === "function") refreshWindyMap();
  });
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(current === "dark" ? "light" : "dark");
}

function initTheme() {
  applyTheme(resolveInitialTheme());
  const btn = document.getElementById("theme-toggle");
  if (btn && !btn.dataset.bound) {
    btn.dataset.bound = "1";
    btn.addEventListener("click", toggleTheme);
  }
}

// ── Chart Defaults (tema-aware) ────────────────────────────────────────────
function getThemeColors() {
  return {
    text: getCssVar("--text-sec") || "#8b949e",
    border: getCssVar("--chart-grid") || "#21262d",
    blue: getCssVar("--blue") || "#58a6ff",
    green: getCssVar("--green") || "#3fb950",
  };
}

function updateChartDefaults() {
  if (typeof Chart === "undefined") return;
  const colors = getThemeColors();
  Chart.defaults.color = colors.text;
  Chart.defaults.borderColor = colors.border;
}

const WEATHER_GRID_HTML = `
  <div><span class="stat-label">Temperatura</span><br><span class="stat-value is-loading" id="weather-temp">—</span></div>
  <div><span class="stat-label">Umidade</span><br><span class="stat-value is-loading" id="weather-humidity">—</span></div>
  <div><span class="stat-label">Pressão</span><br><span class="stat-value is-loading" id="weather-pressure">—</span></div>
  <div><span class="stat-label">Vento</span><br><span class="stat-value is-loading" id="weather-wind">—</span></div>`;

const RISK_PANEL_HTML = `
  <div class="risk-score-wrap">
    <div class="risk-score is-loading" id="risk-badge" aria-busy="true">—</div>
    <div class="risk-category" id="risk-category">—</div>
  </div>
  <div class="risk-recommendation" id="risk-recommendation">—</div>`;

function ensureWeatherLayout() {
  const el = document.getElementById("weather-container");
  if (!el) return;
  if (!document.getElementById("weather-temp")) {
    el.innerHTML = WEATHER_GRID_HTML;
  }
}

function ensureRiskLayout() {
  const el = document.getElementById("risk-container");
  if (!el) return;
  if (!document.getElementById("risk-badge")) {
    el.innerHTML = RISK_PANEL_HTML;
  }
}

function clearSectionError(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.classList.remove("has-error");
  el.querySelector(":scope > .section-error")?.remove();
}

function showSectionError(containerId, message) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (containerId === "weather-container") ensureWeatherLayout();
  if (containerId === "risk-container") ensureRiskLayout();
  el.classList.add("has-error");
  let err = el.querySelector(":scope > .section-error");
  if (!err) {
    err = document.createElement("div");
    err.className = "section-error";
    el.prepend(err);
  }
  err.innerHTML = `<i class="bi bi-exclamation-circle"></i>${message}`;
}

function showChartError(canvasId, message) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  canvas.style.display = "none";
  let err = canvas.parentElement?.querySelector(".chart-error-msg");
  if (!err) {
    err = document.createElement("div");
    err.className = "section-error chart-error-msg";
    canvas.insertAdjacentElement("afterend", err);
  }
  err.innerHTML = `<i class="bi bi-exclamation-circle"></i>${message}`;
}

function clearKpiLoading() {
  ["kpi-total", "kpi-avg", "kpi-day", "kpi-hour"].forEach((id) => {
    document.getElementById(id)?.classList.remove("is-loading");
  });
}

function clearStatLoading() {
  ["weather-temp", "weather-humidity", "weather-pressure", "weather-wind", "risk-badge"].forEach((id) => {
    document.getElementById(id)?.classList.remove("is-loading");
  });
}

var trendChartInstance = null;
var weeklyChartInstance = null;
var hourlyChartInstance = null;
var lastTrendData = null;
var lastWeeklyData = null;
var lastHourlyData = null;
var lastHeatmapData = null;
var lastHeatmapMax = 1;

function renderTrendChart(d) {
  if (typeof Chart === "undefined" || !d) return;
  const c = getThemeColors();
  if (trendChartInstance) trendChartInstance.destroy();
  trendChartInstance = new Chart(document.getElementById("trendChart"), {
    type: "line",
    data: {
      labels: Object.keys(d),
      datasets: [{
        label: "Alertas",
        data: Object.values(d),
        borderColor: c.blue,
        backgroundColor: c.blue + "26",
        borderWidth: 2,
        pointRadius: 2,
        pointHoverRadius: 5,
        tension: 0.35,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: c.text }, grid: { color: c.border } },
        y: { beginAtZero: true, ticks: { color: c.text }, grid: { color: c.border } },
      },
    },
  });
}

function renderWeeklyChart(d) {
  if (typeof Chart === "undefined" || !d) return;
  const c = getThemeColors();
  if (weeklyChartInstance) weeklyChartInstance.destroy();
  weeklyChartInstance = new Chart(document.getElementById("weeklyChart"), {
    type: "bar",
    data: {
      labels: Object.keys(d),
      datasets: [{
        data: Object.values(d),
        backgroundColor: c.blue + "b3",
        borderColor: c.blue,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: c.text }, grid: { color: c.border } },
        y: { beginAtZero: true, ticks: { color: c.text }, grid: { color: c.border } },
      },
    },
  });
}

function renderHourlyChart(d) {
  if (typeof Chart === "undefined" || !d) return;
  const c = getThemeColors();
  if (hourlyChartInstance) hourlyChartInstance.destroy();
  hourlyChartInstance = new Chart(document.getElementById("hourlyChart"), {
    type: "bar",
    data: {
      labels: Object.keys(d),
      datasets: [{
        data: Object.values(d),
        backgroundColor: c.green + "b3",
        borderColor: c.green,
        borderWidth: 1,
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: c.text, maxTicksLimit: 12 }, grid: { color: c.border } },
        y: { beginAtZero: true, ticks: { color: c.text }, grid: { color: c.border } },
      },
    },
  });
}

function refreshAllCharts() {
  if (lastTrendData) renderTrendChart(lastTrendData);
  if (lastWeeklyData) renderWeeklyChart(lastWeeklyData);
  if (lastHourlyData) renderHourlyChart(lastHourlyData);
}

function parseCssColorToRgb(cssColor) {
  const probe = document.createElement("span");
  probe.style.color = cssColor;
  document.body.appendChild(probe);
  const rgb = getComputedStyle(probe).color.match(/\d+/g);
  probe.remove();
  if (!rgb || rgb.length < 3) return [28, 35, 48];
  return rgb.slice(0, 3).map(Number);
}

function heatmapCellColor(v, maxV) {
  const t = maxV > 0 ? v / maxV : 0;
  if (t === 0) return getCssVar("--heatmap-empty") || getCssVar("--bg-card-2");
  const low = parseCssColorToRgb(getCssVar("--heatmap-low") || getCssVar("--blue"));
  const high = parseCssColorToRgb(getCssVar("--heatmap-high") || getCssVar("--green"));
  const r = Math.round(low[0] + t * (high[0] - low[0]));
  const g = Math.round(low[1] + t * (high[1] - low[1]));
  const b = Math.round(low[2] + t * (high[2] - low[2]));
  const alpha = 0.35 + t * 0.55;
  return `rgba(${r},${g},${b},${alpha})`;
}

function refreshHeatmapColors() {
  if (!lastHeatmapData) return;
  document.querySelectorAll("#heatmap-table tbody td:not(.hm-day)").forEach((td) => {
    const m = td.dataset.v;
    const v = m != null ? Number(m) : 0;
    td.style.background = heatmapCellColor(v, lastHeatmapMax);
  });
}

// ── API fetch (evita cache de respostas 503 antigas no navegador) ─────────
async function fetchApi(url, options = {}, retries = 3) {
  const fetchOpts = {
    cache: "no-store",
    headers: { Accept: "application/json", ...(options.headers || {}) },
    ...options,
  };
  for (let attempt = 0; attempt <= retries; attempt++) {
    const r = await fetch(url, fetchOpts);
    if (r.ok || ![502, 503, 504].includes(r.status) || attempt === retries) {
      return r;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000 * (attempt + 1)));
  }
  return fetch(url, fetchOpts);
}

// ── Localização & config ───────────────────────────────────────────────────
const LOC_KEY = "dashboard-location";
const LOC_COLLAPSED_KEY = "dashboard-location-collapsed";
const DEFAULT_LOC = { lat: -23.55, lon: -46.63 };
const LOC_RADIUS_KM = 50;
const MAP_APPLY_DEBOUNCE_MS = 400;
const BRAZIL_CITIES = [
  { id: "sp", name: "São Paulo, SP", lat: -23.5505, lon: -46.6333 },
  { id: "rj", name: "Rio de Janeiro, RJ", lat: -22.9068, lon: -43.1729 },
  { id: "bsb", name: "Brasília, DF", lat: -15.8267, lon: -47.9218 },
  { id: "cwb", name: "Curitiba, PR", lat: -25.4284, lon: -49.2733 },
  { id: "bh", name: "Belo Horizonte, MG", lat: -19.9167, lon: -43.9345 },
  { id: "poa", name: "Porto Alegre, RS", lat: -30.0346, lon: -51.2177 },
  { id: "ssa", name: "Salvador, BA", lat: -12.9714, lon: -38.5014 },
  { id: "rec", name: "Recife, PE", lat: -8.0476, lon: -34.877 },
  { id: "for", name: "Fortaleza, CE", lat: -3.7319, lon: -38.5267 },
  { id: "mao", name: "Manaus, AM", lat: -3.119, lon: -60.0217 },
  { id: "custom", name: "Personalizado (mapa)", lat: null, lon: null },
];
var dashboardConfig = { demo_mode: true, default_lat: DEFAULT_LOC.lat, default_lon: DEFAULT_LOC.lon };
var userLocation = { ...DEFAULT_LOC };  // var (não let) — evita TDZ no IIFE de tema
var lastDataSource = "pending";
var locationPickerMap = null;
var locationPickerMarker = null;
var locationPickerRadius = null;
var mapApplyTimer = null;
var locationReloading = false;
var hasAppliedLocationOnce = false;

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;
  const icons = { success: "bi-check-circle-fill", error: "bi-exclamation-circle-fill", info: "bi-info-circle-fill" };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.setAttribute("role", "status");
  toast.innerHTML = `<i class="bi ${icons[type] || icons.info}" aria-hidden="true"></i><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

function cityDisplayName(lat, lon) {
  const id = nearestCityId(lat, lon);
  const city = BRAZIL_CITIES.find((c) => c.id === id);
  if (city && city.id !== "custom") return city.name;
  return "Local personalizado";
}

function updateLocationHeader(lat, lon) {
  const cityEl = document.getElementById("location-city-name");
  const label = document.getElementById("location-label");
  const txt = `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`;
  if (cityEl) cityEl.textContent = cityDisplayName(lat, lon);
  if (label) label.textContent = txt;
  const windyTitle = document.getElementById("windy-map-title");
  if (windyTitle) windyTitle.textContent = `Chuva em tempo real — ${cityDisplayName(lat, lon)}`;
  updateWindyLoadingText(lat, lon);
}

function updateWindyLoadingText(lat, lon) {
  const el = document.getElementById("windy-loading-text");
  if (!el) return;
  const name = cityDisplayName(lat ?? userLocation.lat, lon ?? userLocation.lon);
  el.textContent = `Carregando radar para ${name}…`;
}

var applyBtnDefaultText = "Aplicar coordenadas";

function setLocationLoading(loading) {
  locationReloading = loading;
  const ids = ["btn-geo", "btn-reset-sp", "btn-apply-location", "select-city"];
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.disabled = loading;
  });
  const applyBtn = document.getElementById("btn-apply-location");
  if (applyBtn) {
    applyBtn.classList.toggle("is-loading", loading);
    applyBtn.textContent = loading ? "Atualizando…" : applyBtnDefaultText;
  }
}

function syncAdvancedAccordion(cityId) {
  const details = document.getElementById("location-advanced");
  if (!details) return;
  if (cityId === "custom") details.open = true;
}

function updateLocationPickerRadius(lat, lon) {
  if (!locationPickerMap || typeof L === "undefined") return;
  const blue = getCssVar("--blue") || "#58a6ff";
  if (locationPickerRadius) {
    locationPickerMap.removeLayer(locationPickerRadius);
  }
  locationPickerRadius = L.circle([lat, lon], {
    radius: LOC_RADIUS_KM * 1000,
    color: blue,
    weight: 1.5,
    opacity: 0.65,
    fillColor: blue,
    fillOpacity: 0.08,
    className: "location-picker-radius",
  }).addTo(locationPickerMap);
  if (locationPickerMarker) locationPickerMarker.bringToFront();
}

function scheduleMapAutoApply(lat, lon) {
  if (mapApplyTimer) clearTimeout(mapApplyTimer);
  mapApplyTimer = setTimeout(() => {
    applyLocationAndReload(lat, lon, { silent: false, collapseMobile: true, force: true });
  }, MAP_APPLY_DEBOUNCE_MS);
}

function syncCoordInputs(lat, lon) {
  const latEl = document.getElementById("input-lat");
  const lonEl = document.getElementById("input-lon");
  if (latEl) latEl.value = lat;
  if (lonEl) lonEl.value = lon;
}

function nearestCityId(lat, lon) {
  let best = "custom";
  let bestDist = Infinity;
  for (const c of BRAZIL_CITIES) {
    if (c.lat == null) continue;
    const d = (c.lat - lat) ** 2 + (c.lon - lon) ** 2;
    if (d < bestDist && d < 0.25) {
      bestDist = d;
      best = c.id;
    }
  }
  return best;
}

function syncCitySelect(lat, lon) {
  const sel = document.getElementById("select-city");
  if (!sel) return;
  sel.value = nearestCityId(lat, lon);
}

function populateCitySelect() {
  const sel = document.getElementById("select-city");
  if (!sel || sel.options.length) return;
  BRAZIL_CITIES.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.name;
    sel.appendChild(opt);
  });
}

function setPickerCoords(lat, lon, fly = true) {
  syncCoordInputs(lat, lon);
  const cityId = nearestCityId(lat, lon);
  syncCitySelect(lat, lon);
  syncAdvancedAccordion(cityId);
  updateLocationHeader(lat, lon);
  const sub = document.getElementById("weather-location-sub");
  if (sub) sub.textContent = `Coordenadas: ${lat.toFixed(4)}°, ${lon.toFixed(4)}°`;
  ensureLocationPickerMap();
  if (locationPickerMap && locationPickerMarker) {
    locationPickerMarker.setLatLng([lat, lon]);
    updateLocationPickerRadius(lat, lon);
    if (fly) locationPickerMap.setView([lat, lon], locationPickerMap.getZoom() || 8);
  }
}

function ensureLocationPickerMap() {
  if (locationPickerMap || typeof L === "undefined") return;
  const el = document.getElementById("location-picker-map");
  if (!el) return;
  const cfg = mapTileConfig();
  locationPickerMap = L.map(el, {
    zoomControl: false,
    scrollWheelZoom: false,
  });
  L.control.zoom({ position: "bottomright" }).addTo(locationPickerMap);
  L.tileLayer(cfg.url, { attribution: cfg.attribution, maxZoom: 18 }).addTo(locationPickerMap);
  locationPickerMarker = L.marker([userLocation.lat, userLocation.lon], { draggable: true }).addTo(locationPickerMap);
  locationPickerMap.setView([userLocation.lat, userLocation.lon], 8);
  locationPickerMap.on("click", (e) => {
    setPickerCoords(e.latlng.lat, e.latlng.lng, false);
    scheduleMapAutoApply(e.latlng.lat, e.latlng.lng);
  });
  locationPickerMarker.on("dragend", () => {
    const p = locationPickerMarker.getLatLng();
    setPickerCoords(p.lat, p.lng, false);
    scheduleMapAutoApply(p.lat, p.lng);
  });
  updateLocationPickerRadius(userLocation.lat, userLocation.lon);
  setTimeout(() => locationPickerMap.invalidateSize(), 150);
}

function loadStoredLocation() {
  try {
    const raw = localStorage.getItem(LOC_KEY);
    if (raw) {
      const p = JSON.parse(raw);
      if (typeof p.lat === "number" && typeof p.lon === "number") {
        userLocation = { lat: p.lat, lon: p.lon };
      }
    }
  } catch { /* ignore */ }
  populateCitySelect();
  setPickerCoords(userLocation.lat, userLocation.lon, true);
}

function saveLocation(lat, lon) {
  userLocation = { lat, lon };
  localStorage.setItem(LOC_KEY, JSON.stringify(userLocation));
  setPickerCoords(lat, lon, true);
  refreshWindyMap();
}

function updateLocationLabel() {
  updateLocationHeader(userLocation.lat, userLocation.lon);
  const sub = document.getElementById("weather-location-sub");
  if (sub) {
    const txt = `${userLocation.lat.toFixed(4)}°, ${userLocation.lon.toFixed(4)}°`;
    sub.textContent = `Coordenadas: ${txt}`;
  }
}

async function applyLocationAndReload(lat, lon, opts = {}) {
  const { silent = false, collapseMobile = false, force = false } = opts;
  if (locationReloading) {
    if (!silent) showToast("Aguarde — atualizando região…", "info");
    return;
  }
  const same =
    Math.abs(userLocation.lat - lat) < 0.0001 &&
    Math.abs(userLocation.lon - lon) < 0.0001;
  saveLocation(lat, lon);
  if (same && hasAppliedLocationOnce && !force) return;
  setLocationLoading(true);
  try {
    await reloadLocationDependentData();
    hasAppliedLocationOnce = true;
    if (!silent) showToast(`Região atualizada — ${cityDisplayName(lat, lon)}`, "success");
    if (collapseMobile && window.innerWidth < 768) collapseLocationBar(true);
  } catch {
    if (!silent) showToast("Falha ao atualizar dados da região", "error");
  } finally {
    setLocationLoading(false);
  }
}

function collapseLocationBar(collapsed) {
  const bar = document.getElementById("location-bar");
  const btn = document.getElementById("btn-location-collapse");
  if (!bar || !btn) return;
  const wasCompact = bar.classList.contains("is-compact");
  bar.classList.toggle("is-compact", collapsed);
  btn.setAttribute("aria-expanded", String(!collapsed));
  localStorage.setItem(LOC_COLLAPSED_KEY, collapsed ? "1" : "0");
  if (wasCompact && !collapsed && locationPickerMap) {
    setTimeout(() => locationPickerMap.invalidateSize(), 200);
  }
}

function resetToSaoPaulo() {
  const sp = BRAZIL_CITIES.find((c) => c.id === "sp");
  if (!sp) return;
  applyLocationAndReload(sp.lat, sp.lon, { silent: false, force: true });
}

function windyEmbedUrl(lat, lon) {
  const tpl = document.querySelector(".windy-frame")?.dataset.srcTemplate || "";
  return tpl.replace(/\{lat\}/g, String(lat)).replace(/\{lon\}/g, String(lon));
}

function refreshWindyMap() {
  const iframe = document.getElementById("windy-iframe") || document.querySelector(".windy-frame");
  const loading = document.getElementById("windy-loading");
  if (!iframe) return;
  updateWindyLoadingText(userLocation.lat, userLocation.lon);
  if (loading) loading.hidden = false;
  iframe.onload = () => { if (loading) loading.hidden = true; };
  iframe.src = windyEmbedUrl(userLocation.lat, userLocation.lon);
}

function lazyLoadWindy() {
  const iframe = document.getElementById("windy-iframe") || document.querySelector(".windy-frame");
  if (!iframe) return;
  const loading = document.getElementById("windy-loading");
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !iframe.src) {
        if (loading) loading.hidden = false;
        iframe.onload = () => { if (loading) loading.hidden = true; };
        iframe.src = windyEmbedUrl(userLocation.lat, userLocation.lon);
        observer.unobserve(iframe);
      }
    });
  }, { rootMargin: "100px" });
  observer.observe(iframe);
}

function updateWindyIframe() { refreshWindyMap(); }

// ── Mapa da região (Leaflet + GeoJSON) ───────────────────────────────────
var regionMap = null;
var regionAlertsLayer = null;
var regionTileLayer = null;
const REGION_MAP_PAD = 2.5;

function locationBBox(lat, lon, pad = REGION_MAP_PAD) {
  const south = Math.max(-90, lat - pad);
  const north = Math.min(90, lat + pad);
  const west = Math.max(-180, lon - pad);
  const east = Math.min(180, lon + pad);
  return `${south},${west},${north},${east}`;
}

function mapTileConfig() {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  return isDark
    ? {
        url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; CARTO',
      }
    : {
        url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; CARTO',
      };
}

function ensureRegionMap() {
  if (regionMap || typeof L === "undefined") return;
  const el = document.getElementById("region-map");
  if (!el) return;
  regionMap = L.map(el, { zoomControl: true, scrollWheelZoom: true });
  const cfg = mapTileConfig();
  regionTileLayer = L.tileLayer(cfg.url, {
    attribution: cfg.attribution,
    maxZoom: 18,
  }).addTo(regionMap);
  regionAlertsLayer = L.layerGroup().addTo(regionMap);
  regionMap.setView([userLocation.lat, userLocation.lon], 8);
}

function refreshRegionMapTiles() {
  if (!regionMap) return;
  const cfg = mapTileConfig();
  if (regionTileLayer) regionMap.removeLayer(regionTileLayer);
  regionTileLayer = L.tileLayer(cfg.url, {
    attribution: cfg.attribution,
    maxZoom: 18,
  }).addTo(regionMap);
  if (regionAlertsLayer) regionAlertsLayer.bringToFront();
}

function refreshLocationPickerTiles() {
  if (!locationPickerMap) return;
  const cfg = mapTileConfig();
  locationPickerMap.eachLayer((layer) => {
    if (layer instanceof L.TileLayer) locationPickerMap.removeLayer(layer);
  });
  L.tileLayer(cfg.url, { attribution: cfg.attribution, maxZoom: 18 }).addTo(locationPickerMap);
  if (locationPickerRadius) locationPickerRadius.bringToFront();
  if (locationPickerMarker) locationPickerMarker.bringToFront();
}

function formatAlertTimestamp(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  return isNaN(d.getTime())
    ? ts
    : d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function stormPopupHtml(props) {
  const conf = props.intensity != null
    ? `${Math.round(props.intensity * 100)}%`
    : "—";
  return `<strong>Alerta de tempestade</strong><br>` +
    `Confiança: ${conf}<br>` +
    `Horário: ${formatAlertTimestamp(props.timestamp)}`;
}

function renderRegionAlerts(geojson) {
  ensureRegionMap();
  if (!regionMap || !regionAlertsLayer) return;

  regionAlertsLayer.clearLayers();
  const features = geojson?.features || [];
  const emptyEl = document.getElementById("region-map-empty");

  if (features.length === 0) {
    if (emptyEl) emptyEl.hidden = false;
    regionMap.setView([userLocation.lat, userLocation.lon], 8);
    setTimeout(() => regionMap.invalidateSize(), 100);
    return;
  }

  if (emptyEl) emptyEl.hidden = true;

  const layer = L.geoJSON(geojson, {
    pointToLayer(feature, latlng) {
      return L.circleMarker(latlng, {
        radius: 9,
        fillColor: getCssVar("--red") || "#f85149",
        color: "#fff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85,
      });
    },
    onEachFeature(feature, layer) {
      const props = feature.properties || {};
      layer.bindPopup(stormPopupHtml(props));
    },
  });
  layer.addTo(regionAlertsLayer);

  const bounds = layer.getBounds();
  if (bounds.isValid()) {
    regionMap.fitBounds(bounds.pad(0.25), { maxZoom: 10 });
  } else {
    regionMap.setView([userLocation.lat, userLocation.lon], 8);
  }
  setTimeout(() => regionMap.invalidateSize(), 100);
}

async function loadRegionMap() {
  const coordsEl = document.getElementById("region-map-coords");
  const txt = `${userLocation.lat.toFixed(4)}°, ${userLocation.lon.toFixed(4)}°`;
  if (coordsEl) coordsEl.textContent = txt;

  ensureRegionMap();
  if (regionMap) {
    regionMap.setView([userLocation.lat, userLocation.lon], regionMap.getZoom() || 8);
  }

  try {
    const bbox = locationBBox(userLocation.lat, userLocation.lon);
    const r = await fetchApi(`/api/map/overlay?bbox=${encodeURIComponent(bbox)}`);
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    renderRegionAlerts(data);
  } catch {
    renderRegionAlerts({ type: "FeatureCollection", features: [] });
  }
}

function lazyInitRegionMap() {
  const wrap = document.querySelector(".region-map-wrap");
  if (!wrap || typeof L === "undefined") return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        ensureRegionMap();
        loadRegionMap();
        observer.unobserve(wrap);
      }
    });
  }, { rootMargin: "80px" });
  observer.observe(wrap);
}

function setDataSourceChip(source) {
  if (source === "live") lastDataSource = "live";
  else if (source === "demo") lastDataSource = lastDataSource === "live" ? "live" : "demo";
  else if (source === "unavailable") lastDataSource = "offline";
  else if (source === "pending") lastDataSource = "pending";

  const chip = document.getElementById("data-source-chip");
  if (!chip) return;
  const labels = {
    pending: ["Carregando…", "demo"],
    demo: ["Demonstração", "demo"],
    live: ["Dados reais", "live"],
    offline: ["Offline", "offline"],
  };
  // Chip reflete a fonte real da resposta (header X-Data-Source), não a flag DEMO_MODE do servidor
  const mode = lastDataSource === "offline" ? "offline"
    : lastDataSource === "demo" ? "demo"
    : lastDataSource === "live" ? "live" : "pending";
  const [text, cls] = labels[mode];
  chip.textContent = text;
  chip.className = `data-source-chip ${cls}`;

  const footerHint = document.getElementById("footer-storage-hint");
  if (footerHint) {
    footerHint.textContent = mode === "live"
      ? "dados via AWS DynamoDB"
      : mode === "demo"
        ? "dados de demonstração (JSON local)"
        : "sem conexão com o servidor";
  }
}

function noteResponseSource(response) {
  const src = response.headers.get("X-Data-Source");
  if (src) setDataSourceChip(src);
}

function setLastUpdated(date) {
  const el = document.getElementById("data-source-updated");
  if (!el) return;
  const ts = date instanceof Date && !isNaN(date)
    ? date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
    : new Date().toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  el.textContent = `Atualizado: ${ts}`;
}

async function loadDashboardConfig() {
  try {
    const r = await fetchApi("/api/dashboard/config");
    if (r.ok) {
      dashboardConfig = await r.json();
      noteResponseSource(r);
    }
  } catch { /* defaults */ }
  if (!dashboardConfig.demo_mode) {
    const dev = document.getElementById("yolo-dev-actions");
    if (dev) dev.style.display = "none";
  }
  setDataSourceChip("pending");
}

function applyLocationFromInputs() {
  const lat = parseFloat(document.getElementById("input-lat").value);
  const lon = parseFloat(document.getElementById("input-lon").value);
  if (Number.isNaN(lat) || Number.isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    showToast("Coordenadas inválidas — verifique latitude e longitude", "error");
    return;
  }
  applyLocationAndReload(lat, lon, { collapseMobile: true, force: true });
}

function onCitySelectChange() {
  const sel = document.getElementById("select-city");
  const city = BRAZIL_CITIES.find((c) => c.id === sel?.value);
  if (!city) return;
  if (city.id === "custom") {
    syncAdvancedAccordion("custom");
    return;
  }
  if (city.lat == null) return;
  applyLocationAndReload(city.lat, city.lon, { collapseMobile: true, force: true });
}

function requestGeolocation() {
  if (!navigator.geolocation) {
    showToast("Seu navegador não suporta geolocalização", "error");
    return;
  }
  showToast("Obtendo sua posição…", "info");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      applyLocationAndReload(pos.coords.latitude, pos.coords.longitude, {
        collapseMobile: true,
        force: true,
      });
    },
    (err) => {
      const msgs = {
        1: "Permissão negada — habilite localização nas configurações do navegador",
        2: "Posição indisponível — tente novamente ou escolha no mapa",
        3: "Tempo esgotado — tente novamente",
      };
      showToast(msgs[err?.code] || "Não foi possível obter sua localização", "error");
    },
    { enableHighAccuracy: true, timeout: 12000 }
  );
}

function initLocationBarUX() {
  const bar = document.getElementById("location-bar");
  const collapseBtn = document.getElementById("btn-location-collapse");
  const badge = document.getElementById("location-badge");
  if (localStorage.getItem(LOC_COLLAPSED_KEY) === "1") collapseLocationBar(true);

  collapseBtn?.addEventListener("click", () => {
    const isCompact = bar?.classList.contains("is-compact");
    collapseLocationBar(!isCompact);
  });

  badge?.addEventListener("click", () => {
    if (bar?.classList.contains("is-compact")) collapseLocationBar(false);
  });
  badge?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (bar?.classList.contains("is-compact")) collapseLocationBar(false);
    }
  });
  if (badge) {
    badge.setAttribute("role", "button");
    badge.setAttribute("tabindex", "0");
    badge.setAttribute("title", "Expandir painel de região");
  }

  const onScroll = () => {
    if (!bar) return;
    const topbarH = document.querySelector(".topbar")?.offsetHeight || 52;
    const rect = bar.getBoundingClientRect();
    bar.classList.toggle("is-stuck", rect.top <= topbarH + 4);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const navLinks = document.querySelectorAll(".page-nav-link");
  navLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
      const href = link.getAttribute("href");
      if (!href?.startsWith("#")) return;
      const target = document.querySelector(href);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      history.replaceState(null, "", href);
    });
  });

  const sections = [...navLinks]
    .map((a) => document.querySelector(a.getAttribute("href")))
    .filter(Boolean);
  if (sections.length && "IntersectionObserver" in window) {
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const id = entry.target.id;
          navLinks.forEach((link) => {
            link.classList.toggle("is-active", link.getAttribute("href") === `#${id}`);
          });
        });
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: 0 }
    );
    sections.forEach((sec) => obs.observe(sec));
  }

  const mapEl = document.getElementById("location-picker-map");
  if (mapEl && "ResizeObserver" in window) {
    const ro = new ResizeObserver(() => {
      if (locationPickerMap) locationPickerMap.invalidateSize();
    });
    ro.observe(mapEl);
  }
}

function syncSlidersFromWeather(data) {
  const slTemp = document.getElementById("sl-temp");
  const slUmid = document.getElementById("sl-umid");
  const slPrec = document.getElementById("sl-prec");
  const slVento = document.getElementById("sl-vento");
  if (data.temperature != null && slTemp) {
    slTemp.value = Math.min(45, Math.max(5, data.temperature));
  }
  if (data.humidity != null && slUmid) {
    slUmid.value = Math.round(data.humidity);
  }
  if (data.precipitation != null && slPrec) {
    slPrec.value = Math.min(50, Math.max(0, data.precipitation));
  }
  if (data.wind_speed != null && slVento) {
    slVento.value = Math.round(Math.min(120, Math.max(0, data.wind_speed * 3.6)));
  }
  updateMLPredictor();
}

async function reloadLocationDependentData() {
  ensureWeatherLayout();
  ensureRiskLayout();
  clearSectionError("weather-container");
  clearSectionError("risk-container");
  const badge = document.getElementById("risk-badge");
  if (badge) {
    badge.classList.add("is-loading");
    badge.textContent = "—";
  }
  await Promise.all([loadWeatherData(), loadRiskData(), loadRegionMap()]);
  refreshWindyMap();
}

// ── Defaults ─────────────────────────────────────────────────────────────
const colors = getThemeColors();
if (typeof Chart !== "undefined") {
  Chart.defaults.color = colors.text;
  Chart.defaults.font.family = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
}

// ── KPIs ──────────────────────────────────────────────────────────────────
async function loadKPIs() {
  try {
    const r = await fetchApi("/api/alerts/summary");
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    if (d.total_30d == null) throw new Error("empty");
    const kTotal = document.getElementById("kpi-total");
    const kAvg = document.getElementById("kpi-avg");
    const kDay = document.getElementById("kpi-day");
    const kHour = document.getElementById("kpi-hour");
    if (!kTotal || !kAvg || !kDay || !kHour) return;
    kTotal.textContent = d.total_30d;
    kAvg.textContent   = d.daily_avg;
    kDay.textContent   = d.peak_day;
    kHour.textContent  = d.peak_hour;
    clearKpiLoading();
  } catch (err) {
    console.warn("KPIs:", err);
    clearKpiLoading();
    ["kpi-total", "kpi-avg", "kpi-day", "kpi-hour"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.textContent = "—";
    });
  }
}

// ── Real-Time Weather Data ─────────────────────────────────────────────────
async function loadWeatherData() {
  ensureWeatherLayout();
  clearSectionError("weather-container");
  try {
    const q = `lat=${userLocation.lat}&lon=${userLocation.lon}`;
    const r = await fetchApi(`/api/weather/current?${q}`);
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();

    document.getElementById("weather-temp").textContent = `${data.temperature}°C`;
    document.getElementById("weather-humidity").textContent = `${data.humidity}%`;
    document.getElementById("weather-pressure").textContent = `${data.pressure} hPa`;
    document.getElementById("weather-wind").textContent = `${data.wind_speed} m/s`;
    clearStatLoading();

    const ts = new Date(data.timestamp);
    document.getElementById("weather-timestamp").textContent =
      `Clima: ${ts.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}`;
    setLastUpdated(ts);
    setDataSourceChip("live");
    syncSlidersFromWeather(data);
  } catch {
    clearStatLoading();
    showSectionError("weather-container", "Clima indisponível — verifique se a API está rodando");
    setDataSourceChip("unavailable");
  }
}

// ── Real-Time Risk Assessment ──────────────────────────────────────────────
async function loadRiskData() {
  ensureRiskLayout();
  clearSectionError("risk-container");
  try {
    const q = `lat=${userLocation.lat}&lon=${userLocation.lon}`;
    const r = await fetchApi(`/api/risk/forecast?${q}`);
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    
    const categoryClasses = {
      "LOW": { cls: "risk-low", text: "BAIXO" },
      "MEDIUM": { cls: "risk-moderate", text: "MÉDIO" },
      "HIGH": { cls: "risk-high", text: "ALTO" }
    };
    
    const colorSet = categoryClasses[data.risk_category] || categoryClasses.LOW;
    const badge = document.getElementById("risk-badge");
    const category = document.getElementById("risk-category");
    
    badge.textContent = `${(data.risk_score * 100).toFixed(0)}%`;
    badge.className = "risk-score " + colorSet.cls;
    badge.classList.remove("is-loading");
    
    category.textContent = `Risco ${colorSet.text}`;
    category.className = "risk-category " + colorSet.cls;
    
    document.getElementById("risk-recommendation").textContent = 
      data.recommendation;
  } catch {
    clearStatLoading();
    const badge = document.getElementById("risk-badge");
    if (badge) {
      badge.classList.remove("is-loading");
      badge.textContent = "—";
    }
    showSectionError("risk-container", "Risco indisponível no momento");
  }
}

// ── YOLO Storm Detector Status ──────────────────────────────────────────────
async function loadYOLOStatus() {
  try {
    const r = await fetchApi("/api/storms/detector-status");
    const data = await r.json();
    if (data.available) {
      document.getElementById("yolo-status").textContent = "Operacional";
      document.getElementById("yolo-status").className = "yolo-stat-value risk-low";
    } else if (data.model_exists) {
      document.getElementById("yolo-status").textContent = "Modelo presente, detector não carregou";
      document.getElementById("yolo-status").className = "yolo-stat-value risk-moderate";
    } else {
      document.getElementById("yolo-status").textContent = "Sem best.pt";
      document.getElementById("yolo-status").className = "yolo-stat-value risk-high";
    }
  } catch {
    document.getElementById("yolo-status").textContent = "Erro ao verificar";
    document.getElementById("yolo-status").className = "yolo-stat-value risk-high";
  }
}

async function loadRecentStorms() {
  const el = document.getElementById("storms-recent-list");
  try {
    const r = await fetchApi("/api/storms/recent?hours=168");
    noteResponseSource(r);
    const storms = await r.json();
    if (!Array.isArray(storms) || storms.length === 0) {
      el.innerHTML =
        '<div class="section-empty" style="padding:0.5rem 0;">' +
        '<i class="bi bi-cloud-slash" aria-hidden="true"></i>' +
        'Nenhum alerta no store local — clique em Simular alerta.</div>';
      return;
    }
    el.innerHTML = storms.slice(0, 8).map(s => {
      const t = s.timestamp ? new Date(s.timestamp).toLocaleString("pt-BR") : "—";
      return `<div style="padding:4px 0;border-bottom:1px solid var(--border);">
        <strong>${(s.confidence * 100).toFixed(0)}%</strong> · ${t} · ${s.latitude?.toFixed(2)}, ${s.longitude?.toFixed(2)}
      </div>`;
    }).join("");
  } catch (e) {
    el.textContent = "Lista de tempestades indisponível (API offline).";
  }
}

async function detectSampleImage() {
  const btn = document.getElementById("btn-detect-sample");
  const status = document.getElementById("test-status");
  btn.disabled = true;
  status.textContent = "Inferência YOLO…";
  try {
    const r = await fetchApi("/api/storms/detect-sample", { method: "POST" });
    const data = await r.json();
    if (data.success) {
      status.textContent = data.message || "Detecção concluída";
      document.getElementById("yolo-last-detection").textContent =
        new Date(data.timestamp).toLocaleTimeString("pt-BR");
      document.getElementById("yolo-avg-confidence").textContent =
        data.num_detections > 0
          ? `${(data.average_confidence * 100).toFixed(0)}%`
          : "—";
    } else {
      status.textContent = data.error || "Falha";
    }
  } catch (err) {
    status.textContent = err.message;
  }
  btn.disabled = false;
}

// ── Test Storm Detection (Simulate) ────────────────────────────────────────
async function testStormDetection() {
  const btn = document.getElementById("btn-test-detection");
  const status = document.getElementById("test-status");
  
  btn.disabled = true;
  status.textContent = "Processando...";
  
  try {
    const r = await fetchApi("/api/alerts/simulate-detection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confidence: 0.85,
        lat: userLocation.lat,
        lon: userLocation.lon
      })
    });
    
    const data = await r.json();
    
    if (data.success) {
      status.textContent = "Alerta registrado!";
      document.getElementById("yolo-last-detection").textContent = 
        new Date(data.alert.timestamp).toLocaleTimeString("pt-BR");
      document.getElementById("yolo-avg-confidence").textContent = 
        `${(data.alert.confidence * 100).toFixed(0)}%`;
      loadRecentStorms();
      loadWeekly();
      loadHourly();
      loadTrend();
      loadHeatmap();
      loadKPIs();
      loadRegionMap();
      
      setTimeout(() => {
        status.textContent = "";
        btn.disabled = false;
      }, 3000);
    } else {
      status.textContent = data.error || "Falha na simulação";
      btn.disabled = false;
    }
  } catch (err) {
    status.textContent = "Erro: " + err.message;
    btn.disabled = false;
  }
}

// ── Trend chart ───────────────────────────────────────────────────────────
async function loadTrend() {
  if (typeof Chart === "undefined") return;
  const r = await fetchApi("/api/alerts/daily");
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (!d || typeof d !== "object") throw new Error("empty");
  lastTrendData = d;
  renderTrendChart(d);
}

// ── Weekly chart ──────────────────────────────────────────────────────────
async function loadWeekly() {
  if (typeof Chart === "undefined") return;
  const r = await fetchApi("/api/alerts/weekly");
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (!d || typeof d !== "object") throw new Error("empty");
  lastWeeklyData = d;
  renderWeeklyChart(d);
}

// ── Hourly chart ──────────────────────────────────────────────────────────
async function loadHourly() {
  if (typeof Chart === "undefined") return;
  const r = await fetchApi("/api/alerts/hourly");
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (!d || typeof d !== "object") throw new Error("empty");
  lastHourlyData = d;
  renderHourlyChart(d);
}

// ── Heatmap ───────────────────────────────────────────────────────────────
async function loadHeatmap() {
  const r = await fetchApi("/api/alerts/heatmap");
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const data = await r.json();
  if (!Array.isArray(data)) throw new Error("empty");
  lastHeatmapData = data;

  const DAYS  = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"];
  const HOURS = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2,"0")}h`);

  const map = {};
  data.forEach(({ x, y, v }) => { map[`${y}-${x}`] = v; });
  lastHeatmapMax = Math.max(...data.map(d => d.v), 1);

  const thead = document.querySelector("#heatmap-table thead tr");
  const tbody = document.querySelector("#heatmap-table tbody");
  if (!thead || !tbody) return;

  thead.innerHTML = "<th></th>";
  HOURS.forEach(h => {
    const th = document.createElement("th");
    th.textContent = h.replace("h","");
    thead.appendChild(th);
  });

  tbody.innerHTML = "";
  DAYS.forEach((day, dy) => {
    const tr = document.createElement("tr");
    const label = document.createElement("td");
    label.className = "hm-day";
    label.textContent = day;
    tr.appendChild(label);

    HOURS.forEach((_, hx) => {
      const v  = map[`${dy}-${hx}`] ?? 0;
      const td = document.createElement("td");
      td.dataset.v = String(v);
      td.style.background = heatmapCellColor(v, lastHeatmapMax);
      td.title = `${day} ${HOURS[hx]}: ${v} alerta(s)`;
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });
}

// ── ML Agrícola — Predictor Interativo ────────────────────────────────────
var mlDebounce = null;

async function updateMLPredictor() {
  const temp  = parseFloat(document.getElementById("sl-temp").value);
  const umid  = parseFloat(document.getElementById("sl-umid").value);
  const prec  = parseFloat(document.getElementById("sl-prec").value);
  const vento = parseFloat(document.getElementById("sl-vento").value);

  document.getElementById("lbl-temp").textContent  = `${temp}°C`;
  document.getElementById("lbl-umid").textContent  = `${umid}%`;
  document.getElementById("lbl-prec").textContent  = `${prec} mm/h`;
  document.getElementById("lbl-vento").textContent = `${vento} km/h`;

  clearTimeout(mlDebounce);
  mlDebounce = setTimeout(async () => {
    try {
      const r = await fetchApi(
        `/api/ml/agricultural-risk?temperatura=${temp}&umidade=${umid}&precipitacao=${prec}&vento_kmh=${vento}`
      );
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
        `<span class="risk-low">Baixo</span> ${Math.round((p.LOW||0)*100)}%<br>` +
        `<span class="risk-moderate">Médio</span> ${Math.round((p.MEDIUM||0)*100)}%<br>` +
        `<span class="risk-high">Alto</span> ${Math.round((p.HIGH||0)*100)}%`;
    } catch {
      document.getElementById("ml-score").textContent = "—";
      document.getElementById("ml-rec").textContent   = "Backend indisponível";
    }
  }, 400);
}

["sl-temp","sl-umid","sl-prec","sl-vento"].forEach((id) => {
  const el = document.getElementById(id);
  if (el) el.addEventListener("input", updateMLPredictor);
});

// ── Galeria NASA ──────────────────────────────────────────────────────────
async function loadNASAGallery() {
  try {
    const r = await fetchApi("/api/nasa/capturas?limite=12");
    const d = await r.json();
    const gallery = document.getElementById("nasa-gallery");
    const empty   = document.getElementById("nasa-empty");

    document.getElementById("nasa-total").textContent =
      d.total > 0 ? `${d.total} imagens disponíveis` : "Nenhuma imagem capturada ainda";

    if (!d.capturas || d.capturas.length === 0) {
      empty.innerHTML =
        '<i class="bi bi-globe-americas"></i> Nenhuma imagem NASA capturada ainda.<br>' +
        '<span style="font-size:11px">Execute <code>build_dataset_nasa.command</code> para baixar o histórico.</span>';
      return;
    }

    empty.remove();
    d.capturas.forEach(cap => {
      const div = document.createElement("div");
      div.className = "nasa-card";
      const ts = new Date(cap.criado_em).toLocaleString("pt-BR", {
        month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit"
      });
      div.innerHTML = `
        <div class="nasa-card-thumb"><i class="bi bi-globe-americas"></i></div>
        <div class="nasa-card-body">
          <div class="nasa-card-title">${cap.arquivo}</div>
          <div class="nasa-card-meta">${ts} · ${cap.tamanho_kb} KB</div>
        </div>`;
      gallery.appendChild(div);
    });
  } catch (e) {
    const emptyEl = document.getElementById("nasa-empty");
    if (emptyEl) {
      emptyEl.className = "section-error";
      emptyEl.style.gridColumn = "1/-1";
      emptyEl.innerHTML = '<i class="bi bi-exclamation-circle"></i> Galeria indisponível';
    }
  }
}

const CHART_ERROR_MSG = "Dados indisponíveis";

async function safeLoad(name, fn) {
  try {
    await fn();
  } catch (err) {
    console.warn(`Dashboard: falha em ${name}`, err);
    if (name === "trend") showChartError("trendChart", CHART_ERROR_MSG);
    if (name === "weekly") showChartError("weeklyChart", CHART_ERROR_MSG);
    if (name === "hourly") showChartError("hourlyChart", CHART_ERROR_MSG);
  }
}

async function loadIoTReadings() {
  try {
    const resp = await fetch("/api/iot/readings/latest?hours=24");
    const data = resp.ok ? await resp.json() : null;
    const readings = data?.readings ?? [];
    const latest = readings[0] ?? null;

    const chip = document.getElementById("iot-source-chip");
    const badge = document.getElementById("iot-status-badge");
    const storageLabel = document.getElementById("iot-storage-label");

    if (chip) { chip.hidden = false; chip.textContent = resp.ok ? "API" : "Demonstração"; }
    if (badge) { badge.textContent = resp.ok ? "Online" : "Demo"; badge.className = "iot-status-badge " + (resp.ok ? "badge-ok" : "badge-demo"); }
    if (storageLabel) storageLabel.textContent = data?.storage ?? "—";

    if (latest) {
      const fmt = (v, unit) => v != null ? `${v}${unit}` : "—";
      const ts = latest.timestamp ? new Date(latest.timestamp).toLocaleString("pt-BR") : "—";
      document.getElementById("iot-temp").textContent  = fmt(latest.temperatura, " °C");
      document.getElementById("iot-umid").textContent  = fmt(latest.umidade, " %");
      document.getElementById("iot-cidade").textContent = latest.cidade ?? "—";
      document.getElementById("iot-ts").textContent    = ts;
      ["iot-temp","iot-umid","iot-cidade","iot-ts"].forEach(id => document.getElementById(id)?.classList.remove("is-loading"));
    }

    if (readings.length > 1) {
      const wrap = document.getElementById("iot-history-wrap");
      const tbody = document.getElementById("iot-history-body");
      if (wrap && tbody) {
        tbody.innerHTML = readings.slice(0, 10).map(r => {
          const ts = r.timestamp ? new Date(r.timestamp).toLocaleString("pt-BR") : "—";
          return `<tr><td>${ts}</td><td>${r.device_id ?? "—"}</td><td>${r.temperatura ?? "—"}</td><td>${r.umidade ?? "—"}</td><td>${r.cidade ?? "—"}</td></tr>`;
        }).join("");
        wrap.hidden = false;
      }
    }
  } catch (err) {
    console.warn("IoT: falha ao carregar leituras", err);
  }
}

async function bootstrapDashboard() {
  await loadDashboardConfig();
  await Promise.allSettled([
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
  setLastUpdated(new Date());
  hasAppliedLocationOnce = true;
}

function bindLocationControls() {
  document.getElementById("btn-apply-location")?.addEventListener("click", applyLocationFromInputs);
  document.getElementById("btn-geo")?.addEventListener("click", requestGeolocation);
  document.getElementById("btn-reset-sp")?.addEventListener("click", resetToSaoPaulo);
  document.getElementById("select-city")?.addEventListener("change", onCitySelectChange);
  ["input-lat", "input-lon"].forEach((id) => {
    document.getElementById(id)?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        applyLocationFromInputs();
      }
    });
  });
}

async function initDashboard() {
  initTheme();
  loadStoredLocation();
  ensureLocationPickerMap();
  initLocationBarUX();
  bindLocationControls();
  await bootstrapDashboard();
  lazyLoadWindy();
  lazyInitRegionMap();

  const btnTest = document.getElementById("btn-test-detection");
  const btnSample = document.getElementById("btn-detect-sample");
  if (btnTest) btnTest.addEventListener("click", testStormDetection);
  if (btnSample) btnSample.addEventListener("click", detectSampleImage);
}

// ── Bootstrap ─────────────────────────────────────────────────────────────
initDashboard();
