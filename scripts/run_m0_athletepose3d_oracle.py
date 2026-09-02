"""M0 Stage A oracle: GT 2D -> MotionAGFormer-XS -> 3D metrics on AthletePose3D.

This isolates the lifter from RTMPose. Ground-truth H36M17 image joints go
through the production temporal window and target index, so a bad number here
is the lifter's or the input convention's, never RTMPose's. RGB frames are not
required, so it runs while the 29GB AthletePose3D image archives are
unavailable.

Two input normalizations are supported because they are not interchangeable:

``full_image``
    ``x/W*2-1``, ``y/W*2-H/W`` — what BPT's iOS pipeline and the official H36M
    reader use. Valid only while the subject fills a H36M-like share of frame.
``person_crop``
    The official ``utils/data.py::crop_scale`` square crop around the pose,
    mapped to [-1, 1] — what MotionAGFormer's own in-the-wild demo uses.

Predictions are denormalized with the same parameters they were normalized
with, then divided by the per-frame AthletePose3D ``ratio`` to reach metric
camera millimetres.

Usage:

    PYTHONPATH=. python3 scripts/run_m0_athletepose3d_oracle.py \
        --records /tmp/pose_3d.zip --sequences 5 --normalization person_crop
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from bpt.benchmarks.pose import cache
from bpt.benchmarks.pose.datasets import athletepose3d
from bpt.benchmarks.pose.evaluation.metrics_3d import evaluate_3d
from bpt.benchmarks.pose.evaluation.metrics_angles import evaluate_angles
from bpt.benchmarks.pose.evaluation.metrics_bones import evaluate_bones
from bpt.benchmarks.pose.evaluation.metrics_temporal import evaluate_temporal
from bpt.benchmarks.pose.normalization import (
    LOOKAHEAD,
    MODES,
    TARGET_INDEX,
    WINDOW_SIZE,
    build_pixel_windows,
    denormalize_targets,
    flip_data,
    normalize_windows,
)
from bpt.benchmarks.pose.temporal import full_real_context_mask


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", default="/tmp/pose_3d.zip", help=".pkl file or .zip holding valid.pkl")
    parser.add_argument("--member", default=None, help="member name inside a zip (default: valid.pkl)")
    parser.add_argument("--sequences", type=int, default=5, help="number of sequences (0 = all)")
    parser.add_argument("--max-frames", type=int, default=0, help="cap frames per sequence (0 = all)")
    parser.add_argument(
        "--frame-stride",
        type=int,
        default=1,
        help="score every Nth target frame; each scored frame still uses its own full 27-frame window",
    )
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "mps", "cuda"))
    parser.add_argument("--batch", type=int, default=128, help="windows per forward pass")
    parser.add_argument("--normalization", choices=MODES, default="full_image")
    parser.add_argument(
        "--no-flip",
        dest="flip",
        action="store_false",
        help="disable the official left/right flip test-time augmentation",
    )
    parser.add_argument("--cache-dir", default="assets/benchmarks/m0/athletepose3d_oracle")
    parser.add_argument("--output", default=None, help="summary path (default: <cache-dir>/summary_<mode>.json)")
    parser.add_argument("--repo-dir", default="external/MotionAGFormer")
    parser.add_argument("--config", default="external/MotionAGFormer/configs/h36m/MotionAGFormer-xsmall.yaml")
    parser.add_argument(
        "--checkpoint", default="external/MotionAGFormer/checkpoint/motionagformer-xs-h36m.pth.tr"
    )
    return parser.parse_args()


def predict_targets(runner, inputs: np.ndarray, batch: int, flip: bool = True) -> np.ndarray:
    """Return each window's target-frame pose, still in normalized units."""

    outputs = []
    for start in range(0, len(inputs), batch):
        chunk = inputs[start : start + batch]
        prediction = np.asarray(runner.predict_3d(chunk))
        if flip:
            mirrored = flip_data(np.asarray(runner.predict_3d(flip_data(chunk))))
            prediction = (prediction + mirrored) / 2.0
        outputs.append(prediction[:, TARGET_INDEX])
    return np.concatenate(outputs, axis=0)


def representation_floor(arrays: dict, ratio: np.ndarray, mask: np.ndarray) -> float:
    """MPJPE of the 2.5D image representation itself: this metric's floor."""

    image_mm = arrays["joints_3d_image"] / ratio[:, None, None]
    return evaluate_3d(image_mm, arrays["joints_3d_camera"], mask)["mpjpe"]


