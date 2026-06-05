import { state } from "../core/state.js";
import { cityDisplayName } from "./cities.js";

function hideWindyLoadingSoon(ms = 12000) {
  const loading = document.getElementById("windy-loading");
  if (!loading || loading.hidden) return;
  setTimeout(() => {
    if (!loading.hidden) loading.hidden = true;
  }, ms);
}

function windyEmbedUrl(lat, lon) {
  const tpl = document.querySelector(".windy-frame")?.dataset.srcTemplate || "";
  return tpl.replace(/\{lat\}/g, String(lat)).replace(/\{lon\}/g, String(lon));
}

export function updateWindyLoadingText(lat, lon) {
  const el = document.getElementById("windy-loading-text");
  if (!el) return;
  const name = cityDisplayName(lat ?? state.userLocation.lat, lon ?? state.userLocation.lon);
  el.textContent = `Carregando radar para ${name}…`;
}

export function refreshWindyMap() {
  const iframe = document.getElementById("windy-iframe") || document.querySelector(".windy-frame");
  const loading = document.getElementById("windy-loading");
  if (!iframe) return;
  updateWindyLoadingText(state.userLocation.lat, state.userLocation.lon);
  if (loading) loading.hidden = false;
  iframe.onload = () => { if (loading) loading.hidden = true; };
  iframe.src = windyEmbedUrl(state.userLocation.lat, state.userLocation.lon);
  hideWindyLoadingSoon();
}

export function lazyLoadWindy() {
  const iframe = document.getElementById("windy-iframe") || document.querySelector(".windy-frame");
  if (!iframe) return;
  const loading = document.getElementById("windy-loading");
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting && !iframe.src) {
        if (loading) loading.hidden = false;
        iframe.onload = () => { if (loading) loading.hidden = true; };
        iframe.src = windyEmbedUrl(state.userLocation.lat, state.userLocation.lon);
        hideWindyLoadingSoon();
        observer.unobserve(iframe);
      }
    });
  }, { rootMargin: "100px" });
  observer.observe(iframe);
}
