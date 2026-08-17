"""MediaPipe Pose Landmarker VIDEO-mode 3D smoke test (heavy by default).

Renders a side-by-side video:
  - left  : original frame with the 2D pose overlay
  - right : matplotlib 3D skeleton from result.pose_world_landmarks
            (real-world meters, origin at the mid-hip)

Qualitative-only tool, like mediapipe_pose_video_smoke.py, but it also
visualizes the world-landmark 3D coordinate frame. It uses the MediaPipe Tasks
API PoseLandmarker in RunningMode.VIDEO with detect_for_video().

Does not touch RTMPose, MotionAGFormer, the iOS app, or model conversion.

Example:
  python tools/smoke/mediapipe_pose_video_3d_smoke.py \
    --video assets/pushup/pushup_02.mp4 \
    --model assets/mediapipe/pose_landmarker_heavy.task \
    --out outputs/pushup_02_pose_heavy_3d.mp4
"""

import argparse
import math
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mpl_cache")

import cv2  # noqa: E402
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VIDEO = ROOT / "assets/pushup/pushup_02.mp4"
DEFAULT_MODEL = ROOT / "assets/mediapipe/pose_landmarker_heavy.task"
DEFAULT_OUT = ROOT / "outputs/pushup_02_pose_heavy_3d.mp4"

# BlazePose 33-landmark skeleton connections.
POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
    (25, 27), (26, 28), (27, 29), (28, 30), (29, 31),
    (30, 32), (27, 31), (28, 32),
    (15, 17), (15, 19), (15, 21), (16, 18), (16, 20), (16, 22),
    (0, 11), (0, 12),
]

MODEL_MISSING_MSG = """
Pose Landmarker model file not found: {path}

Get it with the bundled helper:
  python tools/smoke/download_pose_landmarker.py --variant heavy
"""


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", default=str(DEFAULT_VIDEO))
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--max-frames", type=int, default=0, help="0 = full video")
    parser.add_argument("--panel-height", type=int, default=720, help="output panel height px")
    parser.add_argument(
        "--output-frame-dir",
        default=None,
        help="Optional directory for saved side-by-side JPEG frames.",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=15,
        help="Save one image every N processed frames when --output-frame-dir is set.",
    )
    parser.add_argument(
        "--max-saved-frames",
        type=int,
        default=0,
        help="0 = no cap on saved JPEG frames.",
    )
    parser.add_argument(
        "--contact-sheet",
        default=None,
        help="Optional JPEG contact sheet built from saved side-by-side frames.",
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
    return mp, vision.PoseLandmarker.create_from_options(options)


def draw_pose_2d(frame, landmarks):
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for a, b in POSE_CONNECTIONS:
        if a < len(pts) and b < len(pts):
            cv2.line(frame, pts[a], pts[b], (0, 255, 0), 2)
    for x, y in pts:
        cv2.circle(frame, (x, y), 3, (0, 0, 255), -1)


def render_3d_panel(fig, ax, world_landmarks, size, frame_index, detected):
    """Render the world-landmark 3D skeleton into a BGR image of (size, size)."""
    ax.clear()
    ax.set_title(f"MediaPipe Pose HEAVY 3D  frame {frame_index}  detected={str(detected).lower()}",
                 fontsize=9)
    # Plot mapping: vertical axis = -y (MP y points down), depth = z.
    if detected and world_landmarks:
        xs = np.array([lm.x for lm in world_landmarks])
        ys = np.array([lm.y for lm in world_landmarks])
        zs = np.array([lm.z for lm in world_landmarks])
        px, py, pz = xs, zs, -ys  # plot-space axes
        for a, b in POSE_CONNECTIONS:
            if a < len(px) and b < len(px):
                ax.plot([px[a], px[b]], [py[a], py[b]], [pz[a], pz[b]],
                        color="tab:green", linewidth=1.5)
        ax.scatter(px, py, pz, c="red", s=12, depthshade=False)
        lim = float(np.max(np.abs(np.concatenate([px, py, pz])))) * 1.1 or 1.0
    else:
        lim = 1.0
        ax.text2D(0.5, 0.5, "no pose", ha="center", transform=ax.transAxes)

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_zlim(-lim, lim)
    ax.set_xlabel("x (m)")
    ax.set_ylabel("z depth (m)")
    ax.set_zlabel("-y up (m)")
    ax.view_init(elev=12, azim=-60)

    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())[..., :3]
    bgr = cv2.cvtColor(buf, cv2.COLOR_RGB2BGR)
    return cv2.resize(bgr, (size, size))