def evaluate_sequence(
    prediction_mm: np.ndarray, arrays: dict, ratio: np.ndarray, targets: np.ndarray, stride: int
) -> dict:
    ground_truth = arrays["joints_3d_camera"][targets]
    valid = np.ones(prediction_mm.shape[:2], dtype=bool)
    context = full_real_context_mask(len(arrays["joints_3d_camera"]), WINDOW_SIZE, LOOKAHEAD)[targets]
    fps = arrays["fps"] / stride
    report = {
        "key": arrays["key"],
        "frames": int(len(prediction_mm)),
        "source_frames": int(len(arrays["joints_3d_camera"])),
        "frame_stride": stride,
        "fps": arrays["fps"],
    }
    for name, mask in (("all_frames", valid), ("full_real_context", valid & context[:, None])):
        if not mask.any():
            continue
        metrics = evaluate_3d(prediction_mm, ground_truth, mask)
        bones = evaluate_bones(prediction_mm, ground_truth, mask)
        report[name] = {
            "count": metrics["count"],
            **{key: metrics[key] for key in ("mpjpe", "n_mpjpe", "pa_mpjpe")},
            **{f"{key}_p90": metrics[f"{key}_p90"] for key in ("mpjpe", "n_mpjpe", "pa_mpjpe")},
            "angles": evaluate_angles(prediction_mm, ground_truth, mask)["mae_degrees"],
            "bones": {
                key: bones[key] for key in ("absolute_bone_length_error", "relative_bone_length_error")
            },
        }
    report["temporal"] = evaluate_temporal(prediction_mm, ground_truth, valid, fps=fps)
    report["representation_floor_mpjpe"] = representation_floor(
        {key: value[targets] if key.startswith("joints") else value for key, value in arrays.items()},
        ratio[targets],
        valid,
    )
    return report


def aggregate(reports: list[dict]) -> dict:
    result = {}
    for context in ("all_frames", "full_real_context"):
        present = [report[context] for report in reports if context in report]
        if not present:
            continue
        weights = np.asarray([entry["count"] for entry in present], dtype=np.float64)
        result[context] = {
            "sequences": len(present),
            "joint_observations": int(weights.sum()),
            **{
                metric: float(np.average([entry[metric] for entry in present], weights=weights))
                for metric in ("mpjpe", "n_mpjpe", "pa_mpjpe", "angles")
            },
        }
    result["representation_floor_mpjpe"] = float(
        np.mean([report["representation_floor_mpjpe"] for report in reports])
    )
    return result


def main():
    args = parse_args()
    from pose_feedback.body.motionagformer_runner import MotionAGFormerRunner

    sequences = athletepose3d.group_sequences(
        athletepose3d.load_records(args.records, member=args.member)
    )
    if args.sequences:
        sequences = sequences[: args.sequences]
    print(f"sequences: {len(sequences)} normalization: {args.normalization}")

    started = time.time()
    runner = MotionAGFormerRunner(
        repo_dir=args.repo_dir,
        config_path=args.config,
        checkpoint_path=args.checkpoint,
        window_size=WINDOW_SIZE,
        device=args.device,
    )
    print(f"model loaded in {time.time() - started:.1f}s on {runner.device_name}")

    expect = {
        "model": "motionagformer_xs_h36m",
        "window_size": WINDOW_SIZE,
        "lookahead": LOOKAHEAD,
        "input": "ground_truth_2d",
        "normalization": args.normalization,
        "flip_test": bool(args.flip),
        "frame_stride": int(args.frame_stride),
        "units": "camera_millimetre_via_2.5d_ratio",
    }
    cache_dir = Path(args.cache_dir) / args.normalization
    reports = []
    for position, sequence in enumerate(sequences, start=1):
        arrays = athletepose3d.sequence_arrays(sequence)
        ratio = np.asarray([float(record["ratio"]) for record in sequence.records], dtype=np.float64)
        if args.max_frames:
            ratio = ratio[: args.max_frames]
            for key in ("joints_2d", "joints_3d_camera", "joints_3d_image", "boxes_xyxy", "frame_ids"):
                arrays[key] = arrays[key][: args.max_frames]
        targets = np.arange(0, len(arrays["joints_2d"]), max(1, args.frame_stride))
        cached = cache.load(cache_dir, arrays["key"], expect)
        if cached is None:
            elapsed = time.time()
            windows = build_pixel_windows(arrays["joints_2d"], targets=targets)
            inputs, terms = normalize_windows(windows, arrays["width"], arrays["height"], args.normalization)
            normalized = predict_targets(runner, inputs, args.batch, flip=args.flip)
            prediction = denormalize_targets(normalized, terms) / ratio[targets, None, None]
            cache.save(
                cache_dir,
                arrays["key"],
                {
                    "prediction_mm": prediction,
                    "frame_ids": arrays["frame_ids"][targets],
                    "target_frames": targets,
                },
                {**expect, "frames": int(len(prediction)), "seconds": round(time.time() - elapsed, 2)},
            )
        else:
            prediction = cached[0]["prediction_mm"]
            targets = cached[0]["target_frames"]
        report = evaluate_sequence(prediction, arrays, ratio, targets, max(1, args.frame_stride))
        reports.append(report)
        summary = report["full_real_context"]
        print(
            f"[{position}/{len(sequences)}] {report['key']} frames={report['frames']} "
            f"mpjpe={summary['mpjpe']:.1f} n_mpjpe={summary['n_mpjpe']:.1f} "
            f"pa_mpjpe={summary['pa_mpjpe']:.1f} (mm) angle_mae={summary['angles']:.1f}deg "
            f"floor={report['representation_floor_mpjpe']:.1f}mm"
        )

    output = {
        "baseline": "M0 oracle 2D -> MotionAGFormer-XS",
        "dataset": "AthletePose3D valid",
        "units": "millimetre",
        "contract": expect,
        "sequences": reports,
        "aggregate": aggregate(reports),
    }
    path = Path(args.output) if args.output else cache_dir / "summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output["aggregate"], indent=2, sort_keys=True))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
