"""M0 RGB benchmark on AthletePose3D: image in, 3D pose out, scored on GT 3D.

Two arms, identical frames, identical joints, identical metrics:

``rtmpose_motionagformer``
    RGB -> RTMPose-s (full-image bbox, SimCC decode, inverse affine) -> COCO17
    -> H36M17 -> screen normalization -> 27-frame lookahead-5 window ->
    MotionAGFormer-XS -> target-frame 3D. This is BPT's pipeline.
``mediapipe_lite``
    RGB -> MediaPipe Pose Landmarker lite in VIDEO running mode -> BlazePose 33
    world landmarks -> H36M17. No separate lifter.

Both are compared against ``joint_3d_camera`` in millimetres, and their 2D is
compared against ``joint_3d_image`` xy with the GT box diagonal as the single
NME/PCK scale. Predictions are cached per sequence so a run resumes.

Usage:

    PYTHONPATH=. python3 scripts/run_m0_athletepose3d_rgb.py \\
        --arm rtmpose_motionagformer --image-root /data/athletepose3d/pose_2d \\
        --rtmpose-backend onnx --rtmpose-model models/rtmpose_s.onnx
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from bpt.benchmarks.pose import cache
from pose_feedback.body.motionagformer_adapter import coco17_to_motionagformer_h36m17
from bpt.benchmarks.pose.datasets import athletepose3d, athletepose3d_images
from bpt.benchmarks.pose.evaluation.metrics_2d import evaluate_2d
from bpt.benchmarks.pose.evaluation.metrics_3d import evaluate_3d
from bpt.benchmarks.pose.evaluation.metrics_angles import evaluate_angles
from bpt.benchmarks.pose.evaluation.metrics_bones import evaluate_bones
from bpt.benchmarks.pose.evaluation.metrics_temporal import evaluate_temporal
from bpt.benchmarks.pose.normalization import (
    LOOKAHEAD,
    TARGET_INDEX,
    WINDOW_SIZE,
    build_pixel_windows,
    denormalize_targets,
    flip_data,
    normalize_windows,
)
from bpt.benchmarks.pose.temporal import full_real_context_mask

ARMS = ("rtmpose_motionagformer", "mediapipe_lite")
# The 12 joints with a direct anatomical correspondence in both skeletons.
DIRECT_H36M_INDICES = np.asarray([11, 14, 12, 15, 13, 16, 4, 1, 5, 2, 6, 3], dtype=np.int64)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--records", default="/tmp/pose_3d.zip", help=".pkl file or .zip holding valid.pkl")
    parser.add_argument("--member", default=None)
    parser.add_argument("--image-root", required=True, help="directory holding the extracted RGB frames")
    parser.add_argument("--sequences", type=int, default=0, help="number of sequences (0 = all)")
    parser.add_argument("--max-frames", type=int, default=0, help="cap frames per sequence (0 = all)")
    parser.add_argument("--batch", type=int, default=256, help="lifter windows per forward pass")
    parser.add_argument("--normalization", choices=("full_image", "person_crop"), default="full_image")
    parser.add_argument("--no-flip", dest="flip", action="store_false", help="disable lifter flip test")
    parser.add_argument("--cache-dir", default="assets/benchmarks/m0/athletepose3d_rgb")
    parser.add_argument("--output", default=None)
    # RTMPose arm
    parser.add_argument("--rtmpose-backend", choices=("coreml", "onnx"), default="onnx")
    parser.add_argument("--rtmpose-model", default="assets/coreml/rtmpose_s_forward.mlpackage")
    # MotionAGFormer
    parser.add_argument("--repo-dir", default="external/MotionAGFormer")
    parser.add_argument("--config", default="external/MotionAGFormer/configs/h36m/MotionAGFormer-xsmall.yaml")
    parser.add_argument("--checkpoint", default="external/MotionAGFormer/checkpoint/motionagformer-xs-h36m.pth.tr")
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda", "mps"))
    # MediaPipe arm
    parser.add_argument("--mediapipe-model", default="assets/mediapipe/pose_landmarker_lite.task")
    parser.add_argument("--mediapipe-delegate", choices=("cpu", "gpu"), default="cpu")
    return parser.parse_args()


def run_rtmpose_arm(args, sequence_arrays, paths, state, ratio):
    """RGB -> RTMPose COCO17 -> H36M17 -> lifted 3D millimetres."""

    estimator, runner = state["rtmpose"], state["motion"]
    width, height = sequence_arrays["width"], sequence_arrays["height"]
    coco17, rtmpose_ms = [], []
    for _, frame in athletepose3d_images.iter_frames_bgr(paths):
        started = time.perf_counter()
        coco17.append(estimator.predict(frame))
        rtmpose_ms.append((time.perf_counter() - started) * 1000.0)
    coco17 = np.stack(coco17)

    # Production adapter, so the lifter sees exactly what the app would feed it.
    converted = [coco17_to_motionagformer_h36m17(frame) for frame in coco17]
    h36m_pixels = np.stack([xy for xy, _ in converted]).astype(np.float64)
    h36m_scores = np.stack([score for _, score in converted]).astype(np.float64)

    started = time.perf_counter()
    windows = build_pixel_windows(h36m_pixels)
    window_scores = build_pixel_windows(np.repeat(h36m_scores[..., None], 2, axis=-1))[..., 0]
    inputs, terms = normalize_windows(
        windows, width, height, args.normalization, confidence=window_scores
    )
    targets = predict_targets(runner, inputs, args.batch, flip=args.flip)
    lifter_ms = (time.perf_counter() - started) * 1000.0 / max(1, len(coco17))
    prediction_mm = denormalize_targets(targets, terms) / np.asarray(ratio)[:, None, None]
    return {
        "prediction_mm": prediction_mm,
        "h36m17_2d": np.concatenate([h36m_pixels, h36m_scores[..., None]], axis=-1),
        "coco17_2d": coco17,
        "rtmpose_ms": np.asarray(rtmpose_ms, dtype=np.float32),
        "lifter_ms_per_frame": lifter_ms,
    }


def predict_targets(runner, inputs, batch, flip=True):
    outputs = []
    for start in range(0, len(inputs), batch):
        chunk = inputs[start : start + batch]
        prediction = np.asarray(runner.predict_3d(chunk))
        if flip:
            mirrored = flip_data(np.asarray(runner.predict_3d(flip_data(chunk))))
            prediction = (prediction + mirrored) / 2.0
        outputs.append(prediction[:, TARGET_INDEX])
    return np.concatenate(outputs, axis=0)


def run_mediapipe_arm(args, sequence_arrays, paths, state):
    """RGB -> BlazePose world landmarks -> H36M17 3D for one sequence."""

    import cv2

    from bpt.benchmarks.pose.estimators.mediapipe_pose import (
        to_h36m17_millimetres,
        to_h36m17_pixels,
    )

    estimator = state["mediapipe"]
    width, height = sequence_arrays["width"], sequence_arrays["height"]
    fps = sequence_arrays["fps"] or 30.0
    pose_2d, pose_3d, detect_ms, detected = [], [], [], []
    for index, frame in athletepose3d_images.iter_frames_bgr(paths):
        timestamp_ms = int(round(index * 1000.0 / fps))
        started = time.perf_counter()
        landmarks, world = estimator.detect(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), timestamp_ms)
        detect_ms.append((time.perf_counter() - started) * 1000.0)
        if landmarks is None:
            pose_2d.append(np.full((17, 3), np.nan))
            pose_3d.append(np.full((17, 3), np.nan))
            detected.append(False)
            continue
        pose_2d.append(to_h36m17_pixels(landmarks, width, height))
        pose_3d.append(to_h36m17_millimetres(world))
        detected.append(True)
    return {
        "prediction_mm": np.stack(pose_3d),
        "h36m17_2d": np.stack(pose_2d),
        "detected": np.asarray(detected),
        "detect_ms": np.asarray(detect_ms, dtype=np.float32),
    }


def evaluate_sequence(prediction_mm, prediction_2d, arrays, fps):
    ground_truth_3d = arrays["joints_3d_camera"]
    ground_truth_2d = arrays["joints_2d"]
    valid = np.isfinite(prediction_mm).all(axis=-1)
    context = full_real_context_mask(len(prediction_mm), WINDOW_SIZE, LOOKAHEAD)
    report = {"key": arrays["key"], "frames": int(len(prediction_mm)), "fps": fps}
    report["detected_frames"] = int(valid.any(axis=1).sum())
    for name, mask in (("all_frames", valid), ("full_real_context", valid & context[:, None])):
        if not mask.any():
            continue
        metrics = evaluate_3d(prediction_mm, ground_truth_3d, mask)
        bones = evaluate_bones(prediction_mm, ground_truth_3d, mask)
        entry = {
            "count": metrics["count"],
            **{key: metrics[key] for key in ("mpjpe", "n_mpjpe", "pa_mpjpe")},
            **{f"{key}_p90": metrics[f"{key}_p90"] for key in ("mpjpe", "n_mpjpe", "pa_mpjpe")},
            "angles": evaluate_angles(prediction_mm, ground_truth_3d, mask)["mae_degrees"],
            "bones": {k: bones[k] for k in ("absolute_bone_length_error", "relative_bone_length_error")},
        }
        if prediction_2d is not None:
            direct = DIRECT_H36M_INDICES
            metrics_2d = evaluate_2d(
                prediction_2d[:, direct],
                ground_truth_2d[:, direct],
                mask[:, direct],
                arrays["boxes_xyxy"],
            )
            entry["2d"] = {
                key: metrics_2d[key]
                for key in ("count", "mean_pixel_error", "median_pixel_error", "nme",
                            "pck_0.05", "pck_0.10", "pck_0.20", "pck_auc_0.20")
            }
        report[name] = entry
    report["temporal"] = evaluate_temporal(prediction_mm, ground_truth_3d, valid, fps=fps)
    return report


def aggregate(reports):
    result = {}
    for context in ("all_frames", "full_real_context"):
        present = [report[context] for report in reports if context in report]
        if not present:
            continue
        weights = np.asarray([entry["count"] for entry in present], dtype=np.float64)
        block = {
            "sequences": len(present),
            "joint_observations": int(weights.sum()),
            **{
                metric: float(np.average([entry[metric] for entry in present], weights=weights))
                for metric in ("mpjpe", "n_mpjpe", "pa_mpjpe", "angles")
            },
        }
        with_2d = [entry["2d"] for entry in present if "2d" in entry]
        if with_2d:
            weights_2d = np.asarray([entry["count"] for entry in with_2d], dtype=np.float64)
            block["2d"] = {
                metric: float(np.average([entry[metric] for entry in with_2d], weights=weights_2d))
                for metric in ("mean_pixel_error", "nme", "pck_0.05", "pck_0.10", "pck_0.20", "pck_auc_0.20")
            }
        result[context] = block
    result["detected_frame_ratio"] = float(
        np.sum([r["detected_frames"] for r in reports]) / max(1, np.sum([r["frames"] for r in reports]))
    )
    return result


def build_state(args):
    state = {}
    if args.arm == "rtmpose_motionagformer":
        from pose_feedback.body.motionagformer_runner import MotionAGFormerRunner

        from bpt.benchmarks.pose.estimators.rtmpose import RTMPoseEstimator

        state["rtmpose"] = RTMPoseEstimator(backend=args.rtmpose_backend, model_path=args.rtmpose_model)
        state["motion"] = MotionAGFormerRunner(
            repo_dir=args.repo_dir,
            config_path=args.config,
            checkpoint_path=args.checkpoint,
            window_size=WINDOW_SIZE,
            device=args.device,
        )
    else:
        from bpt.benchmarks.pose.estimators.mediapipe_pose import MediaPipePoseEstimator

        state["mediapipe"] = MediaPipePoseEstimator(
            model_path=args.mediapipe_model, delegate=args.mediapipe_delegate
        )
    return state


def main():
    args = parse_args()
    records = athletepose3d.load_records(args.records, member=args.member)
    sequences = athletepose3d.group_sequences(records)
    if args.sequences:
        sequences = sequences[: args.sequences]
    _, prefix_dropped = athletepose3d_images.resolve_root(
        args.image_root, [record["image_path"] for record in sequences[0].records[:8]]
    )
    print(f"arm={args.arm} sequences={len(sequences)} image prefix dropped={prefix_dropped}")

    state = build_state(args)
    expect = {
        "arm": args.arm,
        "window_size": WINDOW_SIZE,
        "lookahead": LOOKAHEAD,
        "input": "rgb",
        "units": "camera_millimetre",
    }
    if args.arm == "rtmpose_motionagformer":
        expect.update(
            {"normalization": args.normalization, "flip_test": bool(args.flip), "rtmpose_backend": args.rtmpose_backend}
        )
    cache_dir = Path(args.cache_dir) / args.arm
    reports, skipped = [], []

    for position, sequence in enumerate(sequences, start=1):
        arrays = athletepose3d.sequence_arrays(sequence)
        ratio = np.asarray([float(record["ratio"]) for record in sequence.records], dtype=np.float64)
        image_paths = arrays["image_paths"]
        if args.max_frames:
            ratio = ratio[: args.max_frames]
            image_paths = image_paths[: args.max_frames]
            for key in ("joints_2d", "joints_3d_camera", "joints_3d_image", "boxes_xyxy", "frame_ids"):
                arrays[key] = arrays[key][: args.max_frames]
        resolution = athletepose3d_images.check_sequence(args.image_root, image_paths, prefix_dropped)
        if not resolution.complete:
            skipped.append({"key": arrays["key"], "missing_frames": resolution.missing})
            print(f"[{position}/{len(sequences)}] {arrays['key']} SKIPPED: {resolution.missing} frames missing")
            continue
        paths = athletepose3d_images.frame_paths(args.image_root, image_paths, prefix_dropped)

        cached = cache.load(cache_dir, arrays["key"], expect)
        if cached is None:
            started = time.time()
            if args.arm == "rtmpose_motionagformer":
                result = run_rtmpose_arm(args, arrays, paths, state, ratio)
                stored = {
                    "prediction_mm": result["prediction_mm"],
                    "prediction_2d": result["h36m17_2d"],
                    "coco17_2d": result["coco17_2d"],
                    "rtmpose_ms": result["rtmpose_ms"],
                }
                extra = {"lifter_ms_per_frame": float(result["lifter_ms_per_frame"])}
            else:
                result = run_mediapipe_arm(args, arrays, paths, state)
                stored = {
                    "prediction_mm": result["prediction_mm"],
                    "prediction_2d": result["h36m17_2d"],
                    "detect_ms": result["detect_ms"],
                }
                extra = {"detect_ms_mean": float(np.mean(result["detect_ms"]))}
            cache.save(
                cache_dir,
                arrays["key"],
                {**stored, "frame_ids": arrays["frame_ids"]},
                {**expect, "frames": int(len(stored["prediction_mm"])), "seconds": round(time.time() - started, 2), **extra},
            )
            prediction_mm, prediction_2d = stored["prediction_mm"], stored["prediction_2d"]
        else:
            prediction_mm = cached[0]["prediction_mm"]
            prediction_2d = cached[0].get("prediction_2d")

        report = evaluate_sequence(prediction_mm, prediction_2d, arrays, arrays["fps"])
        reports.append(report)
        summary = report.get("full_real_context", report.get("all_frames"))
        line = (
            f"[{position}/{len(sequences)}] {report['key']} frames={report['frames']} "
            f"mpjpe={summary['mpjpe']:.1f} pa_mpjpe={summary['pa_mpjpe']:.1f} (mm) "
            f"angle_mae={summary['angles']:.1f}deg"
        )
        if "2d" in summary:
            line += f" nme={summary['2d']['nme']:.3f} pck@0.05={summary['2d']['pck_0.05']:.3f}"
        print(line, flush=True)

    output = {
        "baseline": f"M0 RGB arm: {args.arm}",
        "dataset": "AthletePose3D valid",
        "units": "millimetre",
        "contract": expect,
        "skipped_sequences": skipped,
        "sequences": reports,
        "aggregate": aggregate(reports) if reports else {},
    }
    path = Path(args.output) if args.output else cache_dir / "summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output["aggregate"], indent=2, sort_keys=True))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
