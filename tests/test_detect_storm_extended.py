"""Extended unit tests for detect_storm helpers."""

from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

import pytest

from app.application.cv.detect_storm import (
    DetectStormUseCase,
    _safe_torch_load,
    _yolov5_repo,
)


def test_yolov5_repo_local_when_hubconf_exists(monkeypatch, tmp_path):
    from app.application.cv import detect_storm as ds

    yolo_src = tmp_path / "yolov5_src"
    yolo_src.mkdir()
    (yolo_src / "hubconf.py").write_text("# stub")
    monkeypatch.setattr(ds, "_YOLOV5_SRC", yolo_src)

    repo, source = _yolov5_repo()
    assert source == "local"
    assert str(yolo_src) == repo


def test_yolov5_repo_github_fallback(monkeypatch):
    from app.application.cv import detect_storm as ds

    monkeypatch.setattr(ds, "_YOLOV5_SRC", pathlib.Path("/nonexistent/yolov5"))
    repo, source = _yolov5_repo()
    assert source == "github"
    assert repo == "ultralytics/yolov5"


def test_execute_rejects_path_traversal():
    repo = MagicMock()
    use_case = DetectStormUseCase(repo=repo)
    with pytest.raises(ValueError, match="path traversal"):
        use_case.execute(bucket="bkt", key="../etc/passwd")


def test_execute_no_detections_skips_persist(monkeypatch, tmp_path):
    repo = MagicMock()
    use_case = DetectStormUseCase(repo=repo)
    image = tmp_path / "img.jpg"
    image.write_bytes(b"x")

    with patch("boto3.client") as mock_boto:
        mock_boto.return_value.download_file = MagicMock()
        with patch("app.application.cv.detect_storm._ensure_model", return_value=tmp_path / "m.pt"):
            with patch("app.application.cv.detect_storm._run_yolo_inference", return_value=[]):
                result = use_case.execute(bucket="bkt", key="img.jpg")

    repo.save.assert_not_called()
    assert result["alert_sent"] is False
    assert result["detections"] == []


def test_cleanup_image_swallows_errors(monkeypatch, tmp_path):
    path = tmp_path / "img.jpg"
    path.write_bytes(b"x")

    def boom():
        raise OSError("permission denied")

    monkeypatch.setattr(pathlib.Path, "unlink", lambda self: boom())
    DetectStormUseCase._cleanup_image(path)


def test_safe_torch_load_fallback(monkeypatch, tmp_path):
    import torch

    weights = tmp_path / "model.pt"
    weights.write_bytes(b"data")

    calls = {"n": 0}

    def fake_load(path, weights_only=False):
        calls["n"] += 1
        if weights_only is False:
            raise RuntimeError("unsafe")
        return {"weights": True}

    monkeypatch.setattr(torch, "load", fake_load)
    loaded = _safe_torch_load(str(weights))
    assert loaded == {"weights": True}
    assert calls["n"] == 2
