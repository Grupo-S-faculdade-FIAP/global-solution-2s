"""Lightweight unit tests for storm_detector dataclasses."""

from app.services.storm_detector import Detection, DetectionResult


def test_detection_dataclass():
    det = Detection(
        x=100.0, y=200.0, width=50.0, height=40.0,
        confidence=0.92, class_name="storm",
    )
    assert det.class_name == "storm"
    assert det.confidence == 0.92


def test_detection_result_dataclass():
    det = Detection(0, 0, 10, 10, 0.8, "storm")
    result = DetectionResult(
        image_path="/tmp/img.png",
        num_detections=1,
        detections=[det],
        has_storm=True,
        average_confidence=0.8,
        timestamp="2026-06-05T12:00:00Z",
    )
    assert result.has_storm is True
    assert result.num_detections == 1
    assert result.detections[0].confidence == 0.8
