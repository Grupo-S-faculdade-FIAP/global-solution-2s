import { BRAZIL_CITIES } from "../core/state.js";

export function nearestCityId(lat, lon) {
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

export function cityDisplayName(lat, lon) {
  const id = nearestCityId(lat, lon);
  const city = BRAZIL_CITIES.find((c) => c.id === id);
  if (city && city.id !== "custom") return city.name;
  return "Local personalizado";
}
