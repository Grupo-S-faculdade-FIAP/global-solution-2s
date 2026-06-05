import { state } from "../core/state.js";
import { fetchApi } from "../core/api.js";
import { clearKpiLoading } from "../core/dom.js";
import { noteResponseSource } from "../core/ui.js";
import {
  renderTrendChart,
  renderWeeklyChart,
  renderHourlyChart,
  renderHeatmapTable,
} from "../charts.js";

export async function loadKPIs() {
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
    kAvg.textContent = d.daily_avg;
    kDay.textContent = d.peak_day;
    kHour.textContent = d.peak_hour;
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

export async function loadTrend() {
  if (typeof Chart === "undefined") return;
  const r = await fetchApi("/api/alerts/daily");
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (!d || typeof d !== "object") throw new Error("empty");
  state.lastTrendData = d;
  renderTrendChart(d);
}

export async function loadWeekly() {
  if (typeof Chart === "undefined") return;
  const r = await fetchApi("/api/alerts/weekly");
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (!d || typeof d !== "object") throw new Error("empty");
  state.lastWeeklyData = d;
  renderWeeklyChart(d);
}

export async function loadHourly() {
  if (typeof Chart === "undefined") return;
  const r = await fetchApi("/api/alerts/hourly");
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (!d || typeof d !== "object") throw new Error("empty");
  state.lastHourlyData = d;
  renderHourlyChart(d);
}

export async function loadHeatmap() {
  const r = await fetchApi("/api/alerts/heatmap");
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const data = await r.json();
  if (!Array.isArray(data)) throw new Error("empty");
  state.lastHeatmapData = data;
  renderHeatmapTable(data);
}
