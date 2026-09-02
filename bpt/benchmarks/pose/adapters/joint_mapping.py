"""Explicit joint contracts for M0 and supported datasets."""

from __future__ import annotations

import numpy as np

from pose_feedback.body.motionagformer_adapter import (
    coco17_to_motionagformer_h36m17,
    normalize_motionagformer_2d,
)


COCO17_NAMES = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

H36M17_NAMES = (
    "pelvis",
    "right_hip",
    "right_knee",
    "right_ankle",
    "left_hip",
    "left_knee",
    "left_ankle",
    "spine",
    "thorax",
    "neck",
    "head",
    "left_shoulder",
    "left_elbow",
    "left_wrist",
    "right_shoulder",
    "right_elbow",
    "right_wrist",
)

DIRECT_BODY_NAMES = (
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

COCO_DIRECT_BODY_INDICES = np.asarray(
    [COCO17_NAMES.index(name) for name in DIRECT_BODY_NAMES], dtype=np.int64
)
H36M_DIRECT_BODY_INDICES = np.asarray(
    [H36M17_NAMES.index(name) for name in DIRECT_BODY_NAMES], dtype=np.int64
)

# Fit3D's official 25-joint skeleton starts with these H36M17 joints. The
# remaining eight joints are toes/heels and are outside M0's output contract.
FIT3D25_TO_H36M17 = np.arange(17, dtype=np.int64)


def coco17_to_h36m17_input(coco17: np.ndarray, width: int, height: int) -> np.ndarray:
    """Apply the production adapter and MotionAGFormer screen normalization."""

    coco17 = np.asarray(coco17, dtype=np.float32)
    if coco17.shape != (17, 3):
        raise ValueError(f"expected COCO17 [17,3], got {coco17.shape}")
    xy, confidence = coco17_to_motionagformer_h36m17(coco17)
    normalized_xy = normalize_motionagformer_2d(xy, width, height)
    return np.concatenate((normalized_xy, confidence[:, None]), axis=-1).astype(np.float32)


def h36m17_pixels_to_motion_input(
    points: np.ndarray,
    width: int,
    height: int,
    confidence: np.ndarray | None = None,
) -> np.ndarray:
    """Build an oracle MotionAGFormer input from native H36M image points."""

    points = np.asarray(points, dtype=np.float32)
    if points.shape != (17, 2):
        raise ValueError(f"expected H36M17 [17,2], got {points.shape}")
    normalized = normalize_motionagformer_2d(points, width, height)
    if confidence is None:
        confidence = np.ones(17, dtype=np.float32)
    confidence = np.asarray(confidence, dtype=np.float32)
    if confidence.shape != (17,):
        raise ValueError(f"expected confidence [17], got {confidence.shape}")
    return np.concatenate((normalized, confidence[:, None]), axis=-1).astype(np.float32)


def fit3d25_to_h36m17(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points)
    if points.shape[-2] < 17:
        raise ValueError(f"Fit3D pose needs at least 17 joints, got {points.shape}")
    return points[..., FIT3D25_TO_H36M17, :]


def mapping_table() -> list[dict[str, object]]:
    """Dataset mapping table used verbatim in generated reports."""

    rows = []
    for name in COCO17_NAMES:
        valid = name in DIRECT_BODY_NAMES
        rows.append(
            {
                "rtmpose_coco_joint": name,
                "fit3d_gt_joint": name if valid else None,
                "athletepose3d_gt_joint": name if valid else None,
                "valid_primary_2d": valid,
                "reason": "direct anatomical correspondence" if valid else "no direct mocap COCO facial landmark",
            }
        )
    return rows
