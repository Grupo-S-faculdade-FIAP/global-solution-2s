import { state } from "../core/state.js";
import { alerts, storms } from "../core/api/endpoints.js";
import { emit } from "../core/events.js";
import { noteResponseSource } from "../core/ui.js";

function setYOLOLoading(loading, text = "Carregando modelo YOLO…") {
  const box = document.getElementById("yolo-loading");
  const label = document.getElementById("yolo-loading-text");
  const status = document.getElementById("yolo-status");
  if (label) label.textContent = text;
  if (box) box.hidden = !loading;
  if (status) {
    status.setAttribute("aria-busy", loading ? "true" : "false");
    status.classList.toggle("is-loading", loading);
  }
}

function updateYoloSummary(stormsList) {
  const lastEl = document.getElementById("yolo-last-detection");
  const avgEl = document.getElementById("yolo-avg-confidence");
  if (!lastEl || !avgEl) return;

  if (!Array.isArray(stormsList) || stormsList.length === 0) {
    lastEl.textContent = "Sem alertas recentes";
    avgEl.textContent = "—";
    return;
  }

  const sorted = [...stormsList].sort((a, b) => {
    const at = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const bt = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    return bt - at;
  });
  const latest = sorted[0];
  const confidences = stormsList
    .map((item) => Number(item.confidence))
    .filter((value) => Number.isFinite(value));
  const avgConfidence = confidences.length
    ? confidences.reduce((sum, value) => sum + value, 0) / confidences.length
    : null;

  lastEl.textContent = latest.timestamp
    ? new Date(latest.timestamp).toLocaleString("pt-BR")
    : "Alerta recente";
  avgEl.textContent = avgConfidence === null ? "—" : `${Math.round(avgConfidence * 100)}%`;
}

export async function loadYOLOStatus() {
  const el = document.getElementById("yolo-status");
  if (el) {
    el.textContent = "Carregando modelo…";
    el.className = "yolo-stat-value risk-moderate is-loading";
  }
  setYOLOLoading(true);
  try {
    const r = await storms.detectorStatus();
    const data = await r.json();
    if (!el) return;
    if (data.available) {
      el.textContent = "Operacional";
      el.className = "yolo-stat-value risk-low";
    } else if (data.model_s3_key) {
      el.textContent = "Configurado via Lambda";
      el.className = "yolo-stat-value risk-low";
    } else if (data.model_exists) {
      el.textContent = "Modelo local presente";
      el.className = "yolo-stat-value risk-moderate";
    } else {
      el.textContent = "Sem best.pt";
      el.className = "yolo-stat-value risk-high";
    }
  } catch {
    if (el) {
      el.textContent = "Erro ao verificar";
      el.className = "yolo-stat-value risk-high";
    }
  } finally {
    setYOLOLoading(false);
  }
}

export async function loadRecentStorms() {
  const el = document.getElementById("storms-recent-list");
  if (!el) return;
  try {
    const r = await storms.recent(168);
    noteResponseSource(r);
    const stormsList = await r.json();
    if (!Array.isArray(stormsList) || stormsList.length === 0) {
      updateYoloSummary([]);
      el.innerHTML =
        '<div class="section-empty" style="padding:0.5rem 0;">' +
        '<i class="bi bi-cloud-slash" aria-hidden="true"></i>' +
        "Nenhum alerta no store local — clique em Simular alerta.</div>";
      return;
    }
    updateYoloSummary(stormsList);
    el.innerHTML = stormsList.slice(0, 8).map((s) => {
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
    const r = await storms.detectSample();
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
    const r = await alerts.simulateDetection({
      confidence: 0.85,
      lat: state.userLocation.lat,
      lon: state.userLocation.lon,
    });

    const data = await r.json();

    if (data.success) {
      status.textContent = data.message || "Alerta registrado!";
      document.getElementById("yolo-last-detection").textContent =
        new Date(data.alert.timestamp).toLocaleTimeString("pt-BR");
      document.getElementById("yolo-avg-confidence").textContent =
        `${(data.alert.confidence * 100).toFixed(0)}%`;
      loadRecentStorms();
      await emit("dashboard:reload", { scope: "post-storm-simulate" });

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
