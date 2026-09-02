"""Masked per-pose alignment protocols for 3D pose metrics."""

from __future__ import annotations

import numpy as np


def root_center(points: np.ndarray, root_index: int = 0) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    return points - points[..., root_index : root_index + 1, :]


def scale_align(
    prediction: np.ndarray,
    target: np.ndarray,
    valid: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit one least-squares scalar per pose, without translation/rotation."""

    pred, gt, mask, squeeze = _batched_inputs(prediction, target, valid)
    aligned = pred.copy()
    scales = np.full(len(pred), np.nan, dtype=np.float64)
    for i in range(len(pred)):
        use = mask[i]
        p, g = pred[i, use], gt[i, use]
        denom = np.sum(p * p)
        if len(p) == 0 or denom <= np.finfo(np.float64).eps:
            continue
        scales[i] = np.sum(p * g) / denom
        aligned[i] = pred[i] * scales[i]
    return (aligned[0], scales[0]) if squeeze else (aligned, scales)


def procrustes_align(
    prediction: np.ndarray,
    target: np.ndarray,
    valid: np.ndarray | None = None,
) -> np.ndarray:
    """Similarity-align each predicted pose to target using valid joints."""

    pred, gt, mask, squeeze = _batched_inputs(prediction, target, valid)
    aligned = np.full_like(pred, np.nan)
    for i in range(len(pred)):
        use = mask[i]
        x, y = pred[i, use], gt[i, use]
        if len(x) < 3:
            continue
        mu_x, mu_y = x.mean(axis=0), y.mean(axis=0)
        x0, y0 = x - mu_x, y - mu_y
        variance = np.sum(x0 * x0)
        if variance <= np.finfo(np.float64).eps:
            continue
        u, singular, vt = np.linalg.svd(x0.T @ y0)
        rotation = u @ vt
        if np.linalg.det(rotation) < 0:
            u[:, -1] *= -1
            singular[-1] *= -1
            rotation = u @ vt
        scale = singular.sum() / variance
        translation = mu_y - scale * (mu_x @ rotation)
        aligned[i] = scale * (pred[i] @ rotation) + translation
    return aligned[0] if squeeze else aligned


def _batched_inputs(prediction, target, valid):
    pred = np.asarray(prediction, dtype=np.float64)
    gt = np.asarray(target, dtype=np.float64)
    if pred.shape != gt.shape or pred.shape[-1] != 3 or pred.ndim not in (2, 3):
        raise ValueError(f"poses must have matching [J,3] or [N,J,3] shapes: {pred.shape}, {gt.shape}")
    squeeze = pred.ndim == 2
    if squeeze:
        pred, gt = pred[None], gt[None]
    finite = np.isfinite(pred).all(axis=-1) & np.isfinite(gt).all(axis=-1)
    if valid is None:
        mask = finite
    else:
        mask = np.asarray(valid, dtype=bool)
        if squeeze and mask.ndim == 1:
            mask = mask[None]
        if mask.shape != finite.shape:
            raise ValueError(f"valid mask {mask.shape} does not match pose joints {finite.shape}")
        mask &= finite
    return pred, gt, mask, squeeze
