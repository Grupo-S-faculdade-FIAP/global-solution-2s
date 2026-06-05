import { state } from "../core/state.js";
import { dashboard } from "../core/api/endpoints.js";
import { noteResponseSource, setDataSourceChip } from "../core/ui.js";
import { SEL } from "../core/selectors.js";

export async function loadDashboardConfig() {
  try {
    const r = await dashboard.config();
    if (r.ok) {
      state.dashboardConfig = await r.json();
      noteResponseSource(r);
      if (state.dashboardConfig.storage === "dynamodb") setDataSourceChip("live");
    }
  } catch { /* defaults */ }
  if (!state.dashboardConfig.demo_mode) {
    const dev = document.getElementById(SEL.yoloDevActions);
    if (dev) dev.style.display = "none";
  }
}
