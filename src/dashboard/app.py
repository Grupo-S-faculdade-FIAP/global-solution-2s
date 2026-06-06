"""Dashboard Flask — HTML em /; rotas /api/* delegam a bff_handlers (espelhadas no FastAPI)."""

from flask import Flask, jsonify, render_template, request

from dashboard import bff_handlers as bff

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

DEMO_MODE = bff.DEMO_MODE
DEFAULT_WEATHER_LAT = bff.DEFAULT_WEATHER_LAT
DEFAULT_WEATHER_LON = bff.DEFAULT_WEATHER_LON
STORM_DETECTOR = bff.STORM_DETECTOR


def _json_response(data, data_source: str = "live", status: int = 200):
    resp = jsonify(data)
    resp.headers["X-Data-Source"] = data_source
    return resp, status


def _from_handler(result: tuple) -> tuple:
    data, source, status = result
    return _json_response(data, data_source=source, status=status)


@app.context_processor
def inject_dashboard_config():
    return {"demo_mode": DEMO_MODE}


@app.after_request
def set_cache_headers(response):
    if request.path.startswith("/api/"):
        if response.status_code == 200:
            response.cache_control.max_age = 300
            response.cache_control.public = True
        else:
            response.cache_control.no_store = True
            response.cache_control.max_age = 0
    elif request.path == "/":
        response.cache_control.max_age = 60
        response.cache_control.public = True
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard/config")
def dashboard_config():
    data, source, status = bff.dashboard_config()
    return _json_response(data, data_source=source, status=status)


@app.route("/api/alerts/weekly")
def alerts_weekly():
    days = request.args.get("days", default=30, type=int)
    return _from_handler(bff.alerts_weekly(days))


@app.route("/api/alerts/hourly")
def alerts_hourly():
    days = request.args.get("days", default=30, type=int)
    return _from_handler(bff.alerts_hourly(days))


@app.route("/api/alerts/daily")
def alerts_daily():
    days = request.args.get("days", default=30, type=int)
    return _from_handler(bff.alerts_daily(days))


@app.route("/api/alerts/heatmap")
def alerts_heatmap():
    days = request.args.get("days", default=30, type=int)
    return _from_handler(bff.alerts_heatmap(days))


@app.route("/api/alerts/summary")
def alerts_summary():
    days = request.args.get("days", default=30, type=int)
    return _from_handler(bff.alerts_summary(days))


@app.route("/api/dashboard/summary")
def dashboard_summary():
    days = request.args.get("days", default=30, type=int)
    return _from_handler(bff.dashboard_summary(days))


@app.route("/api/weather/current")
def weather_current():
    lat = request.args.get("lat", default=DEFAULT_WEATHER_LAT, type=float)
    lon = request.args.get("lon", default=DEFAULT_WEATHER_LON, type=float)
    return _from_handler(bff.weather_current(lat, lon))


@app.route("/api/risk/forecast")
def risk_forecast():
    lat = request.args.get("lat", default=DEFAULT_WEATHER_LAT, type=float)
    lon = request.args.get("lon", default=DEFAULT_WEATHER_LON, type=float)
    return _from_handler(bff.risk_forecast(lat, lon))


@app.route("/api/storms/recent")
def storms_recent():
    hours = request.args.get("hours", default=24, type=int)
    return _from_handler(bff.storms_recent(hours))


@app.route("/api/map/overlay")
def map_overlay():
    bbox = request.args.get("bbox", default="-25,-50,-20,-40")
    return _from_handler(bff.map_overlay(bbox))


@app.route("/api/storms/detect", methods=["POST"])
def detect_storm():
    return _from_handler(bff.detect_storm(request.get_json() or {}))


@app.route("/api/storms/batch-detect", methods=["POST"])
def batch_detect_storms():
    return _from_handler(bff.batch_detect_storms(request.get_json() or {}))


@app.route("/api/alerts/sns/status")
def sns_alerts_status():
    data, source, status = bff.sns_alerts_status()
    return _json_response(data, data_source=source, status=status)


@app.route("/api/alerts/subscribe", methods=["POST"])
def sns_subscribe():
    return _from_handler(bff.sns_subscribe(request.get_json() or {}))


@app.route("/api/alerts/simulate-detection", methods=["POST"])
def simulate_storm_detection():
    return _from_handler(bff.simulate_storm_detection(request.get_json() or {}))


@app.route("/api/ml/agricultural-risk")
def ml_agricultural_risk():
    return _from_handler(
        bff.ml_agricultural_risk(
            request.args.get("temperatura", 25.0, type=float),
            request.args.get("umidade", 60.0, type=float),
            request.args.get("precipitacao", 0.0, type=float),
            request.args.get("vento_kmh", 10.0, type=float),
        )
    )


@app.route("/api/nasa/capturas")
def nasa_capturas():
    limite = request.args.get("limite", 12, type=int)
    data, source, status = bff.nasa_capturas(limite)
    return _json_response(data, data_source=source, status=status)


@app.route("/api/storms/detector-status")
def detector_status():
    data, source, status = bff.detector_status()
    return _json_response(data, data_source=source, status=status)


@app.route("/api/storms/detect-sample", methods=["POST"])
def detect_storm_sample():
    return _from_handler(bff.detect_storm_sample())


@app.route("/api/cv/status")
def cv_status():
    data, source, status = bff.cv_status()
    return _json_response(data, data_source=source, status=status)


if __name__ == "__main__":
    print(
        "Aviso: use `make demo` (uvicorn :8000) — dashboard e API na mesma porta.",
        flush=True,
    )
    app.run(debug=True, host="127.0.0.1", port=5000)
