from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = ""
    ENVIRONMENT: str = "development"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # AWS
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_IMAGES: str = "satellite-images-gs2"
    DYNAMODB_TABLE_IOT: str = "iot"
    DYNAMODB_TABLE_ALERTS: str = "alerts"
    SNS_TOPIC_ARN: str = ""

    # ML / CV
    YOLO_MODEL_PATH: str = "models/yolov8_storm.pt"  # kept for local use
    YOLO_MODEL_S3_KEY: str = "models/best.pt"        # S3 object key for the trained weights
    YOLO_CONFIDENCE_THRESHOLD: float = 0.1
    FIRMS_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
