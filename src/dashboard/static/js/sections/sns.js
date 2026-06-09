import { sns } from "../core/api/endpoints.js";
import { state } from "../core/state.js";

function setBadge(el, configured) {
  if (!el) return;
  el.classList.remove("sns-status-active", "sns-status-inactive", "sns-status-unknown");
  if (configured) {
    el.textContent = "SNS ativo";
    el.className = "sns-status-badge sns-status-active";
  } else {
    el.textContent = "SNS indisponível";
    el.className = "sns-status-badge sns-status-inactive";
  }
}

function setFeedback(message, isError = false) {
  const el = document.getElementById("sns-feedback");
  if (!el) return;
  el.textContent = message || "";
  el.classList.toggle("sns-feedback-error", Boolean(isError && message));
}

export async function loadSnsStatus() {
  const badge = document.getElementById("sns-status-badge");
  const hint = document.getElementById("sns-hint");
  const btn = document.getElementById("btn-sns-subscribe");
  try {
    const r = await sns.status();
    const data = await r.json();
    const configured = Boolean(data.configured);
    setBadge(badge, configured);
    if (hint) {
      hint.hidden = false;
      const maxSubs = data.max_subscribers ?? 20;
      const maxAlerts = data.max_alerts_per_email_day ?? 3;
      const radiusKm = data.alert_radius_km ?? 200;
      const baseHint =
        `Alertas apenas para tempestades dentro de ~${radiusKm} km da localização definida no mapa. ` +
        `Limite: até ${maxSubs} e-mails cadastrados e ${maxAlerts} alertas por e-mail por dia. ` +
        "A AWS envia um e-mail de confirmação após a inscrição. Só recebe alertas quem clicar em " +
        "Confirm subscription no e-mail da Amazon SNS.";
      if (!configured) {
        hint.textContent =
          "SNS não está configurado neste ambiente (defina SNS_TOPIC_ARN na Lambda). " +
          "A simulação de alerta continua funcionando no dashboard; o e-mail só é enviado na AWS.";
      } else {
        hint.textContent = baseHint;
      }
    }
    if (btn) btn.disabled = !configured;
  } catch {
    setBadge(badge, false);
    if (btn) btn.disabled = true;
  }
}

async function subscribeEmail() {
  const input = document.getElementById("sns-email");
  const btn = document.getElementById("btn-sns-subscribe");
  if (!input || !btn) return;

  const email = input.value.trim();
  if (!email) {
    setFeedback("Informe um e-mail válido.", true);
    return;
  }

  btn.disabled = true;
  setFeedback("Inscrevendo…");

  try {
    const r = await sns.subscribe({
      email,
      lat: state.userLocation.lat,
      lon: state.userLocation.lon,
    });
    const data = await r.json();
    if (data.success) {
      setFeedback(data.message || "Inscrição enviada — confirme o e-mail da AWS.");
    } else {
      setFeedback(data.error || "Não foi possível inscrever o e-mail.", true);
      btn.disabled = false;
    }
  } catch (err) {
    setFeedback("Erro: " + err.message, true);
    btn.disabled = false;
  }
}

export function bindSnsActions() {
  document.getElementById("btn-sns-subscribe")?.addEventListener("click", subscribeEmail);
}
