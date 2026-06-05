import { state } from "./core/state.js";
import { getCssVar, getThemeColors, parseCssColorToRgb } from "./core/css.js";

export { getThemeColors };

export function updateChartDefaults() {
  if (typeof Chart === "undefined") return;
  const colors = getThemeColors();
  Chart.defaults.color = colors.text;
  Chart.defaults.borderColor = colors.border;
}

function baseScaleOptions(c) {
  return {
    x: { ticks: { color: c.text }, grid: { color: c.border } },
    y: { beginAtZero: true, ticks: { color: c.text }, grid: { color: c.border } },
  };
}

export function renderTrendChart(d) {
  if (typeof Chart === "undefined" || !d) return;
  const c = getThemeColors();
  if (state.trendChartInstance) state.trendChartInstance.destroy();
  state.trendChartInstance = new Chart(document.getElementById("trendChart"), {
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
      scales: baseScaleOptions(c),
    },
  });
}

export function renderWeeklyChart(d) {
  if (typeof Chart === "undefined" || !d) return;
  const c = getThemeColors();
  if (state.weeklyChartInstance) state.weeklyChartInstance.destroy();
  state.weeklyChartInstance = new Chart(document.getElementById("weeklyChart"), {
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
      scales: baseScaleOptions(c),
    },
  });
}

export function renderHourlyChart(d) {
  if (typeof Chart === "undefined" || !d) return;
  const c = getThemeColors();
  if (state.hourlyChartInstance) state.hourlyChartInstance.destroy();
  state.hourlyChartInstance = new Chart(document.getElementById("hourlyChart"), {
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

export function refreshAllCharts() {
  if (state.lastTrendData) renderTrendChart(state.lastTrendData);
  if (state.lastWeeklyData) renderWeeklyChart(state.lastWeeklyData);
  if (state.lastHourlyData) renderHourlyChart(state.lastHourlyData);
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

export function refreshHeatmapColors() {
  if (!state.lastHeatmapData) return;
  document.querySelectorAll("#heatmap-table tbody td:not(.hm-day)").forEach((td) => {
    const m = td.dataset.v;
    const v = m != null ? Number(m) : 0;
    td.style.background = heatmapCellColor(v, state.lastHeatmapMax);
  });
}

export function renderHeatmapTable(data) {
  const DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
  const HOURS = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, "0")}h`);

  const map = {};
  data.forEach(({ x, y, v }) => { map[`${y}-${x}`] = v; });
  state.lastHeatmapMax = Math.max(...data.map((d) => d.v), 1);

  const thead = document.querySelector("#heatmap-table thead tr");
  const tbody = document.querySelector("#heatmap-table tbody");
  if (!thead || !tbody) return;

  thead.innerHTML = "<th></th>";
  HOURS.forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h.replace("h", "");
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
      const v = map[`${dy}-${hx}`] ?? 0;
      const td = document.createElement("td");
      td.dataset.v = String(v);
      td.style.background = heatmapCellColor(v, state.lastHeatmapMax);
      td.title = `${day} ${HOURS[hx]}: ${v} alerta(s)`;
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });
}
