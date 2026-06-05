/** Constantes imutáveis do dashboard (sem estado de runtime). */

export const LOC_KEY = "dashboard-location";
export const LOC_COLLAPSED_KEY = "dashboard-location-collapsed";
export const DEFAULT_LOC = { lat: -23.55, lon: -46.63 };
export const LOC_RADIUS_KM = 50;
export const MAP_APPLY_DEBOUNCE_MS = 400;
export const REGION_MAP_PAD = 2.5;

export const BRAZIL_CITIES = [
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
