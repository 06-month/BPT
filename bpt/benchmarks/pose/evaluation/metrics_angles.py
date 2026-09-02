"""Fixed H36M17 angle definitions for posture-oriented evaluation."""

from __future__ import annotations

import numpy as np


H36M_ANGLES = {
    "left_elbow": (11, 12, 13),
    "right_elbow": (14, 15, 16),
    "left_knee": (4, 5, 6),
    "right_knee": (1, 2, 3),
    "left_hip": (8, 4, 5),
    "right_hip": (8, 1, 2),
    "left_shoulder": (12, 11, 8),
    "right_shoulder": (15, 14, 8),
}


def angle_degrees(a: np.ndarray, vertex: np.ndarray, c: np.ndarray) -> np.ndarray:
    first, second = a - vertex, c - vertex
    denom = np.linalg.norm(first, axis=-1) * np.linalg.norm(second, axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        cosine = np.sum(first * second, axis=-1) / denom
    return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))


def evaluate_angles(prediction: np.ndarray, target: np.ndarray, valid: np.ndarray) -> dict:
    pred, gt = np.asarray(prediction, dtype=np.float64), np.asarray(target, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool)
    result = {}
    all_errors = []
    for name, (a, b, c) in H36M_ANGLES.items():
        usable = mask[:, a] & mask[:, b] & mask[:, c]
        pred_angle = angle_degrees(pred[:, a], pred[:, b], pred[:, c])
        gt_angle = angle_degrees(gt[:, a], gt[:, b], gt[:, c])
        usable &= np.isfinite(pred_angle) & np.isfinite(gt_angle)
        error = np.abs(pred_angle[usable] - gt_angle[usable])
        result[name] = {
            "count": int(error.size),
            "mean": float(error.mean()) if error.size else float("nan"),
            "median": float(np.median(error)) if error.size else float("nan"),
            "p90": float(np.percentile(error, 90)) if error.size else float("nan"),
        }
        all_errors.extend(error.tolist())
    values = np.asarray(all_errors)
    return {
        "mae_degrees": float(values.mean()) if values.size else float("nan"),
        "per_angle": result,
    }
