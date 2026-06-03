import random
import requests
import sys
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ─── FastAPI Backend Configuration ────────────────────────────────────────────
FASTAPI_BASE_URL = "http://localhost:8000"
DEFAULT_WEATHER_LAT = -23.55  # São Paulo
DEFAULT_WEATHER_LON = -46.63

# ─── YOLO Storm Detector Configuration ────────────────────────────────────────
# Tentar importar o detector de tempestades
STORM_DETECTOR = None
try:
    # Adicionar src ao path para importar módulos da app
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.services.storm_detector import StormDetector
    
    # Caminho do modelo YOLO (usar modelo padrão se existir)
    YOLO_MODEL_PATH = "src/models/weights/best.pt"
    if Path(YOLO_MODEL_PATH).exists():
        STORM_DETECTOR = StormDetector(
            model_path=YOLO_MODEL_PATH,
            confidence_threshold=0.5,
            device="cpu"
        )
        print(f"✅ Storm Detector carregado: {YOLO_MODEL_PATH}")
    else:
        print(f"⚠️  Modelo YOLO não encontrado em {YOLO_MODEL_PATH}")
except Exception as e:
    print(f"⚠️  Storm Detector não disponível: {e}")
    STORM_DETECTOR = None

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


# ─── Proxy Routes to FastAPI Backend ─────────────────────────────────────────
@app.route("/api/weather/current")
def weather_current():
    """
    Proxy to FastAPI /weather/current endpoint.
    Returns current weather data for specified location.
    """
    try:
        lat = request.args.get("lat", default=DEFAULT_WEATHER_LAT, type=float)
        lon = request.args.get("lon", default=DEFAULT_WEATHER_LON, type=float)
        
        response = requests.get(
            f"{FASTAPI_BASE_URL}/weather/current",
            params={"lat": lat, "lon": lon},
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to fetch weather data"}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Backend connection error: {str(e)}"}), 503


@app.route("/api/risk/forecast")
def risk_forecast():
    """
    Proxy to FastAPI /risk/forecast endpoint.
    Returns risk score, category, and recommendations.
    """
    try:
        lat = request.args.get("lat", default=DEFAULT_WEATHER_LAT, type=float)
        lon = request.args.get("lon", default=DEFAULT_WEATHER_LON, type=float)
        
        response = requests.get(
            f"{FASTAPI_BASE_URL}/risk/forecast",
            params={"lat": lat, "lon": lon},
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to fetch risk forecast"}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Backend connection error: {str(e)}"}), 503


@app.route("/api/storms/recent")
def storms_recent():
    """
    Proxy to FastAPI /storms/recent endpoint.
    Returns recent storm detections.
    """
    try:
        hours = request.args.get("hours", default=24, type=int)
        
        response = requests.get(
            f"{FASTAPI_BASE_URL}/storms/recent",
            params={"hours": hours},
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to fetch storm data"}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Backend connection error: {str(e)}"}), 503


@app.route("/api/map/overlay")
def map_overlay():
    """
    Proxy to FastAPI /map/overlay endpoint.
    Returns GeoJSON features for map overlay.
    """
    try:
        bbox = request.args.get("bbox", default="-25,-50,-20,-40")
        
        response = requests.get(
            f"{FASTAPI_BASE_URL}/map/overlay",
            params={"bbox": bbox},
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "Failed to fetch map overlay"}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Backend connection error: {str(e)}"}), 503


# ─── YOLO Storm Detection Endpoints ────────────────────────────────────────────
@app.route("/api/storms/detect", methods=["POST"])
def detect_storm():
    """
    Detecta tempestades em uma imagem usando YOLO.
    
    Body (JSON):
      - image_url: URL ou caminho local da imagem
      - save_visualization: Se deve salvar imagem com bounding boxes (opcional, default: false)
    
    Returns:
        {
          "success": bool,
          "num_detections": int,
          "detections": [...],
          "has_storm": bool,
          "average_confidence": float,
          "message": str
        }
    """
    if not STORM_DETECTOR:
        return jsonify({
            "success": False,
            "error": "Storm Detector não está disponível. Treine o modelo primeiro.",
            "message": "Modelo YOLO não encontrado"
        }), 503

    try:
        data = request.get_json() or {}
        image_url = data.get("image_url")
        
        if not image_url:
            return jsonify({
                "success": False,
                "error": "Campo obrigatório 'image_url' não fornecido"
            }), 400
        
        # Fazer predição
        result = STORM_DETECTOR.predict(image_url)
        
        return jsonify({
            "success": True,
            "num_detections": result.num_detections,
            "detections": [
                {
                    "x": d.x,
                    "y": d.y,
                    "width": d.width,
                    "height": d.height,
                    "confidence": d.confidence,
                    "class_name": d.class_name
                }
                for d in result.detections
            ],
            "has_storm": result.has_storm,
            "average_confidence": result.average_confidence,
            "timestamp": result.timestamp,
            "message": f"Detectadas {result.num_detections} tempestades" if result.has_storm else "Nenhuma tempestade detectada"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/storms/batch-detect", methods=["POST"])
def batch_detect_storms():
    """
    Detecta tempestades em múltiplas imagens.
    
    Body (JSON):
      - image_urls: Lista de URLs/caminhos de imagens
    
    Returns:
        Lista de resultados de detecção
    """
    if not STORM_DETECTOR:
        return jsonify({
            "success": False,
            "error": "Storm Detector não está disponível"
        }), 503

    try:
        data = request.get_json() or {}
        image_urls = data.get("image_urls", [])
        
        if not image_urls:
            return jsonify({
                "success": False,
                "error": "Campo obrigatório 'image_urls' não fornecido"
            }), 400
        
        results = STORM_DETECTOR.predict_batch(image_urls)
        
        return jsonify({
            "success": True,
            "total_images": len(results),
            "total_detections": sum(r.num_detections for r in results),
            "images_with_storm": sum(1 for r in results if r.has_storm),
            "results": [
                {
                    "image_path": r.image_path,
                    "num_detections": r.num_detections,
                    "has_storm": r.has_storm,
                    "average_confidence": r.average_confidence,
                    "timestamp": r.timestamp
                }
                for r in results
            ]
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/alerts/simulate-detection", methods=["POST"])
def simulate_storm_detection():
    """
    Simula uma detecção de tempestade e gera um alerta.
    Útil para testes quando não há modelo treinado ou sem imagens disponíveis.
    
    Body (JSON, opcional):
      - confidence: Confiança da detecção simulada (0-1), default: 0.85
      - lat: Latitude, default: -23.55 (São Paulo)
      - lon: Longitude, default: -46.63
    
    Returns:
        Alerta gerado com timestamp
    """
    try:
        data = request.get_json() or {}
        confidence = data.get("confidence", 0.85)
        lat = data.get("lat", -23.55)
        lon = data.get("lon", -46.63)
        
        # Adicionar alerta simulado ao histórico de alertas
        alert = {
            "id": f"alert_{datetime.now().timestamp()}",
            "type": "storm_detection",
            "confidence": confidence,
            "latitude": lat,
            "longitude": lon,
            "timestamp": datetime.now().isoformat(),
            "message": f"Tempestade detectada com confiança {confidence:.1%}",
            "simulated": True
        }
        
        return jsonify({
            "success": True,
            "alert": alert,
            "message": "Alerta de tempestade simulado com sucesso"
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)

