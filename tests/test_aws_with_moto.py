"""Integration tests using moto for AWS services (DynamoDB, S3, SNS).

Testa pipeline completo sem chamar AWS real.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_dynamodb, mock_s3, mock_sns

from app.application.cv.detect_storm import DetectStormUseCase
from app.infrastructure.aws.dynamodb_storm import DynamoDBStormAlertRepository


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials."""
    import os
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
@mock_dynamodb
def dynamodb_table(aws_credentials):
    """Cria tabela DynamoDB mock."""
    import boto3
    from app.core.config import settings

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName=settings.DYNAMODB_TABLE_ALERTS,
        KeySchema=[
            {"AttributeName": "alert_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "alert_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    yield table


@pytest.fixture
@mock_s3
def s3_bucket(aws_credentials):
    """Cria bucket S3 mock."""
    import boto3
    from app.core.config import settings

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=settings.S3_BUCKET_IMAGES)
    s3.put_object(
        Bucket=settings.S3_BUCKET_IMAGES,
        Key=settings.YOLO_MODEL_S3_KEY,
        Body=b"fake model weights",
    )
    yield s3


@pytest.fixture
@mock_sns
def sns_topic(aws_credentials):
    """Cria tópico SNS mock."""
    import boto3
    from app.core.config import settings

    sns = boto3.client("sns", region_name="us-east-1")
    response = sns.create_topic(Name="storm-alerts")
    settings.SNS_TOPIC_ARN = response["TopicArn"]
    yield sns


@mock_dynamodb
def test_dynamodb_save_with_moto(aws_credentials, dynamodb_table):
    """Testa salvar alerta em DynamoDB mock."""
    from app.core.config import settings

    repo = DynamoDBStormAlertRepository()
    result = repo.save(
        s3_key="screenshots/storm_001.jpg",
        detection_count=2,
        bucket="satellite-images",
        alert_id="storm_abc123",
        simulated=False,
        classes=["storm", "cloud"],
        confidence=0.92,
    )

    assert result["alert_id"] == "storm_abc123"
    assert result["detection_count"] == 2
    assert result["confidence"] == 0.92
    assert "_duplicate" not in result


@mock_dynamodb
def test_dynamodb_duplicate_detection(aws_credentials, dynamodb_table):
    """Testa deduplicação por alert_id."""
    from app.core.config import settings

    repo = DynamoDBStormAlertRepository()

    # Primeiro save
    result1 = repo.save(
        s3_key="screenshots/storm_001.jpg",
        detection_count=2,
        bucket="satellite-images",
        alert_id="storm_unique",
        simulated=False,
        classes=["storm"],
        confidence=0.9,
    )
    assert "_duplicate" not in result1

    # Segundo save com mesmo alert_id
    result2 = repo.save(
        s3_key="screenshots/storm_002.jpg",
        detection_count=1,
        bucket="satellite-images",
        alert_id="storm_unique",
        simulated=False,
        classes=["storm"],
        confidence=0.85,
    )
    assert result2.get("_duplicate") is True


@mock_dynamodb
def test_validation_rejects_path_traversal(aws_credentials):
    """Testa rejeição de path traversal."""
    repo = DynamoDBStormAlertRepository()

    with pytest.raises(ValueError, match="path traversal"):
        repo.save(
            s3_key="../../../etc/passwd",
            detection_count=1,
            bucket="images",
            alert_id="bad",
        )

    with pytest.raises(ValueError, match="path traversal"):
        repo.save(
            s3_key="image.jpg",
            detection_count=1,
            bucket="../../../etc/passwd",
            alert_id="bad",
        )


@mock_dynamodb
def test_validation_rejects_control_chars(aws_credentials):
    """Testa rejeição de control characters."""
    repo = DynamoDBStormAlertRepository()

    with pytest.raises(ValueError, match="control characters"):
        repo.save(
            s3_key="image\n.jpg",
            detection_count=1,
            bucket="images",
            alert_id="bad",
        )


@mock_s3
@mock_dynamodb
@mock_sns
def test_detect_storm_use_case_e2e(aws_credentials, s3_bucket, dynamodb_table, sns_topic):
    """Testa pipeline completo com moto."""
    import boto3
    import tempfile
    import pathlib
    from app.core.config import settings

    # Setup
    repo = DynamoDBStormAlertRepository()
    use_case = DetectStormUseCase(repo=repo)

    # Criar imagem fake temporária
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"fake image data")
        tmp_path = tmp.name

    # Upload fake image para S3 mock
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(
        Bucket=settings.S3_BUCKET_IMAGES,
        Key="screenshots/test_storm.jpg",
        Body=b"fake satellite image",
    )

    try:
        # Mock YOLO inference
        with patch("app.application.cv.detect_storm._run_yolo_inference") as mock_yolo, \
             patch("app.application.cv.detect_storm._ensure_model") as mock_model, \
             patch("app.services.sns_alerts.publish_storm_alert") as mock_sns:

            mock_yolo.return_value = [
                {"class": "storm", "confidence": 0.95, "bbox": [10, 20, 100, 200]},
            ]
            mock_model.return_value = pathlib.Path("/tmp/model.pt")
            mock_sns.return_value = "msg-12345"

            # Executar use case
            result = use_case.execute(
                bucket=settings.S3_BUCKET_IMAGES,
                key="screenshots/test_storm.jpg",
            )

        # Assertions
        assert result["bucket"] == settings.S3_BUCKET_IMAGES
        assert result["key"] == "screenshots/test_storm.jpg"
        assert result["alert_sent"] is True
        assert result["duplicate"] is False
        assert result["sns_message_id"] == "msg-12345"
        assert len(result["detections"]) == 1
        assert result["detections"][0]["class"] == "storm"
    finally:
        # Cleanup
        import os
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@mock_dynamodb
def test_detect_storm_path_traversal_rejection(aws_credentials):
    """Testa rejeição de path traversal no use case."""
    from app.application.cv.detect_storm import DetectStormUseCase

    repo = DynamoDBStormAlertRepository()
    use_case = DetectStormUseCase(repo=repo)

    with pytest.raises(ValueError, match="path traversal"):
        use_case.execute(bucket="images", key="../../../etc/passwd")
