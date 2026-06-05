"""Tests for DI container factories."""

import pytest

from app import container
from app.infrastructure.aws.dynamodb_iot import DynamoDBIoTReadingRepository
from app.infrastructure.aws.dynamodb_storm import DynamoDBStormAlertRepository
from app.infrastructure.persistence.json_iot_store import JsonIoTReadingRepository
from app.infrastructure.persistence.json_storm_store import JsonStormAlertRepository


def test_get_storm_repo_mock(monkeypatch):
    monkeypatch.setattr(container.settings, "DYNAMODB_USE_MOCK", True)
    repo = container.get_storm_repo()
    assert isinstance(repo, JsonStormAlertRepository)


def test_get_storm_repo_dynamodb(monkeypatch):
    monkeypatch.setattr(container.settings, "DYNAMODB_USE_MOCK", False)
    repo = container.get_storm_repo()
    assert isinstance(repo, DynamoDBStormAlertRepository)


def test_get_iot_repo_mock(monkeypatch):
    monkeypatch.setattr(container.settings, "IOT_USE_MOCK", True)
    repo = container.get_iot_repo()
    assert isinstance(repo, JsonIoTReadingRepository)


def test_get_iot_repo_dynamodb(monkeypatch):
    monkeypatch.setattr(container.settings, "IOT_USE_MOCK", False)
    repo = container.get_iot_repo()
    assert isinstance(repo, DynamoDBIoTReadingRepository)
