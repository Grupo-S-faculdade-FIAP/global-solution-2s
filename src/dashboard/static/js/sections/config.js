import { state } from "../core/state.js";
import { fetchApi } from "../core/api.js";
import { noteResponseSource, setDataSourceChip } from "../core/ui.js";

export async function loadDashboardConfig() {
  try {
    const r = await fetchApi("/api/dashboard/config");
    if (r.ok) {
      state.dashboardConfig = await r.json();
      noteResponseSource(r);
      if (state.dashboardConfig.storage === "dynamodb") setDataSourceChip("live");
    }
  } catch { /* defaults */ }
  if (!state.dashboardConfig.demo_mode) {
    const dev = document.getElementById("yolo-dev-actions");
    if (dev) dev.style.display = "none";
  }
}
