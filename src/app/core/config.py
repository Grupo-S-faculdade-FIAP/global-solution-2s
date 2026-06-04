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

    # ─── CORS (hardcoded — works everywhere) ────────────────────────────
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:8000",
    ]

    # ─── AWS ──────────────────────────────────────────────────────────────
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    SNS_TOPIC_ARN: str = ""

    # ─── DynamoDB ─────────────────────────────────────────────────────────
    DYNAMODB_WEATHER_TABLE: str = "weather_metrics"
    DYNAMODB_STORM_TABLE: str = "storm_detections"
    DYNAMODB_RISK_TABLE: str = "risk_predictions"
    DYNAMODB_IOT_TABLE: str = "iot_readings"

    # ─── S3 ───────────────────────────────────────────────────────────────
    S3_BUCKET_MODELS: str = "model-artifacts"
    S3_BUCKET_IMAGES: str = "satellite-images-gs2"
    S3_BUCKET_OUTPUTS: str = "output-detections"

    # ─── Open-Meteo API ───────────────────────────────────────────────────
    OPENMETEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPENMETEO_TIMEZONE: str = "auto"

    # ─── Weather Ingestion (Lambda) ───────────────────────────────────────
    WEATHER_LOCATIONS: str = (
        "-23.5505,-46.6333,-22.9068,-43.1729,-15.8267,-47.8711,"
        "-30.0346,-51.2177,-9.9794,-49.8623"
    )
    WEATHER_RETENTION_DAYS: int = 90

    # ─── Computer Vision (YOLOv5) ──────────────────────────────────────────
    YOLO_MODEL_PATH: str = "s3://satellite-images-gs2/models/best.pt"
    YOLO_MODEL_S3_KEY: str = "models/best.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.4
    YOLO_INPUT_SIZE: int = 640
    YOLO_MODEL_RETENTION_DAYS: int = 30

    # ─── DynamoDB — Alertas (CV pipeline) ─────────────────────────────────
    DYNAMODB_TABLE_ALERTS: str = "alerts"
    DYNAMODB_USE_MOCK: bool = False
    DYNAMODB_MOCK_STORE_PATH: str = ""

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

# boto3 usa os.environ / cadeia padrão — espelha credenciais do .env carregado pelo Pydantic
import os  # noqa: E402

if settings.AWS_ACCESS_KEY_ID:
    os.environ.setdefault("AWS_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID)
if settings.AWS_SECRET_ACCESS_KEY:
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY)
if settings.AWS_REGION:
    os.environ.setdefault("AWS_DEFAULT_REGION", settings.AWS_REGION)
    os.environ.setdefault("AWS_REGION", settings.AWS_REGION)
