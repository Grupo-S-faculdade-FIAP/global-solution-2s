import { state } from "../core/state.js";
import { REGION_MAP_PAD } from "../core/constants.js";
import { map } from "../core/api/endpoints.js";
import { SEL } from "../core/selectors.js";
import { getCssVar } from "../core/css.js";
import { noteResponseSource } from "../core/ui.js";
import { mapTileConfig } from "./tiles.js";

export function locationBBox(lat, lon, pad = REGION_MAP_PAD) {
  const south = Math.max(-90, lat - pad);
  const north = Math.min(90, lat + pad);
  const west = Math.max(-180, lon - pad);
  const east = Math.min(180, lon + pad);
  return `${south},${west},${north},${east}`;
}

function formatAlertTimestamp(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  return isNaN(d.getTime())
    ? ts
    : d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function stormPopupHtml(props) {
  const conf = props.intensity != null ? `${Math.round(props.intensity * 100)}%` : "—";
  return `<strong>Alerta de tempestade</strong><br>Confiança: ${conf}<br>Horário: ${formatAlertTimestamp(props.timestamp)}`;
}

function featureTimestamp(feature) {
  const ts = feature?.properties?.timestamp;
  const d = ts ? new Date(ts) : null;
  return d && !isNaN(d.getTime()) ? d : null;
}

function updateRegionAlertStatus(features, loadFailed = false) {
  const badge = document.getElementById(SEL.regionAlertBadge);
  const message = document.getElementById(SEL.regionAlertMessage);
  if (!badge || !message) return;

  badge.className = "region-alert-badge";
  if (loadFailed) {
    badge.classList.add("region-alert-badge-warning");
    badge.textContent = "Indisponível";
    message.textContent = "Não foi possível consultar os alertas agora. Tente novamente em alguns instantes.";
    return;
  }

  if (!features.length) {
    badge.classList.add("region-alert-badge-ok");
    badge.textContent = "Sem alerta ativo";
    message.textContent = "Nenhum alerta de tempestade foi encontrado na sua área nos últimos 7 dias.";
    return;
  }

  const maxConfidence = features.reduce((max, feature) => {
    const intensity = Number(feature?.properties?.intensity);
    return Number.isFinite(intensity) ? Math.max(max, intensity) : max;
  }, 0);
  const latest = features
    .map(featureTimestamp)
    .filter(Boolean)
    .sort((a, b) => b.getTime() - a.getTime())[0];
  const countLabel = features.length === 1 ? "1 alerta" : `${features.length} alertas`;
  const confidenceLabel = maxConfidence > 0 ? `, confiança máxima ${Math.round(maxConfidence * 100)}%` : "";
  const latestLabel = latest ? `, mais recente em ${formatAlertTimestamp(latest.toISOString())}` : "";

  badge.classList.add("region-alert-badge-danger");
  badge.textContent = "Alerta de tempestade";
  message.textContent = `${countLabel} no raio monitorado${confidenceLabel}${latestLabel}.`;
}

export function ensureRegionMap() {
  if (state.regionMap || typeof L === "undefined") return;
  const el = document.getElementById("region-map");
  if (!el) return;
  state.regionMap = L.map(el, { zoomControl: true, scrollWheelZoom: true });
  const cfg = mapTileConfig();
  state.regionTileLayer = L.tileLayer(cfg.url, { attribution: cfg.attribution, maxZoom: 18 }).addTo(state.regionMap);
  state.regionAlertsLayer = L.layerGroup().addTo(state.regionMap);
  state.regionMap.setView([state.userLocation.lat, state.userLocation.lon], 8);
}

export function refreshRegionMapTiles() {
  if (!state.regionMap) return;
  const cfg = mapTileConfig();
  if (state.regionTileLayer) state.regionMap.removeLayer(state.regionTileLayer);
  state.regionTileLayer = L.tileLayer(cfg.url, { attribution: cfg.attribution, maxZoom: 18 }).addTo(state.regionMap);
  if (state.regionAlertsLayer) {
    state.regionMap.removeLayer(state.regionAlertsLayer);
    state.regionAlertsLayer.addTo(state.regionMap);
  }
}

export function refreshLocationPickerTiles() {
  if (!state.locationPickerMap) return;
  const cfg = mapTileConfig();
  state.locationPickerMap.eachLayer((layer) => {
    if (layer instanceof L.TileLayer) state.locationPickerMap.removeLayer(layer);
  });
  L.tileLayer(cfg.url, { attribution: cfg.attribution, maxZoom: 18 }).addTo(state.locationPickerMap);
  if (state.locationPickerRadius?.bringToFront) state.locationPickerRadius.bringToFront();
  if (state.locationPickerMarker?.setZIndexOffset) state.locationPickerMarker.setZIndexOffset(1000);
}

function renderRegionAlerts(geojson, loadFailed = false) {
  ensureRegionMap();
  if (!state.regionMap || !state.regionAlertsLayer) return;

  state.regionAlertsLayer.clearLayers();
  const features = geojson?.features || [];
  const emptyEl = document.getElementById(SEL.regionMapEmpty);
  updateRegionAlertStatus(features, loadFailed);

  if (features.length === 0) {
    if (emptyEl) emptyEl.hidden = false;
    state.regionMap.setView([state.userLocation.lat, state.userLocation.lon], 8);
    setTimeout(() => state.regionMap.invalidateSize(), 100);
    return;
  }

  if (emptyEl) emptyEl.hidden = true;

  const layer = L.geoJSON(geojson, {
    pointToLayer(_feature, latlng) {
      return L.circleMarker(latlng, {
        radius: 9,
        fillColor: getCssVar("--red") || "#f85149",
        color: "#fff",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.85,
      });
    },
    onEachFeature(feature, lyr) {
      const props = feature.properties || {};
      lyr.bindPopup(stormPopupHtml(props));
    },
  });
  layer.addTo(state.regionAlertsLayer);

  const bounds = layer.getBounds();
  if (bounds.isValid()) {
    state.regionMap.fitBounds(bounds.pad(0.25), { maxZoom: 10 });
  } else {
    state.regionMap.setView([state.userLocation.lat, state.userLocation.lon], 8);
  }
  setTimeout(() => state.regionMap.invalidateSize(), 100);
}

export async function loadRegionMap() {
  const coordsEl = document.getElementById(SEL.regionMapCoords);
  const txt = `${state.userLocation.lat.toFixed(4)}°, ${state.userLocation.lon.toFixed(4)}°`;
  if (coordsEl) coordsEl.textContent = txt;

  ensureRegionMap();
  if (state.regionMap) {
    state.regionMap.setView([state.userLocation.lat, state.userLocation.lon], state.regionMap.getZoom() || 8);
  }

  try {
    const bbox = locationBBox(state.userLocation.lat, state.userLocation.lon);
    const r = await map.overlay(bbox);
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    renderRegionAlerts(data);
  } catch {
    renderRegionAlerts({ type: "FeatureCollection", features: [] }, true);
  }
}

export function lazyInitRegionMap() {
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
