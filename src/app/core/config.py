from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# src/app/core/config.py → repo root
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILES = (
    _PROJECT_ROOT / ".env",
    _PROJECT_ROOT / "src" / ".env",
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ─── Project ──────────────────────────────────────────────────────────
    PROJECT_NAME: str = "Global Solutions — Environmental Intelligence"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = True

    # ─── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ─── CORS (dinâmico via variáveis ambiente) ───────────────────────────
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:8000",
    ]
    # CORS_EXTRA_ORIGINS: "https://example.com,https://api.example.com"
    # será mesclado com ALLOWED_ORIGINS se definido

    # ─── AWS (usa IAM roles em Lambda, não credenciais em ambiente) ───────
    AWS_REGION: str = "us-east-1"
    # AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY NÃO devem ser definidos aqui.
    # Lambda usa IAM execution role; dev local pode usar ~/.aws/credentials
    SNS_TOPIC_ARN: str = ""
    SNS_ENABLED: bool = True
    SNS_ALERT_SUBJECT: str = "Rain Alert — Storm Detected"
    SNS_MAX_SUBSCRIBERS: int = 20
    SNS_MAX_ALERTS_PER_EMAIL_DAY: int = 3
    SNS_REGION_COOLDOWN_MINUTES: int = 60
    SNS_ALERT_RADIUS_KM: float = 200.0
    SNS_RATE_LIMIT_STORE_PATH: str = ""
    SNS_REGION_COOLDOWN_STORE_PATH: str = ""
    SNS_SUBSCRIBER_STORE_PATH: str = ""
    # Amazon SES — entrega por e-mail com filtro geo/rate limit por destinatário.
    # Quando vazio, alertas usam sns.publish(TopicArn) (todos os inscritos confirmados recebem).
    SES_FROM_EMAIL: str = ""
    SES_ENABLED: bool = True

    # ─── DynamoDB ─────────────────────────────────────────────────────────
    DYNAMODB_WEATHER_TABLE: str = "weather_metrics"
    DYNAMODB_STORM_TABLE: str = "storm_detections"
    DYNAMODB_RISK_TABLE: str = "risk_predictions"
    DYNAMODB_IOT_TABLE: str = "iot_readings"

    # ─── S3 ───────────────────────────────────────────────────────────────
    S3_BUCKET_MODELS: str = "model-artifacts"
    S3_BUCKET_IMAGES: str = "satellite-images-gs2"
    S3_BUCKET_OUTPUTS: str = "output-detections"

    # ─── INMET (BDMEP / estações automáticas) ─────────────────────────────
    INMET_CACHE_PATH: str = "data/weather/inmet/training_cache.csv"
    INMET_TRAINING_YEARS: str = "2024"

    # ─── Open-Meteo API ───────────────────────────────────────────────────
    OPENMETEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPENMETEO_TIMEZONE: str = "auto"
    # Limite horário para APIs externas sem token (dev local); Lambda isenta
    EXTERNAL_API_RATE_LIMIT_ENABLED: bool = True
    EXTERNAL_API_RATE_LIMIT_PER_HOUR: int = 20
    EXTERNAL_API_RATE_LIMIT_STORE_PATH: str = ""

    # ─── Weather Ingestion (Lambda) ───────────────────────────────────────
    WEATHER_LOCATIONS: str = (
        "-23.5505,-46.6333,-22.9068,-43.1729,-15.8267,-47.8711,"
        "-30.0346,-51.2177,-9.9794,-49.8623"
    )
    WEATHER_RETENTION_DAYS: int = 90

    # ─── Computer Vision (YOLOv5) ──────────────────────────────────────────
    YOLO_MODEL_PATH: str = "s3://satellite-images-gs2/models/best.pt"
    YOLO_MODEL_S3_KEY: str = "models/best.pt"
    # Operating point: conf=0.55 → P=73.5% (storm70-l-tiled val)
    YOLO_CONFIDENCE_THRESHOLD: float = 0.55
    YOLO_IOU_THRESHOLD: float = 0.45
    YOLO_INPUT_SIZE: int = 640
    YOLO_MODEL_RETENTION_DAYS: int = 30
    YOLO_MODEL_VERSION: str = "1.0.0"  # Versão semantica
    MODEL_VERSIONS_REGISTRY_PATH: str = "~/.cache/model_versions.json"

    # ─── DynamoDB — Alertas (CV pipeline) ─────────────────────────────────
    DYNAMODB_TABLE_ALERTS: str = "alerts"
    DYNAMODB_TABLE_SNS_RATE_LIMIT: str = "sns_rate_limits"
    # Apenas CI/testes locais sem AWS (não expor em produção/UI).
    DYNAMODB_USE_MOCK: bool = False
    DYNAMODB_MOCK_STORE_PATH: str = ""

    # ─── IoT (ESP32) ───────────────────────────────────────────────────────
    # true = leituras simuladas (sem ESP32/DynamoDB iot_readings); false = AWS real
    IOT_USE_MOCK: bool = True

    # ─── Machine Learning (Risk Prediction) ────────────────────────────────
    ML_MODEL_PATH: str = "models/risk_predictor.pkl"
    ML_RISK_THRESHOLD_HIGH: float = 0.7
    ML_RISK_THRESHOLD_MEDIUM: float = 0.4

    # ─── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ─── External APIs ────────────────────────────────────────────────────
    WINDY_API_ENABLED: bool = True

    # ─── Dashboard ────────────────────────────────────────────────────────
    DEMO_MODE: bool = True

    # ─── NASA Worldview (GOES-East IR C13) ────────────────────────────────
    NASA_CAPTURE_ENABLED: bool = True
    NASA_CAPTURES_DIR: str = "data/nasa_captures"
    NASA_KEEP_LOCAL: bool = False
    NASA_HISTORICO_DIAS: int = 30
    NASA_S3_PREFIX: str = "nasa-satellite"
    # Prefixo que dispara Lambda S3 (somente .jpg no bucket de produção)
    NASA_CV_S3_PREFIX: str = "screenshots"

    model_config = SettingsConfigDict(
        env_file=tuple(str(p) for p in _ENV_FILES if p.exists()) or (str(_ENV_FILES[0]),),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()


def get_allowed_origins() -> list[str]:
    """Retorna lista de origens CORS, incluindo extras do ambiente se definidas."""
    import os  # noqa: E402

    origins = list(settings.ALLOWED_ORIGINS)
    extra_origins = os.environ.get("CORS_EXTRA_ORIGINS", "")
    if extra_origins:
        extra_list = [o.strip() for o in extra_origins.split(",") if o.strip()]
        origins.extend(extra_list)
    return origins
