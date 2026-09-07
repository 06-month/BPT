"""Experimental MediaPipe Pose Heavy Core ML pipeline smoke test.

This script tries to run a hand-built BODY pose pipeline around Core ML
conversions of the internal MediaPipe Pose Heavy TFLite forwards:

  frame -> detector Core ML -> detector decode -> ROI crop -> landmark Core ML
  -> landmark decode -> coordinate restore -> visualization

It does not use placeholder landmarks. If conversion or decode information is
missing, it stops at the exact stage and writes a feasibility report.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.experimental.mediapipe_pose_coreml_pipeline import (  # noqa: E402
    ExperimentalMediaPipePoseHeavyCoreMLPipeline,
    ExperimentalPipelineError,
    PoseCoreMLStageStatus,
    draw_pose_landmarks,
    write_feasibility_report,
)


DEFAULT_VIDEO = ROOT / "assets/pushup/pushup_02.mp4"
DEFAULT_DETECTOR = ROOT / "assets/coreml/mediapipe_pose_heavy_coreml/pose_detector.mlpackage"
DEFAULT_LANDMARK = ROOT / "assets/coreml/mediapipe_pose_heavy_coreml/pose_landmarks_detector.mlpackage"
DEFAULT_OUT = ROOT / "outputs/mediapipe_pose_heavy_coreml_pipeline.mp4"
DEFAULT_DEBUG_DIR = ROOT / "outputs/mediapipe_pose_coreml_debug"
DEFAULT_COMPARE_OUT = ROOT / "outputs/mediapipe_pose_heavy_coreml_vs_task.mp4"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", default=str(DEFAULT_VIDEO))
    parser.add_argument("--detector-model", default=str(DEFAULT_DETECTOR))
    parser.add_argument("--landmark-model", default=str(DEFAULT_LANDMARK))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--save-frames", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--compare-mediapipe-task", action="store_true")
    parser.add_argument("--compare-out", default=str(DEFAULT_COMPARE_OUT))
    parser.add_argument("--compute-units", default="all")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    debug_dir = DEFAULT_DEBUG_DIR
    debug_dir.mkdir(parents=True, exist_ok=True)
    report_path = debug_dir / "mediapipe_pose_heavy_coreml_pipeline_feasibility_report.md"
    json_report_path = debug_dir / "mediapipe_pose_heavy_coreml_pipeline_status.json"

    status = initial_status()
    details = {
        "video": args.video,
        "detector_model": args.detector_model,
        "landmark_model": args.landmark_model,
        "output_video": args.out,
        "compare_mediapipe_task": args.compare_mediapipe_task,
    }

    video_path = Path(args.video)
    if not video_path.exists():
        return stop_with_report(
            status,
            details,
            report_path,
            json_report_path,
            "input_video",
            f"input video not found: {video_path}",
        )

    detector_path = Path(args.detector_model)
    landmark_path = Path(args.landmark_model)
    missing_models = [str(path) for path in (detector_path, landmark_path) if not path.exists()]
    if missing_models:
        return stop_with_report(
            status,
            details,
            report_path,
            json_report_path,
            "coreml_conversion",
            "Core ML model file(s) missing; conversion did not produce runnable models: "
            + ", ".join(missing_models),
        )

    status.coreml_conversion = True
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return stop_with_report(
            status,
            details,
            report_path,
            json_report_path,
            "video_open",
            f"failed to open video: {video_path}",
        )

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(out_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        cap.release()
        return stop_with_report(
            status,
            details,
            report_path,
            json_report_path,
            "video_writer",
            f"failed to open writer: {out_path}",
        )

    try:
        pipeline = ExperimentalMediaPipePoseHeavyCoreMLPipeline(
            detector_model=detector_path,
            landmark_model=landmark_path,
            compute_units=args.compute_units,
        )
    except Exception as exc:  # noqa: BLE001
        cap.release()
        writer.release()
        return stop_with_report(
            status,
            details,
            report_path,
            json_report_path,
            "coreml_runtime",
            f"{type(exc).__name__}: {exc}",
        )

    processed = 0
    detected = 0
    errors = []
    frame_results = []
    start = time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if args.max_frames and processed >= args.max_frames:
                break
            try:
                result = pipeline.process_frame(frame, frame_index=processed)
                status = result.stage_status
                if result.landmarks_px is not None:
                    detected += 1
                annotated = draw_pose_landmarks(frame, result.landmarks_px)
                writer.write(annotated)
                frame_results.append((processed, result.landmarks_px))
                if args.save_frames:
                    cv2.imwrite(str(debug_dir / f"coreml_frame_{processed:05d}.jpg"), annotated)
            except ExperimentalPipelineError as exc:
                errors.append({"frame": processed, "stage": exc.stage, "message": exc.message})
                status.mark_failure(exc.stage, exc.message)
                break
            processed += 1
    finally:
        cap.release()
        writer.release()

    elapsed = max(time.perf_counter() - start, 1e-9)
    details.update(
        {
            "processed_frames": processed,
            "detected_frames": detected,
            "runtime_fps": processed / elapsed,
            "errors": errors,
        }
    )

    if args.compare_mediapipe_task and frame_results and not errors:
        comparison = compare_with_mediapipe_task(args, frame_results)
        details["comparison"] = comparison
        status.comparison = bool(comparison.get("ran"))
    elif args.compare_mediapipe_task:
        details["comparison"] = {
            "ran": False,
            "reason": "Core ML pipeline did not produce comparable landmarks.",
            "output_video": args.compare_out,
        }

    write_reports(status, details, report_path, json_report_path)
    print(json.dumps({"stage_status": status.__dict__, "details": details}, indent=2, default=str))
    return 0 if not errors else 1


def initial_status() -> PoseCoreMLStageStatus:
    status = PoseCoreMLStageStatus()
    status.task_extraction = (ROOT / "assets/coreml/mediapipe_pose_heavy_tflite/pose_detector.tflite").exists() and (
        ROOT / "assets/coreml/mediapipe_pose_heavy_tflite/pose_landmarks_detector.tflite"
    ).exists()
    status.tflite_inspection = (ROOT / "assets/coreml/mediapipe_pose_heavy_coreml_inspection.json").exists()
    status.coreml_conversion = Path(DEFAULT_DETECTOR).exists() and Path(DEFAULT_LANDMARK).exists()
    return status


def stop_with_report(
    status: PoseCoreMLStageStatus,
    details: dict,
    report_path: Path,
    json_report_path: Path,
    stage: str,
    message: str,
) -> int:
    status.mark_failure(stage, message)
    details["stop_stage"] = stage
    details["stop_message"] = message
    write_reports(status, details, report_path, json_report_path)
    print(json.dumps({"stage_status": status.__dict__, "details": details}, indent=2, default=str))
    return 0


def write_reports(
    status: PoseCoreMLStageStatus,
    details: dict,
    report_path: Path,
    json_report_path: Path,
) -> None:
    write_feasibility_report(report_path, status, details)
    json_report_path.write_text(
        json.dumps({"stage_status": status.__dict__, "details": details}, indent=2, default=str),
        encoding="utf-8",
    )


def compare_with_mediapipe_task(args, frame_results):
    # Kept optional and isolated. It only runs after the Core ML pipeline has
    # produced real landmarks, so it cannot create fake parity metrics.
    os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")
    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
    except Exception as exc:  # noqa: BLE001
        return {"ran": False, "reason": f"mediapipe import failed: {type(exc).__name__}: {exc}"}

    model_path = ROOT / "assets/mediapipe/pose_landmarker_heavy.task"
    if not model_path.exists():
        return {"ran": False, "reason": f"reference task missing: {model_path}"}

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        return {"ran": False, "reason": f"failed to reopen video: {args.video}"}
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(
        args.compare_out,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width * 2, height),
    )
    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(
            model_asset_path=str(model_path),
            delegate=python.BaseOptions.Delegate.CPU,
        ),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)
    coreml_by_frame = dict(frame_results)
    errors = []
    missing = 0
    processed = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if processed not in coreml_by_frame:
                processed += 1
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect_for_video(mp_image, int(processed * 1000.0 / fps))
            pose_list = getattr(result, "pose_landmarks", None) or []
            left = draw_pose_landmarks(frame, coreml_by_frame[processed], color=(255, 0, 0))
            if pose_list:
                ref = np.array([[lm.x * width, lm.y * height] for lm in pose_list[0]], dtype=np.float32)
                right = draw_pose_landmarks(frame, ref, color=(0, 255, 0))
                core = np.asarray(coreml_by_frame[processed], dtype=np.float32)[:, :2]
                n = min(len(core), len(ref))
                errors.extend(np.linalg.norm(core[:n] - ref[:n], axis=1).tolist())
            else:
                missing += 33
                right = frame.copy()
            writer.write(np.concatenate([left, right], axis=1))
            processed += 1
    finally:
        cap.release()
        writer.release()
        close = getattr(landmarker, "close", None)
        if close is not None:
            close()

    if not errors:
        return {"ran": False, "reason": "no comparable landmarks", "missing_landmark_count": missing}
    arr = np.asarray(errors, dtype=np.float32)
    return {
        "ran": True,
        "output_video": args.compare_out,
        "mean_pixel_error": float(np.mean(arr)),
        "median_pixel_error": float(np.median(arr)),
        "p90_pixel_error": float(np.percentile(arr, 90)),
        "missing_landmark_count": int(missing),
    }


if __name__ == "__main__":
    raise SystemExit(main())
