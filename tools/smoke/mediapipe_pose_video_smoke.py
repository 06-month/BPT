"""MediaPipe Pose Landmarker VIDEO-mode smoke test on the bundled clip.

Qualitative-only tool to eyeball MediaPipe Pose body keypoint stability against
the current RTMPose-s body pipeline. It uses the MediaPipe Tasks API
PoseLandmarker (NOT the deprecated mp.solutions.pose) in RunningMode.VIDEO and
calls detect_for_video() with monotonic per-frame timestamps.

This does not touch RTMPose, MotionAGFormer, the iOS app, or any model
conversion code. It only reads a video and writes an annotated video.

Example:
  python tools/smoke/mediapipe_pose_video_smoke.py \
    --video assets/smoke/vedio_1.mp4 \
    --model assets/mediapipe/pose_landmarker_lite.task \
    --out outputs/mediapipe_pose_video_smoke.mp4
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Match the project hand runner: force CPU and disable the GPU delegate so the
# Tasks graph does not depend on a GL inference delegate on macOS.
os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mpl_cache")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VIDEO = ROOT / "assets/smoke/vedio_1.mp4"
DEFAULT_MODEL = ROOT / "assets/mediapipe/pose_landmarker_lite.task"
DEFAULT_OUT = ROOT / "outputs/mediapipe_pose_video_smoke.mp4"

MODEL_MISSING_MSG = """
Pose Landmarker model file not found: {path}

Get it with the bundled helper:
  python tools/smoke/download_pose_landmarker.py

Or download manually:
  1. Download pose_landmarker_lite.task from the official MediaPipe Pose
     Landmarker model page:
       https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models
  2. Place it at:
       assets/mediapipe/pose_landmarker_lite.task
"""


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", default=str(DEFAULT_VIDEO))
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="0 means process the full video",
    )
    parser.add_argument("--min-pose-detection-confidence", type=float, default=0.5)
    parser.add_argument("--min-pose-presence-confidence", type=float, default=0.5)
    parser.add_argument("--min-tracking-confidence", type=float, default=0.5)
    return parser.parse_args()


def build_landmarker(args):
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(
            model_asset_path=args.model,
            delegate=python.BaseOptions.Delegate.CPU,
        ),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=args.min_pose_detection_confidence,
        min_pose_presence_confidence=args.min_pose_presence_confidence,
        min_tracking_confidence=args.min_tracking_confidence,
        output_segmentation_masks=False,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)
    return mp, vision, landmarker


def pose_connections(vision):
    """Return the list of (start, end) landmark index pairs for the skeleton."""
    # MediaPipe exposes pose connections under solutions; fall back to a hand
    # written list if that import is unavailable in this build.
    try:
        from mediapipe.python.solutions import pose as mp_pose

        return [(c[0], c[1]) for c in mp_pose.POSE_CONNECTIONS]
    except Exception:  # noqa: BLE001
        # 33-landmark BlazePose topology (subset covering the main skeleton).
        return [
            (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
            (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
            (25, 27), (26, 28), (27, 29), (28, 30), (29, 31),
            (30, 32), (27, 31), (28, 32),
        ]


def draw_pose(frame, landmarks, connections):
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for start, end in connections:
        if start < len(pts) and end < len(pts):
            cv2.line(frame, pts[start], pts[end], (0, 255, 0), 2)
    for x, y in pts:
        cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)


def overlay_text(frame, frame_index, detected):
    lines = [
        "MediaPipe Pose VIDEO",
        f"frame: {frame_index}",
        f"detected: {str(detected).lower()}",
    ]
    y = 24
    for line in lines:
        cv2.putText(
            frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
            (0, 0, 0), 3, cv2.LINE_AA,
        )
        cv2.putText(
            frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
            (255, 255, 255), 1, cv2.LINE_AA,
        )
        y += 24


def main():
    args = parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Input video not found: {video_path}")
        return 1

    model_path = Path(args.model)
    if not model_path.exists():
        print(MODEL_MISSING_MSG.format(path=model_path))
        return 1

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Failed to open video: {video_path}")
        return 1

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

    mp, vision, landmarker = build_landmarker(args)
    connections = pose_connections(vision)

    processed = 0
    detected_frames = 0
    start = time.time()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if args.max_frames and processed >= args.max_frames:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            # Monotonic timestamp derived from frame index and video FPS.
            timestamp_ms = int(processed * (1000.0 / fps))

            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            pose_list = getattr(result, "pose_landmarks", None) or []
            detected = len(pose_list) > 0
            if detected:
                detected_frames += 1
                draw_pose(frame, pose_list[0], connections)

            overlay_text(frame, processed, detected)
            writer.write(frame)
            processed += 1
    finally:
        cap.release()
        writer.release()
        close = getattr(landmarker, "close", None)
        if close is not None:
            close()

    elapsed = max(time.time() - start, 1e-9)
    runtime_fps = processed / elapsed
    detection_rate = (detected_frames / processed) if processed else 0.0

    print("MediaPipe Pose VIDEO-mode smoke test")
    print(f"  video path        : {video_path}")
    print(f"  model path        : {model_path}")
    print(f"  output path       : {out_path}")
    print(f"  video fps/size     : {fps:.2f} @ {width}x{height}")
    print(f"  processed frames  : {processed}")
    print(f"  detected frames   : {detected_frames}")
    print(f"  detection rate    : {detection_rate:.3f}")
    print(f"  runtime fps       : {runtime_fps:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