def should_save_frame(frame_index, saved_count, args):
    if not args.output_frame_dir:
        return False
    if args.max_saved_frames and saved_count >= args.max_saved_frames:
        return False
    interval = max(1, int(args.save_every))
    return frame_index % interval == 0


def write_contact_sheet(frame_paths, output_path, thumb_width=420, cols=3):
    if not frame_paths:
        return False
    images = [cv2.imread(str(path)) for path in frame_paths]
    images = [image for image in images if image is not None]
    if not images:
        return False

    first_h, first_w = images[0].shape[:2]
    thumb_height = int(round(thumb_width * first_h / first_w))
    thumbs = [cv2.resize(image, (thumb_width, thumb_height)) for image in images]

    rows = int(math.ceil(len(thumbs) / cols))
    canvas = np.full((rows * thumb_height, cols * thumb_width, 3), 255, dtype=np.uint8)
    for idx, thumb in enumerate(thumbs):
        row = idx // cols
        col = idx % cols
        y1 = row * thumb_height
        x1 = col * thumb_width
        canvas[y1:y1 + thumb_height, x1:x1 + thumb_width] = thumb

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(output_path), canvas))


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

    panel_h = args.panel_height
    video_panel_w = int(round(panel_h * width / height))
    out_w = video_panel_w + panel_h  # video panel + square 3D panel
    out_h = panel_h

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (out_w, out_h),
    )
    if not writer.isOpened():
        print(f"Failed to open output video writer: {out_path}")
        return 1

    frame_dir = Path(args.output_frame_dir) if args.output_frame_dir else None
    if frame_dir is not None:
        frame_dir.mkdir(parents=True, exist_ok=True)
    saved_frame_paths = []

    mp, landmarker = build_landmarker(args)
    fig = plt.figure(figsize=(5, 5), dpi=100)
    ax = fig.add_subplot(111, projection="3d")

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
            timestamp_ms = int(processed * (1000.0 / fps))
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            pose_2d = getattr(result, "pose_landmarks", None) or []
            pose_world = getattr(result, "pose_world_landmarks", None) or []
            detected = len(pose_2d) > 0
            if detected:
                detected_frames += 1
                draw_pose_2d(frame, pose_2d[0])

            left = cv2.resize(frame, (video_panel_w, panel_h))
            world = pose_world[0] if pose_world else None
            right = render_3d_panel(fig, ax, world, panel_h, processed, detected)

            combined = np.hstack([left, right])
            writer.write(combined)
            if should_save_frame(processed, len(saved_frame_paths), args):
                frame_path = frame_dir / f"frame_{processed:05d}.jpg"
                if cv2.imwrite(str(frame_path), combined):
                    saved_frame_paths.append(frame_path)
            processed += 1
    finally:
        cap.release()
        writer.release()
        plt.close(fig)
        close = getattr(landmarker, "close", None)
        if close is not None:
            close()

    contact_sheet_written = False
    if args.contact_sheet:
        contact_sheet_written = write_contact_sheet(saved_frame_paths, args.contact_sheet)

    elapsed = max(time.time() - start, 1e-9)
    print("MediaPipe Pose VIDEO-mode 3D smoke test")
    print(f"  video path        : {video_path}")
    print(f"  model path        : {model_path}")
    print(f"  output path       : {out_path}")
    print(f"  output size       : {out_w}x{out_h}")
    print(f"  processed frames  : {processed}")
    print(f"  detected frames   : {detected_frames}")
    print(f"  detection rate    : {(detected_frames / processed) if processed else 0.0:.3f}")
    if frame_dir is not None:
        print(f"  saved frame dir   : {frame_dir}")
        print(f"  saved image count : {len(saved_frame_paths)}")
    if args.contact_sheet:
        print(f"  contact sheet     : {args.contact_sheet}")
        print(f"  contact written   : {str(contact_sheet_written).lower()}")
    print(f"  runtime fps       : {processed / elapsed:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
