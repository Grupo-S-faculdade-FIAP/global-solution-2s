import { emit } from "./core/events.js";
import { getThemeColors } from "./core/css.js";
import { SEL } from "./core/selectors.js";

export const THEME_KEY = "dashboard-theme";

export function resolveInitialTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "dark" || saved === "light") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function updateMetaThemeColor(theme) {
  const meta = document.getElementById(SEL.metaThemeColor);
  if (meta) meta.content = theme === "dark" ? "#0d1117" : "#ffffff";
}

function updateThemeIcon(theme) {
  const btn = document.getElementById(SEL.themeToggle);
  if (!btn) return;
  const isDark = theme === "dark";
  btn.innerHTML = isDark
    ? '<i class="bi bi-sun-fill" aria-hidden="true"></i>'
    : '<i class="bi bi-moon-stars-fill" aria-hidden="true"></i>';
  btn.setAttribute("aria-pressed", String(isDark));
  btn.setAttribute("aria-label", isDark ? "Ativar modo claro" : "Ativar modo escuro");
  btn.title = isDark ? "Modo escuro — clique para claro" : "Modo claro — clique para escuro";
}

function updateThemeLabel(theme) {
  const label = document.getElementById(SEL.themeModeLabel);
  if (label) label.textContent = theme === "dark" ? "Escuro" : "Claro";
}

export function applyTheme(theme) {
  if (theme !== "dark" && theme !== "light") theme = "dark";
  const html = document.documentElement;
  html.setAttribute("data-theme", theme);
  html.classList.remove("theme-dark", "theme-light");
  html.classList.add(theme === "dark" ? "theme-dark" : "theme-light");
  html.style.colorScheme = theme;
  localStorage.setItem(THEME_KEY, theme);
  updateMetaThemeColor(theme);
  updateThemeIcon(theme);
  updateThemeLabel(theme);
  emit("theme:changed", { theme });
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(current === "dark" ? "light" : "dark");
}

export function initTheme() {
  applyTheme(resolveInitialTheme());
  const btn = document.getElementById(SEL.themeToggle);
  if (btn && !btn.dataset.bound) {
    btn.dataset.bound = "1";
    btn.addEventListener("click", toggleTheme);
  }
}

/** Inicializa Chart.js com cores do tema (chamado no bootstrap). */
export function initChartDefaults() {
  if (typeof Chart === "undefined") return;
  const colors = getThemeColors();
  Chart.defaults.color = colors.text;
  Chart.defaults.borderColor = colors.border;
  Chart.defaults.font.family =
    "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
}
