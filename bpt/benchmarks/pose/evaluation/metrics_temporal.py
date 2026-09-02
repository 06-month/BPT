"""Temporal derivative errors for correctly corresponding frames."""

from __future__ import annotations

import numpy as np


def evaluate_temporal(
    prediction: np.ndarray,
    target: np.ndarray,
    valid: np.ndarray,
    fps: float | None = None,
) -> dict:
    pred, gt = np.asarray(prediction, dtype=np.float64), np.asarray(target, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool)
    factor = float(fps) if fps is not None else 1.0
    velocity_pred, velocity_gt = np.diff(pred, axis=0) * factor, np.diff(gt, axis=0) * factor
    velocity_valid = mask[1:] & mask[:-1]
    velocity_error = np.linalg.norm(velocity_pred - velocity_gt, axis=-1)
    velocity_values = velocity_error[velocity_valid & np.isfinite(velocity_error)]
    acceleration_pred, acceleration_gt = np.diff(velocity_pred, axis=0) * factor, np.diff(velocity_gt, axis=0) * factor
    acceleration_valid = velocity_valid[1:] & velocity_valid[:-1]
    acceleration_error = np.linalg.norm(acceleration_pred - acceleration_gt, axis=-1)
    acceleration_values = acceleration_error[acceleration_valid & np.isfinite(acceleration_error)]
    return {
        "mpjve": float(velocity_values.mean()) if velocity_values.size else float("nan"),
        "acceleration_error": float(acceleration_values.mean()) if acceleration_values.size else float("nan"),
        "time_basis": "per_second" if fps is not None else "per_frame",
        "fps": fps,
        "velocity_count": int(velocity_values.size),
        "acceleration_count": int(acceleration_values.size),
    }
