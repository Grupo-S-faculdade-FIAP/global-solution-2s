import { fetchApi } from "../core/api.js";
import { clearIotLoading } from "../core/dom.js";
import { noteResponseSource } from "../core/ui.js";

export async function loadIoTReadings() {
  try {
    const resp = await fetchApi("/api/iot/readings/latest?hours=24");
    noteResponseSource(resp);
    const data = resp.ok ? await resp.json() : null;
    const readings = data?.readings ?? [];
    const latest = readings[0] ?? null;

    const chip = document.getElementById("iot-source-chip");
    const badge = document.getElementById("iot-status-badge");
    const storageLabel = document.getElementById("iot-storage-label");

    if (chip) { chip.hidden = false; chip.textContent = resp.ok ? "API" : "Demonstração"; }
    if (badge) {
      badge.textContent = resp.ok ? "Online" : "Demo";
      badge.className = "iot-status-badge " + (resp.ok ? "badge-ok" : "badge-demo");
    }
    if (storageLabel) storageLabel.textContent = data?.storage ?? "—";

    if (latest) {
      const fmt = (v, unit) => (v != null ? `${v}${unit}` : "—");
      const ts = latest.timestamp ? new Date(latest.timestamp).toLocaleString("pt-BR") : "—";
      document.getElementById("iot-temp").textContent = fmt(latest.temperatura, " °C");
      document.getElementById("iot-umid").textContent = fmt(latest.umidade, " %");
      document.getElementById("iot-cidade").textContent = latest.cidade ?? "—";
      document.getElementById("iot-ts").textContent = ts;
    } else {
      ["iot-temp", "iot-umid", "iot-cidade", "iot-ts"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.textContent = "—";
      });
    }
    clearIotLoading();

    if (readings.length > 1) {
      const wrap = document.getElementById("iot-history-wrap");
      const tbody = document.getElementById("iot-history-body");
      if (wrap && tbody) {
        tbody.innerHTML = readings.slice(0, 10).map((r) => {
          const ts = r.timestamp ? new Date(r.timestamp).toLocaleString("pt-BR") : "—";
          return `<tr><td>${ts}</td><td>${r.device_id ?? "—"}</td><td>${r.temperatura ?? "—"}</td><td>${r.umidade ?? "—"}</td><td>${r.cidade ?? "—"}</td></tr>`;
        }).join("");
        wrap.hidden = false;
      }
    }
  } catch (err) {
    console.warn("IoT: falha ao carregar leituras", err);
    clearIotLoading();
  }
}
