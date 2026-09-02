"""Input normalization contracts for the MotionAGFormer lifter.

MotionAGFormer emits its prediction in the same normalized space it consumes,
so every prediction must be denormalized with the exact terms its input was
normalized with. Both supported modes therefore share one inverse:

    pixel_xy = (normalized_xy + bias) * scale/2 + origin
    depth    = z * scale/2

``full_image``
    ``x/W*2-1``, ``y/W*2-H/W``. The official H36M reader's convention and
    BPT's iOS pipeline. It only matches training when the subject fills a
    H36M-like share of the frame.
``person_crop``
    The official ``utils/data.py::crop_scale`` square crop around the pose
    extent, mapped to [-1, 1]. MotionAGFormer's own in-the-wild demo path.
"""

from __future__ import annotations

import numpy as np

from bpt.benchmarks.pose.temporal import temporal_window_indices

WINDOW_SIZE = 27
LOOKAHEAD = 5
TARGET_INDEX = WINDOW_SIZE - 1 - LOOKAHEAD
LEFT_JOINTS = [1, 2, 3, 14, 15, 16]
RIGHT_JOINTS = [4, 5, 6, 11, 12, 13]
MODES = ("full_image", "person_crop")


def build_pixel_windows(
    points: np.ndarray, window_size: int = WINDOW_SIZE, lookahead: int = LOOKAHEAD
) -> np.ndarray:
    """Stack every target frame's ``[T,17,2]`` window, edge-padded at clip ends."""

    points = np.asarray(points, dtype=np.float64)
    count = len(points)
    indices = np.stack(
        [temporal_window_indices(count, frame, window_size, lookahead) for frame in range(count)]
    )
    return points[indices]


def normalize_windows(windows: np.ndarray, width: int, height: int, mode: str):
    """Return normalized ``[N,T,17,3]`` inputs and their denormalization terms."""

    if mode not in MODES:
        raise ValueError(f"unknown normalization mode: {mode}")
    windows = np.asarray(windows, dtype=np.float64)
    count = len(windows)
    if mode == "full_image":
        scale = np.full(count, float(width))
        bias = np.tile([1.0, height / width], (count, 1))
        origin = np.zeros((count, 2))
    else:
        minimum, maximum = windows.min(axis=(1, 2)), windows.max(axis=(1, 2))
        extent = maximum - minimum
        scale = np.where(extent.max(axis=1) > 0, extent.max(axis=1), 1.0)
        bias = np.ones((count, 2))
        origin = (minimum + maximum - scale[:, None]) / 2.0
    normalized = (windows - origin[:, None, None, :]) / (scale[:, None, None, None] / 2.0)
    normalized -= bias[:, None, None, :]
    if mode == "person_crop":
        normalized = np.clip(normalized, -1.0, 1.0)
    confidence = np.ones((*normalized.shape[:-1], 1))
    inputs = np.concatenate((normalized, confidence), axis=-1).astype(np.float32)
    return inputs, {"scale": scale, "bias": bias, "origin": origin, "mode": mode}


def denormalize_targets(prediction: np.ndarray, terms: dict) -> np.ndarray:
    """Undo ``normalize_windows`` for one pose per window, into pixel 2.5D."""

    prediction = np.asarray(prediction, dtype=np.float64)
    scale = terms["scale"][:, None, None]
    output = prediction.copy()
    output[..., :2] = (output[..., :2] + terms["bias"][:, None, :]) * (scale / 2.0) + terms["origin"][:, None, :]
    output[..., 2:] = output[..., 2:] * (scale / 2.0)
    return output


def flip_data(data: np.ndarray) -> np.ndarray:
    """Official left/right flip: mirror x, then swap the left and right chains."""

    flipped = np.asarray(data).copy()
    flipped[..., 0] *= -1
    flipped[..., LEFT_JOINTS + RIGHT_JOINTS, :] = flipped[..., RIGHT_JOINTS + LEFT_JOINTS, :]
    return flipped
