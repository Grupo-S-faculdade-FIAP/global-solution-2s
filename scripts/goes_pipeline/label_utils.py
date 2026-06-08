"""
Utilitários compartilhados do pipeline NASA → YOLO.

Garante que labels e imagens de treino compartilham o mesmo espaço de coordenadas
(letterbox 640×640), ignora chrome da UI do NASA Worldview e valida qualidade do dataset.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

YOLO_SIZE = 640
# v3.1: calibração para o ponto ideal — limpar ruído sem destruir sinal.
# area_min 150px² (era 300 — muito agressivo, jogou fora storm cells válidos)
# limiar 168 (era 170 — captura mais bordas de tempestade)
# merge_dist 0.08 no detect_storms (era 0.05 — merge só quando realmente próximos)
# Objetivo: ~4-6 bboxes/img (sweet spot entre 1.8 e 12.5)
DEFAULT_LIMIAR = 168
DEFAULT_AREA_PX = 150

# Margens onde o NASA Worldview deixa legenda / escala / timestamp
UI_MASK_X_FRAC = 0.18
UI_MASK_Y_FRAC = 0.12

# Fração mínima de pixels brilhantes dentro da bbox para aceitar o rótulo
MIN_BRIGHT_RATIO_IN_BBOX = 0.05

# Bboxes fantasma do pipeline corrompido (auditoria / migração)
KNOWN_GHOST_BBOXES: tuple[tuple[float, float, float, float], ...] = (
    (0.079687, 0.176852, 0.145833, 0.088889),
    (0.015885, 0.152778, 0.018229, 0.040741),
    (0.410417, 0.018056, 0.030208, 0.036111),
)

GHOST_TOLERANCE = 0.025

# Limites do quality gate (treino bloqueado se violados)
GATE_MAX_GHOST_FILE_RATIO = 0.05
GATE_MAX_DOMINANT_BBOX_RATIO = 0.08
GATE_MIN_NEGATIVE_RATIO = 0.05
GATE_MIN_POSITIVE_IMAGES = 5
GATE_MIN_BBOX_LINES = 10


@dataclass
class StormBbox:
    x_c: float
    y_c: float
    w: float
    h: float
    area_px: int = 0

    def as_yolo_line(self, class_id: int = 0) -> str:
        return f"{class_id} {self.x_c:.6f} {self.y_c:.6f} {self.w:.6f} {self.h:.6f}"

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.x_c, self.y_c, self.w, self.h)


@dataclass
class AuditReport:
    total_images: int = 0
    total_bbox_lines: int = 0
    unique_bbox_lines: int = 0
    ghost_file_count: int = 0
    ghost_bbox_line_count: int = 0
    dominant_bbox: str = ""
    dominant_bbox_count: int = 0
    empty_label_count: int = 0
    flags: list[dict[str, Any]] = field(default_factory=list)
    passed: bool = False
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_images": self.total_images,
            "total_bbox_lines": self.total_bbox_lines,
            "unique_bbox_lines": self.unique_bbox_lines,
            "ghost_file_count": self.ghost_file_count,
            "ghost_file_ratio": round(self.ghost_file_count / max(self.total_images, 1), 4),
            "ghost_bbox_line_count": self.ghost_bbox_line_count,
            "dominant_bbox": self.dominant_bbox,
            "dominant_bbox_count": self.dominant_bbox_count,
            "dominant_bbox_ratio": round(
                self.dominant_bbox_count / max(self.total_bbox_lines, 1), 4
            ),
            "empty_label_count": self.empty_label_count,
            "negative_ratio": round(self.empty_label_count / max(self.total_images, 1), 4),
            "passed": self.passed,
            "failures": self.failures,
            "flags": self.flags,
        }


def letterbox_resize(
    img: np.ndarray,
    new_shape: int = YOLO_SIZE,
    color: tuple[int, int, int] = (114, 114, 114),
) -> np.ndarray:
    """Redimensiona preservando aspect ratio com padding (padrão YOLOv5)."""
    h, w = img.shape[:2]
    r = min(new_shape / h, new_shape / w)
    new_unpad = (int(round(w * r)), int(round(h * r)))
    if (w, h) != new_unpad:
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)

    dw = new_shape - new_unpad[0]
    dh = new_shape - new_unpad[1]
    left = int(round(dw / 2 - 0.1))
    right = int(round(dw / 2 + 0.1))
    top = int(round(dh / 2 - 0.1))
    bottom = int(round(dh / 2 + 0.1))
    return cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)


def apply_ui_mask(
    gray: np.ndarray,
    mask_x_frac: float = UI_MASK_X_FRAC,
    mask_y_frac: float = UI_MASK_Y_FRAC,
) -> np.ndarray:
    """Zera regiões de chrome da UI antes do threshold."""
    masked = gray.copy()
    h, w = masked.shape
    masked[: int(h * mask_y_frac), :] = 0
    masked[:, : int(w * mask_x_frac)] = 0
    return masked


def bbox_bright_ratio(
    gray: np.ndarray,
    xc: float,
    yc: float,
    w: float,
    h: float,
    limiar: int,
) -> float:
    """Fração de pixels acima do limiar dentro da bbox normalizada."""
    H, W = gray.shape
    x1 = max(0, int((xc - w / 2) * W))
    y1 = max(0, int((yc - h / 2) * H))
    x2 = min(W, int((xc + w / 2) * W))
    y2 = min(H, int((yc + h / 2) * H))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    roi = gray[y1:y2, x1:x2]
    return float((roi > limiar).sum()) / roi.size


def is_ghost_bbox(
    xc: float,
    yc: float,
    w: float,
    h: float,
    tolerance: float = GHOST_TOLERANCE,
) -> bool:
    """Detecta bboxes do pipeline corrompido ou canto fixo da UI."""
    for gx, gy, gw, gh in KNOWN_GHOST_BBOXES:
        if (
            abs(xc - gx) <= tolerance
            and abs(yc - gy) <= tolerance
            and abs(w - gw) <= tolerance
            and abs(h - gh) <= tolerance
        ):
            return True
    # Canto superior esquerdo: centro em região de UI
    if xc < UI_MASK_X_FRAC and yc < UI_MASK_Y_FRAC + 0.08:
        return True
    return False


def merge_nearby_boxes(
    bboxes: list[StormBbox],
    iou_threshold: float = 0.3,
    distance_threshold: float = 0.05,
) -> list[StormBbox]:
    """
    Reduz over-segmentation unindo bboxes que se sobrepõem ou cujos centros
    estão próximos. Itera até estabilizar (sem mais merges possíveis).

    Args:
        iou_threshold: IoU mínimo para forçar merge.
        distance_threshold: distância máxima entre centros (coords normalizadas)
            para forçar merge mesmo sem sobreposição.
    """
    if len(bboxes) <= 1:
        return bboxes

    def to_xyxy(b: StormBbox) -> tuple[float, float, float, float]:
        return (b.x_c - b.w / 2, b.y_c - b.h / 2, b.x_c + b.w / 2, b.y_c + b.h / 2)

    def compute_iou(a: StormBbox, b: StormBbox) -> float:
        ax1, ay1, ax2, ay2 = to_xyxy(a)
        bx1, by1, bx2, by2 = to_xyxy(b)
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        if inter == 0.0:
            return 0.0
        union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
        return inter / union if union > 0 else 0.0

    def center_dist(a: StormBbox, b: StormBbox) -> float:
        return ((a.x_c - b.x_c) ** 2 + (a.y_c - b.y_c) ** 2) ** 0.5

    def merge_two(a: StormBbox, b: StormBbox) -> StormBbox:
        ax1, ay1, ax2, ay2 = to_xyxy(a)
        bx1, by1, bx2, by2 = to_xyxy(b)
        x1, y1 = min(ax1, bx1), min(ay1, by1)
        x2, y2 = max(ax2, bx2), max(ay2, by2)
        return StormBbox(
            x_c=(x1 + x2) / 2,
            y_c=(y1 + y2) / 2,
            w=x2 - x1,
            h=y2 - y1,
            area_px=a.area_px + b.area_px,
        )

    boxes = list(bboxes)
    changed = True
    while changed:
        changed = False
        new_boxes: list[StormBbox] = []
        absorbed = [False] * len(boxes)
        for i in range(len(boxes)):
            if absorbed[i]:
                continue
            current = boxes[i]
            for j in range(i + 1, len(boxes)):
                if absorbed[j]:
                    continue
                should_merge = (
                    compute_iou(current, boxes[j]) >= iou_threshold
                    or center_dist(current, boxes[j]) <= distance_threshold
                )
                if should_merge:
                    current = merge_two(current, boxes[j])
                    absorbed[j] = True
                    changed = True
            new_boxes.append(current)
        boxes = new_boxes

    return boxes


def detect_storms(
    img_bgr: np.ndarray,
    limiar: int = DEFAULT_LIMIAR,
    area_min: int = DEFAULT_AREA_PX,
    ui_mask_x: float = UI_MASK_X_FRAC,
    ui_mask_y: float = UI_MASK_Y_FRAC,
    min_bright_ratio: float = MIN_BRIGHT_RATIO_IN_BBOX,
    merge_iou: float = 0.3,
    merge_dist: float = 0.08,
) -> list[StormBbox]:
    """
    Detecta regiões convectivas (pixels frios/brilhantes) na imagem de treino.

    A detecção deve rodar na mesma imagem 640×640 que será usada no YOLO.
    v3.0: kernel 9×9, close 5×, merge_nearby_boxes para reduzir over-segmentation.
    """
    H, W = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = apply_ui_mask(gray, ui_mask_x, ui_mask_y)

    _, mascara = cv2.threshold(gray, limiar, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel, iterations=2)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel, iterations=5)

    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(mascara, connectivity=8)
    bboxes: list[StormBbox] = []

    for i in range(1, n_labels):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < area_min:
            continue

        x0 = int(stats[i, cv2.CC_STAT_LEFT])
        y0 = int(stats[i, cv2.CC_STAT_TOP])
        bw = int(stats[i, cv2.CC_STAT_WIDTH])
        bh = int(stats[i, cv2.CC_STAT_HEIGHT])

        x_c = (x0 + bw / 2) / W
        y_c = (y0 + bh / 2) / H
        w_n = bw / W
        h_n = bh / H

        if w_n > 0.90 or h_n > 0.90:
            continue
        if is_ghost_bbox(x_c, y_c, w_n, h_n):
            continue

        bright = bbox_bright_ratio(gray, x_c, y_c, w_n, h_n, limiar)
        if bright < min_bright_ratio:
            continue

        bboxes.append(StormBbox(x_c=x_c, y_c=y_c, w=w_n, h=h_n, area_px=area))

    return merge_nearby_boxes(bboxes, iou_threshold=merge_iou, distance_threshold=merge_dist)





def load_bboxes(lbl_path: Path) -> list[tuple[float, float, float, float]]:
    if not lbl_path.exists() or lbl_path.stat().st_size == 0:
        return []
    rows: list[tuple[float, float, float, float]] = []
    for line in lbl_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) >= 5:
            rows.append(tuple(map(float, parts[1:5])))
    return rows


def write_label_file(lbl_path: Path, bboxes: list[StormBbox]) -> None:
    lbl_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [bb.as_yolo_line() for bb in bboxes]
    lbl_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def audit_dataset(dataset_root: Path) -> AuditReport:
    """Audita qualidade dos labels; usado por 06_audit e gate de treino."""
    report = AuditReport()
    line_counter: Counter[str] = Counter()
    ghost_files: set[str] = set()

    for split in ("train", "val"):
        img_dir = dataset_root / "images" / split
        lbl_dir = dataset_root / "labels" / split
        if not img_dir.exists():
            continue

        for img_path in sorted(img_dir.glob("*.png")):
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            report.total_images += 1

            lines = []
            if lbl_path.exists():
                raw = lbl_path.read_text(encoding="utf-8").strip()
                lines = [ln for ln in raw.splitlines() if ln.strip()]

            if not lines:
                report.empty_label_count += 1

            file_has_ghost = False
            for line in lines:
                report.total_bbox_lines += 1
                line_counter[line] += 1
                parts = line.split()
                if len(parts) >= 5:
                    xc, yc, w, h = map(float, parts[1:5])
                    if is_ghost_bbox(xc, yc, w, h):
                        report.ghost_bbox_line_count += 1
                        file_has_ghost = True

            if file_has_ghost:
                ghost_files.add(img_path.name)
                report.flags.append({
                    "arquivo": img_path.name,
                    "split": split,
                    "motivos": ["bbox_fantasma"],
                })

    report.ghost_file_count = len(ghost_files)
    report.unique_bbox_lines = len(line_counter)
    if line_counter:
        report.dominant_bbox, report.dominant_bbox_count = line_counter.most_common(1)[0]

    positive_images = report.total_images - report.empty_label_count
    failures: list[str] = []
    n = max(report.total_images, 1)
    m = max(report.total_bbox_lines, 1)

    if report.total_bbox_lines < GATE_MIN_BBOX_LINES:
        failures.append(
            f"bbox_lines={report.total_bbox_lines} (<{GATE_MIN_BBOX_LINES})"
        )
    if positive_images < GATE_MIN_POSITIVE_IMAGES:
        failures.append(
            f"positive_images={positive_images} (<{GATE_MIN_POSITIVE_IMAGES})"
        )
    if report.ghost_file_count / n > GATE_MAX_GHOST_FILE_RATIO:
        failures.append(
            f"ghost_files={report.ghost_file_count}/{report.total_images} "
            f"(>{GATE_MAX_GHOST_FILE_RATIO:.0%})"
        )
    if report.dominant_bbox_count / m > GATE_MAX_DOMINANT_BBOX_RATIO:
        failures.append(
            f"dominant_bbox={report.dominant_bbox_count}/{report.total_bbox_lines} "
            f"(>{GATE_MAX_DOMINANT_BBOX_RATIO:.0%})"
        )
    if report.empty_label_count / n < GATE_MIN_NEGATIVE_RATIO:
        failures.append(
            f"negatives={report.empty_label_count}/{report.total_images} "
            f"(<{GATE_MIN_NEGATIVE_RATIO:.0%})"
        )

    report.failures = failures
    report.passed = len(failures) == 0
    return report


def save_audit_report(report: AuditReport, out_path: Path) -> dict[str, Any]:
    data = report.to_dict()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


def format_audit_summary(data: dict[str, Any]) -> str:
    status = "PASSED" if data["passed"] else "FAILED"
    lines = [
        f"Label quality audit: {status}",
        f"  Images       : {data['total_images']}",
        f"  Bbox lines   : {data['total_bbox_lines']} ({data['unique_bbox_lines']} unique)",
        f"  Ghost files  : {data['ghost_file_count']} ({data['ghost_file_ratio']:.1%})",
        f"  Negatives    : {data['empty_label_count']} ({data['negative_ratio']:.1%})",
    ]
    if data["dominant_bbox"]:
        lines.append(
            f"  Top bbox     : {data['dominant_bbox_count']}x "
            f"({data['dominant_bbox_ratio']:.1%})"
        )
    if data["failures"]:
        lines.append("  Failures:")
        for f in data["failures"]:
            lines.append(f"    - {f}")
    return "\n".join(lines)
