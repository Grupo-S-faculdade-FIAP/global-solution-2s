import { state } from "../core/state.js";
import { alerts, dashboard } from "../core/api/endpoints.js";
import { clearKpiLoading } from "../core/dom.js";
import { SEL } from "../core/selectors.js";
import { noteResponseSource } from "../core/ui.js";
import {
  renderTrendChart,
  renderWeeklyChart,
  renderHourlyChart,
  renderHeatmapTable,
} from "../charts.js";

function renderKpis(d) {
  if (d?.total_30d == null) throw new Error("empty");
  const kTotal = document.getElementById(SEL.kpiTotal);
  const kAvg = document.getElementById(SEL.kpiAvg);
  const kDay = document.getElementById(SEL.kpiDay);
  const kHour = document.getElementById(SEL.kpiHour);
  if (!kTotal || !kAvg || !kDay || !kHour) return;
  kTotal.textContent = d.total_30d;
  kAvg.textContent = d.daily_avg;
  kDay.textContent = d.peak_day;
  kHour.textContent = d.peak_hour;
  clearKpiLoading();
}

function clearKpiValues() {
  clearKpiLoading();
  [SEL.kpiTotal, SEL.kpiAvg, SEL.kpiDay, SEL.kpiHour].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.textContent = "—";
  });
}

export async function loadAlertsBundle() {
  try {
    const r = await dashboard.summary();
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    renderKpis(d.kpis ?? d);
    if (typeof Chart !== "undefined") {
      if (d.trend_30_days) {
        state.lastTrendData = d.trend_30_days;
        renderTrendChart(d.trend_30_days);
      }
      if (d.alerts_by_weekday) {
        state.lastWeeklyData = d.alerts_by_weekday;
        renderWeeklyChart(d.alerts_by_weekday);
      }
      if (d.alerts_by_hour) {
        state.lastHourlyData = d.alerts_by_hour;
        renderHourlyChart(d.alerts_by_hour);
      }
    }
    if (Array.isArray(d.heatmap)) {
      state.lastHeatmapData = d.heatmap;
      renderHeatmapTable(d.heatmap);
    }
  } catch (err) {
    console.warn("Alerts bundle:", err);
    clearKpiValues();
    throw err;
  }
}

export async function loadKPIs() {
  try {
    const r = await alerts.summary();
    noteResponseSource(r);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    renderKpis(await r.json());
  } catch (err) {
    console.warn("KPIs:", err);
    clearKpiValues();
  }
}

export async function loadTrend() {
  if (typeof Chart === "undefined") return;
  const r = await alerts.daily();
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (!d || typeof d !== "object") throw new Error("empty");
  state.lastTrendData = d;
  renderTrendChart(d);
}

export async function loadWeekly() {
  if (typeof Chart === "undefined") return;
  const r = await alerts.weekly();
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (!d || typeof d !== "object") throw new Error("empty");
  state.lastWeeklyData = d;
  renderWeeklyChart(d);
}

export async function loadHourly() {
  if (typeof Chart === "undefined") return;
  const r = await alerts.hourly();
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const d = await r.json();
  if (!d || typeof d !== "object") throw new Error("empty");
  state.lastHourlyData = d;
  renderHourlyChart(d);
}

export async function loadHeatmap() {
  const r = await alerts.heatmap();
  noteResponseSource(r);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  const data = await r.json();
  if (!Array.isArray(data)) throw new Error("empty");
  state.lastHeatmapData = data;
  renderHeatmapTable(data);
}
