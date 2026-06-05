"""Testes do pipeline de labels NASA → YOLO."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

_GOES = Path(__file__).resolve().parents[1] / "scripts" / "goes_pipeline"
if str(_GOES) not in sys.path:
    sys.path.insert(0, str(_GOES))

from label_utils import (  # noqa: E402
    audit_dataset,
    detect_storms,
    is_ghost_bbox,
    letterbox_resize,
    write_label_file,
    load_bboxes,
    StormBbox,
)


def test_is_ghost_bbox_detects_known_artifact():
    assert is_ghost_bbox(0.079687, 0.176852, 0.145833, 0.088889)
    assert not is_ghost_bbox(0.5, 0.5, 0.1, 0.1)


def test_letterbox_preserves_aspect_ratio():
    img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    out = letterbox_resize(img, new_shape=640)
    assert out.shape == (640, 640, 3)


def test_detect_storms_on_synthetic_bright_blob():
    img = np.zeros((640, 640, 3), dtype=np.uint8)
    cv2.rectangle(img, (300, 300), (380, 360), (255, 255, 255), -1)
    bboxes = detect_storms(img, limiar=200, area_min=50)
    assert len(bboxes) >= 1
    assert not is_ghost_bbox(*bboxes[0].as_tuple())


def test_audit_dataset_flags_ghost_labels(tmp_path: Path):
    img_dir = tmp_path / "images" / "train"
    lbl_dir = tmp_path / "labels" / "train"
    img_dir.mkdir(parents=True)
    lbl_dir.mkdir(parents=True)

    cv2.imwrite(str(img_dir / "nasa_test.png"), np.zeros((64, 64, 3), dtype=np.uint8))
    write_label_file(
        lbl_dir / "nasa_test.txt",
        [StormBbox(0.079687, 0.176852, 0.145833, 0.088889)],
    )

    report = audit_dataset(tmp_path)
    assert report.ghost_file_count == 1
    assert not report.passed


def test_write_and_load_roundtrip(tmp_path: Path):
    lbl = tmp_path / "sample.txt"
    boxes = [StormBbox(0.5, 0.5, 0.2, 0.1)]
    write_label_file(lbl, boxes)
    loaded = load_bboxes(lbl)
    assert len(loaded) == 1
    assert loaded[0] == pytest.approx((0.5, 0.5, 0.2, 0.1))
