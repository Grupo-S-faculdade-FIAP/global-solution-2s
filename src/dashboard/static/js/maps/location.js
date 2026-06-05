import {
  state,
  BRAZIL_CITIES,
  LOC_KEY,
  LOC_COLLAPSED_KEY,
  LOC_RADIUS_KM,
  MAP_APPLY_DEBOUNCE_MS,
} from "../core/state.js";
import { getCssVar } from "../core/css.js";
import { showToast } from "../core/ui.js";
import { mapTileConfig } from "./tiles.js";
import { cityDisplayName, nearestCityId } from "./cities.js";
import { refreshWindyMap } from "./windy.js";
import { reloadLocationDependentData } from "../sections/climate.js";

const applyBtnDefaultText = "Aplicar coordenadas";

export function updateLocationHeader(lat, lon) {
  const cityEl = document.getElementById("location-city-name");
  const label = document.getElementById("location-label");
  const txt = `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`;
  if (cityEl) cityEl.textContent = cityDisplayName(lat, lon);
  if (label) label.textContent = txt;
  const windyTitle = document.getElementById("windy-map-title");
  if (windyTitle) windyTitle.textContent = `Chuva em tempo real — ${cityDisplayName(lat, lon)}`;
  const loadingText = document.getElementById("windy-loading-text");
  if (loadingText) loadingText.textContent = `Carregando radar para ${cityDisplayName(lat, lon)}…`;
}

function setLocationLoading(loading) {
  state.locationReloading = loading;
  ["btn-geo", "btn-reset-sp", "btn-apply-location", "select-city"].forEach((id) => {
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
  if (!state.locationPickerMap || typeof L === "undefined") return;
  const blue = getCssVar("--blue") || "#58a6ff";
  if (state.locationPickerRadius) state.locationPickerMap.removeLayer(state.locationPickerRadius);
  state.locationPickerRadius = L.circle([lat, lon], {
    radius: LOC_RADIUS_KM * 1000,
    color: blue,
    weight: 1.5,
    opacity: 0.65,
    fillColor: blue,
    fillOpacity: 0.08,
    className: "location-picker-radius",
  }).addTo(state.locationPickerMap);
  if (state.locationPickerMarker) state.locationPickerMarker.bringToFront();
}

function scheduleMapAutoApply(lat, lon) {
  if (state.mapApplyTimer) clearTimeout(state.mapApplyTimer);
  state.mapApplyTimer = setTimeout(() => {
    applyLocationAndReload(lat, lon, { silent: false, collapseMobile: true, force: true });
  }, MAP_APPLY_DEBOUNCE_MS);
}

function syncCoordInputs(lat, lon) {
  const latEl = document.getElementById("input-lat");
  const lonEl = document.getElementById("input-lon");
  if (latEl) latEl.value = lat;
  if (lonEl) lonEl.value = lon;
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

export function setPickerCoords(lat, lon, fly = true) {
  syncCoordInputs(lat, lon);
  syncCitySelect(lat, lon);
  syncAdvancedAccordion(nearestCityId(lat, lon));
  updateLocationHeader(lat, lon);
  const sub = document.getElementById("weather-location-sub");
  if (sub) sub.textContent = `Coordenadas: ${lat.toFixed(4)}°, ${lon.toFixed(4)}°`;
  ensureLocationPickerMap();
  if (state.locationPickerMap && state.locationPickerMarker) {
    state.locationPickerMarker.setLatLng([lat, lon]);
    updateLocationPickerRadius(lat, lon);
    if (fly) state.locationPickerMap.setView([lat, lon], state.locationPickerMap.getZoom() || 8);
  }
}

export function ensureLocationPickerMap() {
  if (state.locationPickerMap || typeof L === "undefined") return;
  const el = document.getElementById("location-picker-map");
  if (!el) return;
  const cfg = mapTileConfig();
  state.locationPickerMap = L.map(el, { zoomControl: false, scrollWheelZoom: false });
  L.control.zoom({ position: "bottomright" }).addTo(state.locationPickerMap);
  L.tileLayer(cfg.url, { attribution: cfg.attribution, maxZoom: 18 }).addTo(state.locationPickerMap);
  state.locationPickerMarker = L.marker([state.userLocation.lat, state.userLocation.lon], { draggable: true }).addTo(state.locationPickerMap);
  state.locationPickerMap.setView([state.userLocation.lat, state.userLocation.lon], 8);
  state.locationPickerMap.on("click", (e) => {
    setPickerCoords(e.latlng.lat, e.latlng.lng, false);
    scheduleMapAutoApply(e.latlng.lat, e.latlng.lng);
  });
  state.locationPickerMarker.on("dragend", () => {
    const p = state.locationPickerMarker.getLatLng();
    setPickerCoords(p.lat, p.lng, false);
    scheduleMapAutoApply(p.lat, p.lng);
  });
  updateLocationPickerRadius(state.userLocation.lat, state.userLocation.lon);
  setTimeout(() => state.locationPickerMap.invalidateSize(), 150);
}

export function loadStoredLocation() {
  try {
    const raw = localStorage.getItem(LOC_KEY);
    if (raw) {
      const p = JSON.parse(raw);
      if (typeof p.lat === "number" && typeof p.lon === "number") {
        state.userLocation = { lat: p.lat, lon: p.lon };
      }
    }
  } catch { /* ignore */ }
  populateCitySelect();
  setPickerCoords(state.userLocation.lat, state.userLocation.lon, true);
}

function saveLocation(lat, lon) {
  state.userLocation = { lat, lon };
  localStorage.setItem(LOC_KEY, JSON.stringify(state.userLocation));
  setPickerCoords(lat, lon, true);
  refreshWindyMap();
}

export async function applyLocationAndReload(lat, lon, opts = {}) {
  const { silent = false, collapseMobile = false, force = false } = opts;
  if (state.locationReloading) {
    if (!silent) showToast("Aguarde — atualizando região…", "info");
    return;
  }
  const same =
    Math.abs(state.userLocation.lat - lat) < 0.0001 &&
    Math.abs(state.userLocation.lon - lon) < 0.0001;
  saveLocation(lat, lon);
  if (same && state.hasAppliedLocationOnce && !force) return;
  setLocationLoading(true);
  try {
    await reloadLocationDependentData();
    state.hasAppliedLocationOnce = true;
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
  if (wasCompact && !collapsed && state.locationPickerMap) {
    setTimeout(() => state.locationPickerMap.invalidateSize(), 200);
  }
}

function resetToSaoPaulo() {
  const sp = BRAZIL_CITIES.find((c) => c.id === "sp");
  if (!sp) return;
  applyLocationAndReload(sp.lat, sp.lon, { silent: false, force: true });
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
      applyLocationAndReload(pos.coords.latitude, pos.coords.longitude, { collapseMobile: true, force: true });
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

export function initLocationBarUX() {
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
      if (state.locationPickerMap) state.locationPickerMap.invalidateSize();
    });
    ro.observe(mapEl);
  }
}

export function bindLocationControls() {
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
