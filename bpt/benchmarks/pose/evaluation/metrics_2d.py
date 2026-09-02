"""Image-space 2D keypoint metrics with one fixed bbox-diagonal scale."""

from __future__ import annotations

import numpy as np


def bbox_diagonal(bboxes_xyxy: np.ndarray) -> np.ndarray:
    boxes = np.asarray(bboxes_xyxy, dtype=np.float64)
    if boxes.shape[-1] != 4:
        raise ValueError("bboxes must end in [x1,y1,x2,y2]")
    sizes = boxes[..., 2:4] - boxes[..., 0:2]
    return np.linalg.norm(sizes, axis=-1)


def bbox_from_keypoints(points: np.ndarray, valid: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool)
    if points.shape[:-1] != valid.shape:
        raise ValueError("keypoints and valid mask shapes differ")
    boxes = np.full((len(points), 4), np.nan, dtype=np.float64)
    for i, mask in enumerate(valid):
        if not np.any(mask):
            continue
        xy = points[i, mask, :2]
        boxes[i] = [xy[:, 0].min(), xy[:, 1].min(), xy[:, 0].max(), xy[:, 1].max()]
    return boxes


def evaluate_2d(
    prediction: np.ndarray,
    target: np.ndarray,
    valid: np.ndarray,
    bboxes_xyxy: np.ndarray,
    thresholds: tuple[float, ...] = (0.05, 0.10, 0.20),
    auc_max: float = 0.20,
) -> dict:
    pred = np.asarray(prediction, dtype=np.float64)[..., :2]
    gt = np.asarray(target, dtype=np.float64)[..., :2]
    mask = np.asarray(valid, dtype=bool).copy()
    if pred.shape != gt.shape or pred.shape[:-1] != mask.shape:
        raise ValueError("2D prediction, target and valid shapes differ")
    mask &= np.isfinite(pred).all(axis=-1) & np.isfinite(gt).all(axis=-1)
    scales = bbox_diagonal(bboxes_xyxy)
    usable_scale = np.isfinite(scales) & (scales > 0)
    mask &= usable_scale[:, None]
    error_px = np.linalg.norm(pred - gt, axis=-1)
    normalized = error_px / scales[:, None]
    flat_error = error_px[mask]
    flat_nme = normalized[mask]
    if flat_error.size == 0:
        raise ValueError("no valid 2D joints")
    pck = {f"pck_{threshold:.2f}": float(np.mean(flat_nme <= threshold)) for threshold in thresholds}
    grid = np.linspace(0.0, auc_max, 201)
    curve = np.asarray([np.mean(flat_nme <= threshold) for threshold in grid])
    trapezoid = getattr(np, "trapezoid", np.trapz)  # numpy<2 spells it trapz
    auc = float(trapezoid(curve, grid) / auc_max)
    per_joint = {}
    for joint in range(pred.shape[1]):
        use = mask[:, joint]
        if not np.any(use):
            continue
        values = normalized[use, joint]
        per_joint[joint] = {
            "count": int(use.sum()),
            "mean_pixel_error": float(error_px[use, joint].mean()),
            "nme": float(values.mean()),
            **{f"pck_{threshold:.2f}": float(np.mean(values <= threshold)) for threshold in thresholds},
        }
    return {
        "count": int(flat_error.size),
        "mean_pixel_error": float(flat_error.mean()),
        "median_pixel_error": float(np.median(flat_error)),
        "nme": float(flat_nme.mean()),
        **pck,
        "pck_auc_0.20": auc,
        "per_joint": per_joint,
        "error_px": error_px,
        "normalized_error": normalized,
        "valid": mask,
    }
