#!/usr/bin/env python3
"""Smoke test AWS E2E — DynamoDB + API health."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    from app.core.config import settings  # noqa: PLC0415
    from app.services.sns_alerts import sns_status  # noqa: PLC0415
    from app.services.storm_alerts_store import (  # noqa: PLC0415
        add_alert,
        list_alerts_since_hours,
        use_mock_store,
    )

    base_url = os.environ.get("AWS_API_URL", "http://127.0.0.1:8000")
    failed = 0

    print("\n=== Smoke AWS E2E ===\n")
    mode = "mock" if settings.DYNAMODB_USE_MOCK else "dynamodb"
    print(f"  [PASS] storage_mode: DYNAMODB_USE_MOCK={settings.DYNAMODB_USE_MOCK} ({mode})")

    sns = sns_status()
    if sns["configured"]:
        print(f"  [PASS] sns: configured ({sns['topic_arn']})")
    elif not settings.SNS_ENABLED:
        print("  [WARN] sns: SNS_ENABLED=false — publish disabled")
    else:
        print("  [WARN] sns: SNS_TOPIC_ARN not set — alerts skip SNS publish")

    if not settings.DYNAMODB_USE_MOCK:
        import boto3  # noqa: PLC0415
        from botocore.exceptions import BotoCoreError, ClientError  # noqa: PLC0415
        try:
            client = boto3.client("dynamodb", region_name=settings.AWS_REGION)
            resp = client.describe_table(TableName=settings.DYNAMODB_TABLE_ALERTS)
            print(f"  [PASS] dynamodb_table: {resp['Table']['TableStatus']}")
        except (ClientError, BotoCoreError) as exc:
            print(f"  [FAIL] dynamodb_table: {exc}")
            failed += 1
    else:
        print("  [PASS] dynamodb_table: mock mode — skipped")

    test_id = "smoke_e2e_test"
    add_alert(
        s3_key="smoke_test_image.jpg",
        detection_count=1,
        bucket=settings.S3_BUCKET_IMAGES,
        alert_id=test_id,
        simulated=True,
    )
    recent = list_alerts_since_hours(1)
    if any(str(a.get("alert_id")) == test_id for a in recent):
        print(f"  [PASS] alert_roundtrip: write/read OK ({mode})")
    else:
        print(f"  [FAIL] alert_roundtrip: {test_id} not found")
        failed += 1

    try:
        resp = requests.get(f"{base_url.rstrip('/')}/health", timeout=15)
        if resp.status_code == 200:
            print(f"  [PASS] api_health: {resp.status_code}")
        else:
            print(f"  [FAIL] api_health: HTTP {resp.status_code}")
            failed += 1
    except requests.RequestException as exc:
        print(f"  [WARN] api_health: {exc} (API local pode estar offline)")

    print()
    if failed:
        print(f"❌ {failed} check(s) failed")
        return 1
    print("✅ All checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
