"""Root-relative, scale-aligned and Procrustes-aligned 3D metrics."""

from __future__ import annotations

import numpy as np

from bpt.benchmarks.pose.geometry.alignment import procrustes_align, root_center, scale_align


def evaluate_3d(
    prediction: np.ndarray,
    target: np.ndarray,
    valid: np.ndarray,
    root_index: int = 0,
) -> dict:
    pred = np.asarray(prediction, dtype=np.float64)
    gt = np.asarray(target, dtype=np.float64)
    mask = np.asarray(valid, dtype=bool).copy()
    if pred.shape != gt.shape or pred.shape[-1] != 3 or pred.shape[:-1] != mask.shape:
        raise ValueError("3D prediction, target and valid shapes differ")
    mask &= np.isfinite(pred).all(axis=-1) & np.isfinite(gt).all(axis=-1)
    pred_rel, gt_rel = root_center(pred, root_index), root_center(gt, root_index)
    pred_scale, scales = scale_align(pred_rel, gt_rel, mask)
    pred_pa = procrustes_align(pred_rel, gt_rel, mask)
    errors = {
        "mpjpe": np.linalg.norm(pred_rel - gt_rel, axis=-1),
        "n_mpjpe": np.linalg.norm(pred_scale - gt_rel, axis=-1),
        "pa_mpjpe": np.linalg.norm(pred_pa - gt_rel, axis=-1),
    }
    output = {"count": int(mask.sum()), "scales": scales, "valid": mask, "errors": errors}
    for name, values in errors.items():
        valid_values = values[mask & np.isfinite(values)]
        output[name] = float(valid_values.mean()) if valid_values.size else float("nan")
        output[f"{name}_p50"] = float(np.percentile(valid_values, 50)) if valid_values.size else float("nan")
        output[f"{name}_p75"] = float(np.percentile(valid_values, 75)) if valid_values.size else float("nan")
        output[f"{name}_p90"] = float(np.percentile(valid_values, 90)) if valid_values.size else float("nan")
        output[f"{name}_p95"] = float(np.percentile(valid_values, 95)) if valid_values.size else float("nan")
    output["per_joint"] = {
        joint: {
            name: float(values[mask[:, joint], joint].mean()) if np.any(mask[:, joint]) else float("nan")
            for name, values in errors.items()
        }
        for joint in range(pred.shape[1])
    }
    return output
