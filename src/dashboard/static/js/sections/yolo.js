import { state } from "../core/state.js";
import { fetchApi } from "../core/api.js";
import { noteResponseSource } from "../core/ui.js";
import { loadKPIs, loadTrend, loadWeekly, loadHourly, loadHeatmap } from "./alerts.js";
import { loadRegionMap } from "../maps/region.js";

export async function loadYOLOStatus() {
  try {
    const r = await fetchApi("/api/storms/detector-status");
    const data = await r.json();
    const el = document.getElementById("yolo-status");
    if (!el) return;
    if (data.available) {
      el.textContent = "Operacional";
      el.className = "yolo-stat-value risk-low";
    } else if (data.model_exists) {
      el.textContent = "Modelo presente, detector não carregou";
      el.className = "yolo-stat-value risk-moderate";
    } else {
      el.textContent = "Sem best.pt";
      el.className = "yolo-stat-value risk-high";
    }
  } catch {
    const el = document.getElementById("yolo-status");
    if (el) {
      el.textContent = "Erro ao verificar";
      el.className = "yolo-stat-value risk-high";
    }
  }
}

export async function loadRecentStorms() {
  const el = document.getElementById("storms-recent-list");
  if (!el) return;
  try {
    const r = await fetchApi("/api/storms/recent?hours=168");
    noteResponseSource(r);
    const storms = await r.json();
    if (!Array.isArray(storms) || storms.length === 0) {
      el.innerHTML =
        '<div class="section-empty" style="padding:0.5rem 0;">' +
        '<i class="bi bi-cloud-slash" aria-hidden="true"></i>' +
        "Nenhum alerta no store local — clique em Simular alerta.</div>";
      return;
    }
    el.innerHTML = storms.slice(0, 8).map((s) => {
      const t = s.timestamp ? new Date(s.timestamp).toLocaleString("pt-BR") : "—";
      return `<div style="padding:4px 0;border-bottom:1px solid var(--border);">
        <strong>${(s.confidence * 100).toFixed(0)}%</strong> · ${t} · ${s.latitude?.toFixed(2)}, ${s.longitude?.toFixed(2)}
      </div>`;
    }).join("");
  } catch {
    el.textContent = "Lista de tempestades indisponível (API offline).";
  }
}

export async function detectSampleImage() {
  const btn = document.getElementById("btn-detect-sample");
  const status = document.getElementById("test-status");
  if (!btn || !status) return;
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
        data.num_detections > 0 ? `${(data.average_confidence * 100).toFixed(0)}%` : "—";
    } else {
      status.textContent = data.error || "Falha";
    }
  } catch (err) {
    status.textContent = err.message;
  }
  btn.disabled = false;
}

export async function testStormDetection() {
  const btn = document.getElementById("btn-test-detection");
  const status = document.getElementById("test-status");
  if (!btn || !status) return;

  btn.disabled = true;
  status.textContent = "Processando...";

  try {
    const r = await fetchApi("/api/alerts/simulate-detection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confidence: 0.85,
        lat: state.userLocation.lat,
        lon: state.userLocation.lon,
      }),
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

export function bindYoloActions() {
  document.getElementById("btn-test-detection")?.addEventListener("click", testStormDetection);
  document.getElementById("btn-detect-sample")?.addEventListener("click", detectSampleImage);
}
