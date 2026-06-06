"""Unit tests for tracing helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core import tracing


def test_init_xray_disabled(monkeypatch):
    monkeypatch.setattr(tracing, "XRAY_ENABLED", False)
    tracing.init_xray()


def test_add_trace_metadata_disabled(monkeypatch):
    monkeypatch.setattr(tracing, "XRAY_ENABLED", False)
    tracing.add_trace_metadata("key", "value")


def test_start_subsegment_disabled(monkeypatch):
    monkeypatch.setattr(tracing, "XRAY_ENABLED", False)
    with tracing.start_subsegment("test-op") as ctx:
        assert ctx is not None


def test_wrap_lambda_handler_disabled(monkeypatch):
    monkeypatch.setattr(tracing, "XRAY_ENABLED", False)

    def handler(event, context):
        return {"ok": True}

    wrapped = tracing.wrap_lambda_handler(handler)
    assert wrapped({"x": 1}, None) == {"ok": True}


def test_init_xray_import_error(monkeypatch):
    monkeypatch.setattr(tracing, "XRAY_ENABLED", True)

    def fake_import(name, *args, **kwargs):
        if name == "aws_xray_sdk.core":
            raise ImportError("missing")
        return __import__(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        tracing.init_xray()


def test_add_trace_metadata_with_recorder(monkeypatch):
    monkeypatch.setattr(tracing, "XRAY_ENABLED", True)
    mock_segment = MagicMock()
    mock_recorder = MagicMock()
    mock_recorder.current_segment.return_value = mock_segment

    with patch.dict("sys.modules", {"aws_xray_sdk.core": MagicMock(xray_recorder=mock_recorder)}):
        tracing.add_trace_metadata("bucket", "test-bkt")
        mock_segment.put_metadata.assert_called_once_with("bucket", "test-bkt")


def test_wrap_lambda_handler_with_xray(monkeypatch):
    monkeypatch.setattr(tracing, "XRAY_ENABLED", True)
    mock_recorder = MagicMock()

    with patch.dict("sys.modules", {"aws_xray_sdk.core": MagicMock(xray_recorder=mock_recorder)}):
        def handler(event, context):
            return event

        wrapped = tracing.wrap_lambda_handler(handler)
        ctx = MagicMock(function_name="gs2-api")
        assert wrapped({"ping": 1}, ctx) == {"ping": 1}
        mock_recorder.begin_segment.assert_called_once()
        mock_recorder.end_segment.assert_called_once()
