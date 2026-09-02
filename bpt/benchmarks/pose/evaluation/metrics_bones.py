"""Bone-length accuracy and within-sequence consistency metrics."""

from __future__ import annotations

import numpy as np


H36M_BONES = {
    "pelvis_left_hip": (0, 4),
    "pelvis_right_hip": (0, 1),
    "left_hip_knee": (4, 5),
    "left_knee_ankle": (5, 6),
    "right_hip_knee": (1, 2),
    "right_knee_ankle": (2, 3),
    "left_shoulder_elbow": (11, 12),
    "left_elbow_wrist": (12, 13),
    "right_shoulder_elbow": (14, 15),
    "right_elbow_wrist": (15, 16),
}


def evaluate_bones(prediction: np.ndarray, target: np.ndarray, valid: np.ndarray) -> dict:
    pred, gt = np.asarray(prediction, dtype=np.float64), np.asarray(target, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool)
    per_bone = {}
    absolute_all, relative_all = [], []
    for name, (start, end) in H36M_BONES.items():
        usable = mask[:, start] & mask[:, end]
        pred_length = np.linalg.norm(pred[:, end] - pred[:, start], axis=-1)
        gt_length = np.linalg.norm(gt[:, end] - gt[:, start], axis=-1)
        usable &= np.isfinite(pred_length) & np.isfinite(gt_length) & (gt_length > 0)
        absolute = np.abs(pred_length[usable] - gt_length[usable])
        relative = absolute / gt_length[usable]
        per_bone[name] = {
            "count": int(absolute.size),
            "absolute_error": float(absolute.mean()) if absolute.size else float("nan"),
            "relative_error": float(relative.mean()) if relative.size else float("nan"),
            "prediction_variance": float(np.var(pred_length[usable])) if absolute.size else float("nan"),
            "prediction_cv": _coefficient_of_variation(pred_length[usable]),
        }
        absolute_all.extend(absolute.tolist())
        relative_all.extend(relative.tolist())
    absolute_values, relative_values = np.asarray(absolute_all), np.asarray(relative_all)
    variances = [v["prediction_variance"] for v in per_bone.values() if np.isfinite(v["prediction_variance"])]
    return {
        "absolute_bone_length_error": float(absolute_values.mean()) if absolute_values.size else float("nan"),
        "relative_bone_length_error": float(relative_values.mean()) if relative_values.size else float("nan"),
        "bone_length_variance": float(np.mean(variances)) if variances else float("nan"),
        "per_bone": per_bone,
    }


def _coefficient_of_variation(values: np.ndarray) -> float:
    if values.size == 0 or np.mean(values) == 0:
        return float("nan")
    return float(np.std(values) / np.mean(values))
