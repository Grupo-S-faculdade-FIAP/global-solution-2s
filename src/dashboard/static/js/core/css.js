/** Leitura de variáveis CSS do tema ativo. */

export function getCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function getThemeColors() {
  return {
    text: getCssVar("--text-sec") || "#8b949e",
    border: getCssVar("--chart-grid") || "#21262d",
    blue: getCssVar("--blue") || "#58a6ff",
    green: getCssVar("--green") || "#3fb950",
  };
}

export function parseCssColorToRgb(cssColor) {
  const probe = document.createElement("span");
  probe.style.color = cssColor;
  document.body.appendChild(probe);
  const rgb = getComputedStyle(probe).color.match(/\d+/g);
  probe.remove();
  if (!rgb || rgb.length < 3) return [28, 35, 48];
  return rgb.slice(0, 3).map(Number);
}
