from pydantic_settings import BaseSettings


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
    
    # ─── DynamoDB ─────────────────────────────────────────────────────────
    DYNAMODB_WEATHER_TABLE: str = "weather_metrics"
    DYNAMODB_STORM_TABLE: str = "storm_detections"
    DYNAMODB_RISK_TABLE: str = "risk_predictions"
    DYNAMODB_IOT_TABLE: str = "iot_readings"
    
    # ─── S3 ───────────────────────────────────────────────────────────────
    S3_BUCKET_MODELS: str = "model-artifacts"
    S3_BUCKET_IMAGES: str = "input-images"
    S3_BUCKET_OUTPUTS: str = "output-detections"
    
    # ─── Open-Meteo API ───────────────────────────────────────────────────
    OPENMETEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    OPENMETEO_TIMEZONE: str = "auto"  # Auto-detect from coordinates
    
    # ─── Weather Ingestion (Lambda) ───────────────────────────────────────
    WEATHER_LOCATIONS: str = "-23.5505,-46.6333,-22.9068,-43.1729,-15.8267,-47.8711,-30.0346,-51.2177,-9.9794,-49.8623"
    # Format: lat1,lon1,lat2,lon2,...
    WEATHER_RETENTION_DAYS: int = 90
    
    # ─── Computer Vision (YOLOv5) ──────────────────────────────────────────
    YOLO_MODEL_PATH: str = "s3://model-artifacts/yolov5s-storm-best.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5
    YOLO_INPUT_SIZE: int = 640
    YOLO_MODEL_RETENTION_DAYS: int = 30
    
    # ─── Machine Learning (Risk Prediction) ────────────────────────────────
    ML_MODEL_PATH: str = "models/risk_predictor.pkl"
    ML_RISK_THRESHOLD_HIGH: float = 0.7
    ML_RISK_THRESHOLD_MEDIUM: float = 0.4
    
    # ─── Logging ──────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    
    # ─── External APIs ────────────────────────────────────────────────────
    WINDY_API_ENABLED: bool = True
    
    class Config:
        """Pydantic settings config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

