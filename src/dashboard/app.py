import random
from datetime import datetime, timedelta

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ─── Cache middleware ─────────────────────────────────────────────────────────
@app.after_request
def set_cache_headers(response):
    """Add cache headers to API responses."""
    if request.path.startswith("/api/"):
        # Cache JSON API responses for 5 minutes
        response.cache_control.max_age = 300
        response.cache_control.public = True
    elif request.path == "/":
        # HTML: cache for 1 minute
        response.cache_control.max_age = 60
        response.cache_control.public = True
    return response

# ─── Seed para reprodutibilidade ──────────────────────────────────────────────
random.seed(42)

# ─── Distribuição base por dia da semana ─────────────────────────────────────
WEEKLY_ALERTS = {
    "Segunda": 5,
    "Terça": 12,
    "Quarta": 8,
    "Quinta": 15,
    "Sexta": 10,
    "Sábado": 4,
    "Domingo": 3,
}

# ─── Distribuição base por hora (pico convectivo 14h–16h) ────────────────────
HOURLY_ALERTS = {
    "00h": 1, "01h": 0, "02h": 1, "03h": 0, "04h": 0,
    "05h": 1, "06h": 2, "07h": 3, "08h": 4, "09h": 5,
    "10h": 4, "11h": 6, "12h": 7, "13h": 9, "14h": 14,
    "15h": 16, "16h": 13, "17h": 10, "18h": 8, "19h": 6,
    "20h": 5, "21h": 4, "22h": 3, "23h": 2,
}

# ─── Tendência 30 dias (simulação realista) ───────────────────────────────────
_base_date = datetime(2026, 5, 3)
_weekday_mult = [0.6, 1.2, 0.9, 1.5, 1.1, 0.5, 0.4]  # Seg–Dom
DAILY_TREND = {}
for _i in range(30):
    _day = _base_date + timedelta(days=_i)
    _base_val = 10 * _weekday_mult[_day.weekday()]
    DAILY_TREND[_day.strftime("%d/%m")] = max(0, round(random.gauss(_base_val, 2), 0))

# ─── Heatmap: dia da semana (0=Seg) × hora → contagem ────────────────────────
_hour_vals = list(HOURLY_ALERTS.values())
HEATMAP = []
for _d in range(7):
    for _h in range(24):
        _val = max(0, int(round(_hour_vals[_h] * _weekday_mult[_d] + random.gauss(0, 0.4))))
        HEATMAP.append({"x": _h, "y": _d, "v": _val})

# ─── KPIs ─────────────────────────────────────────────────────────────────────
_total = int(sum(DAILY_TREND.values()))
_peak_day = max(WEEKLY_ALERTS, key=lambda k: WEEKLY_ALERTS[k])
_peak_hour = max(HOURLY_ALERTS, key=lambda k: HOURLY_ALERTS[k])
SUMMARY = {
    "total_30d": _total,
    "daily_avg": round(_total / 30, 1),
    "peak_day": _peak_day,
    "peak_hour": _peak_hour,
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/alerts/weekly")
def alerts_weekly():
    """Distribuição de alertas por dia da semana."""
    return jsonify(WEEKLY_ALERTS)


@app.route("/api/alerts/hourly")
def alerts_hourly():
    """Distribuição de alertas por hora do dia."""
    return jsonify(HOURLY_ALERTS)


@app.route("/api/alerts/daily")
def alerts_daily():
    """Tendência diária dos últimos 30 dias."""
    return jsonify(DAILY_TREND)


@app.route("/api/alerts/heatmap")
def alerts_heatmap():
    """Heatmap dia-da-semana × hora."""
    return jsonify(HEATMAP)


@app.route("/api/alerts/summary")
def alerts_summary():
    """KPIs consolidados."""
    return jsonify(SUMMARY)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

