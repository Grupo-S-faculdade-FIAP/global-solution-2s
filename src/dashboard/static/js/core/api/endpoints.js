/** Contratos HTTP do BFF — único lugar com paths /api/*. */

import { fetchApi } from "../api.js";

export const dashboard = {
  config: () => fetchApi("/api/dashboard/config"),
};

export const alerts = {
  summary: () => fetchApi("/api/alerts/summary"),
  daily: () => fetchApi("/api/alerts/daily"),
  weekly: () => fetchApi("/api/alerts/weekly"),
  hourly: () => fetchApi("/api/alerts/hourly"),
  heatmap: () => fetchApi("/api/alerts/heatmap"),
  simulateDetection: (body) =>
    fetchApi("/api/alerts/simulate-detection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};

export const weather = {
  current: (lat, lon) =>
    fetchApi(`/api/weather/current?lat=${lat}&lon=${lon}`),
};

export const risk = {
  forecast: (lat, lon) =>
    fetchApi(`/api/risk/forecast?lat=${lat}&lon=${lon}`),
};

export const storms = {
  detectorStatus: () => fetchApi("/api/storms/detector-status"),
  recent: (hours = 168) => fetchApi(`/api/storms/recent?hours=${hours}`),
  detectSample: () => fetchApi("/api/storms/detect-sample", { method: "POST" }),
};

export const map = {
  overlay: (bbox) =>
    fetchApi(`/api/map/overlay?bbox=${encodeURIComponent(bbox)}`),
};

export const ml = {
  agriculturalRisk: ({ temperatura, umidade, precipitacao, vento_kmh }) =>
    fetchApi(
      `/api/ml/agricultural-risk?temperatura=${temperatura}&umidade=${umidade}&precipitacao=${precipitacao}&vento_kmh=${vento_kmh}`
    ),
};

export const iot = {
  latestReadings: (hours = 24) =>
    fetchApi(`/api/iot/readings/latest?hours=${hours}`),
};

export const nasa = {
  capturas: (limite = 12) => fetchApi(`/api/nasa/capturas?limite=${limite}`),
};
