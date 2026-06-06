"""Mocked tests for StormDetector without loading real YOLO weights."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.storm_detector import Detection, StormDetector


@pytest.fixture
def mock_yolo_model():
    pred = MagicMock()
    pred.tolist.return_value = [[10.0, 20.0, 50.0, 60.0, 0.92, 0.0]]
    results = MagicMock()
    results.pred = [pred]
    results.names = {0: "storm"}

    model = MagicMock(return_value=results)
    model.names = {0: "storm"}
    model.conf = 0.5
    return model


def test_storm_detector_init_uses_local_weights(mock_yolo_model, tmp_path, monkeypatch):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"fake")

    with patch("app.services.storm_detector.torch.hub.load", return_value=mock_yolo_model) as load:
        detector = StormDetector(model_path=str(weights), device="cpu")

    load.assert_called_once()
    assert detector.get_model_info()["framework"] == "YOLOv5"


def test_predict_returns_detections(mock_yolo_model, tmp_path, monkeypatch):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"fake")
    image = tmp_path / "img.png"
    image.write_bytes(b"not-a-real-png")

    fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
    with patch("app.services.storm_detector.torch.hub.load", return_value=mock_yolo_model):
        with patch("app.services.storm_detector.cv2.imread", return_value=fake_img):
            detector = StormDetector(model_path=str(weights), device="cpu")
            result = detector.predict(str(image))

    assert result.num_detections == 1
    assert result.has_storm is True
    assert result.detections[0].class_name == "storm"


def test_predict_missing_image_returns_empty(mock_yolo_model, tmp_path):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"fake")

    with patch("app.services.storm_detector.torch.hub.load", return_value=mock_yolo_model):
        with patch("app.services.storm_detector.cv2.imread", return_value=None):
            detector = StormDetector(model_path=str(weights), device="cpu")
            result = detector.predict(str(tmp_path / "missing.png"))

    assert result.num_detections == 0
    assert result.has_storm is False


def test_predict_batch(mock_yolo_model, tmp_path):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"fake")
    fake_img = np.zeros((50, 50, 3), dtype=np.uint8)

    with patch("app.services.storm_detector.torch.hub.load", return_value=mock_yolo_model):
        with patch("app.services.storm_detector.cv2.imread", return_value=fake_img):
            detector = StormDetector(model_path=str(weights), device="cpu")
            results = detector.predict_batch(["a.png", "b.png"])

    assert len(results) == 2


def test_predict_with_visualization(mock_yolo_model, tmp_path):
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"fake")
    image_path = tmp_path / "img.png"
    fake_img = np.zeros((80, 80, 3), dtype=np.uint8)

    with patch("app.services.storm_detector.torch.hub.load", return_value=mock_yolo_model):
        with patch("app.services.storm_detector.cv2.imread", return_value=fake_img):
            with patch("app.services.storm_detector.cv2.imwrite") as mock_write:
                detector = StormDetector(model_path=str(weights), device="cpu")
                result, vis = detector.predict_with_visualization(str(image_path), str(tmp_path / "out.png"))

    assert result.num_detections == 1
    assert vis.shape == fake_img.shape
    mock_write.assert_called_once()
