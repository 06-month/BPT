import argparse
import json
import os
from pathlib import Path
import sys

import numpy as np


os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mpl_cache")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.motionagformer_adapter import motionagformer_angles
from visualize_2d_video_with_uplift_3d_side_by_side import (
    draw_coco17,
    drawing_sizes,
    make_writer,
    read_frame,
)


H36M_SKELETON = [
    (0, 1),
    (1, 2),
    (2, 3),
    (0, 4),
    (4, 5),
    (5, 6),
    (0, 7),
    (7, 8),
    (8, 9),
    (9, 10),
    (8, 11),
    (11, 12),
    (12, 13),
    (8, 14),
    (14, 15),
    (15, 16),
]


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize MotionAGFormer 2D/3D side-by-side smoke output.")
    parser.add_argument("--video", default="assets/smoke/vedio_1.mp4")
    parser.add_argument("--rtmpose-jsonl", default="assets/smoke/vedio_1_rtmpose_2d_keypoints.jsonl")
    parser.add_argument("--mode", choices=("full", "lookahead3", "lookahead5"), default="lookahead5")
    parser.add_argument("--motionagformer-npz", default=None)
    parser.add_argument(
        "--output-video",
        default="assets/smoke/vedio_1_motionagformer_lookahead5_2d_3d_side_by_side.mp4",
    )
    parser.add_argument("--marker-scale", type=float, default=0.6)
    parser.add_argument("--max-frames", type=int, default=240)
    parser.add_argument("--axis-preset", choices=("raw", "user"), default="user")
    return parser.parse_args()


def main():
    args = parse_args()
    import cv2

    motionagformer_npz = args.motionagformer_npz or default_motionagformer_npz(args.mode)
    if not Path(motionagformer_npz).exists():
        print({"video_created": False, "reason": "missing_motionagformer_output", "path": motionagformer_npz})
        return 0
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print({"video_opened": False, "video": args.video})
        return 0
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0
    image_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    image_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sizes = drawing_sizes(image_w, image_h, args.marker_scale)
    rtmpose = load_rtmpose_jsonl(Path(args.rtmpose_jsonl))
    data = np.load(motionagformer_npz, allow_pickle=True)
    pred, frame_indices, latency_frames, latency_sec, mode = resolved_predictions(data, args.mode)

    writer = make_writer(Path(args.output_video), fps, image_w * 2, image_h)
    rendered = 0
    for idx, joints in enumerate(pred[: args.max_frames]):
        source_frame_idx = int(frame_indices[idx]) if idx < len(frame_indices) else idx
        ok, frame = read_frame(cap, source_frame_idx)
        if not ok:
            continue
        left = frame.copy()
        row = rtmpose.get(source_frame_idx)
        if row and row.get("keypoints_coco17") is not None:
            draw_coco17(left, np.asarray(row["keypoints_coco17"], dtype="float32"), sizes)
        draw_label(left, f"RTMPose 2D | frame {source_frame_idx}", sizes)
        right = render_3d_stack(
            joints=joints,
            angles=motionagformer_angles(joints),
            window_idx=idx,
            source_frame_idx=source_frame_idx,
            width=image_w,
            height=image_h,
            axis_preset=args.axis_preset,
            mode=mode,
            latency_frames=latency_frames,
            latency_sec=latency_sec,
        )
        writer.write(np.concatenate([left, right], axis=1))
        rendered += 1
    cap.release()
    writer.release()
    print(
        {
            "video_created": True,
            "mode": mode,
            "latency_frames": latency_frames,
            "latency_sec": latency_sec,
            "rendered_frames": rendered,
            "output_video": args.output_video,
        },
    )
    return 0


def load_rtmpose_jsonl(path):
    rows = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                rows[int(row["frame_idx"])] = row
    return rows


def default_motionagformer_npz(mode):
    return f"assets/smoke/vedio_1_motionagformer_{mode}_all.npz"


def resolved_predictions(data, fallback_mode):
    pred = np.asarray(data["pred_3d"], dtype="float32")
    latency_frames = int(np.asarray(data["latency_frames"])[0]) if "latency_frames" in data.files else latency_for_mode(fallback_mode)
    latency_sec = float(np.asarray(data["latency_sec"])[0]) if "latency_sec" in data.files else latency_frames / 30.0
    mode = str(np.asarray(data["mode"])[0]) if "mode" in data.files else fallback_mode
    frame_indices = data["frame_indices"]
    if frame_indices.ndim == 2:
        if pred.ndim == 4:
            output_idx = int(np.clip(frame_indices.shape[1] - latency_frames - 1, 0, frame_indices.shape[1] - 1))
            return pred[:, output_idx], frame_indices[:, output_idx], latency_frames, latency_sec, mode
        return pred, frame_indices[:, frame_indices.shape[1] // 2], latency_frames, latency_sec, mode
    return pred, frame_indices, latency_frames, latency_sec, mode


def latency_for_mode(mode):
    if mode == "full":
        return 121
    if mode == "lookahead3":
        return 3
    if mode == "lookahead5":
        return 5
    return 0


def draw_label(image, text, sizes):
    import cv2

    cv2.putText(
        image,
        text,
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        sizes["font_scale"],
        (255, 255, 255),
        sizes["text_thickness"],
        cv2.LINE_AA,
    )


def render_3d_stack(
    joints,
    angles,
    window_idx,
    source_frame_idx,
    width,
    height,
    axis_preset,
    mode,
    latency_frames,
    latency_sec,
):
    import cv2

    heights = [height // 3, height // 3, height - 2 * (height // 3)]
    panels = [
        render_3d_panel(
            joints,
            angles,
            window_idx,
            source_frame_idx,
            width,
            heights[0],
            "front",
            axis_preset,
            True,
            mode,
            latency_frames,
            latency_sec,
        ),
        render_3d_panel(
            joints,
            angles,
            window_idx,
            source_frame_idx,
            width,
            heights[1],
            "side",
            axis_preset,
            False,
            mode,
            latency_frames,
            latency_sec,
        ),
        render_3d_panel(
            joints,
            angles,
            window_idx,
            source_frame_idx,
            width,
            heights[2],
            "top",
            axis_preset,
            False,
            mode,
            latency_frames,
            latency_sec,
        ),
    ]
    return np.vstack(panels)


def render_3d_panel(
    joints,
    angles,
    window_idx,
    source_frame_idx,
    width,
    height,
    view,
    axis_preset,
    detail,
    mode,
    latency_frames,
    latency_sec,
):
    import cv2
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    points, labels = transform_for_view(joints, axis_preset)
    fig = plt.figure(figsize=(width / 120.0, max(1.2, height / 120.0)), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    for a, b in H36M_SKELETON:
        color = "tab:gray"
        if {a, b}.issubset({1, 2, 3, 14, 15, 16}):
            color = "tab:red"
        elif {a, b}.issubset({4, 5, 6, 11, 12, 13}):
            color = "tab:green"
        segment = points[[a, b]]
        ax.plot(segment[:, 0], segment[:, 1], segment[:, 2], color=color, linewidth=2.2)
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], c="black", s=12)
    set_equal_axes(ax, points)
    ax.set_xlabel(labels[0], fontsize=7)
    ax.set_ylabel(labels[1], fontsize=7)
    ax.set_zlabel(labels[2], fontsize=7)
    ax.set_title(f"MotionAGFormer 3D {view} | {mode}", fontsize=9)
    elev, azim = view_angles(view)
    ax.view_init(elev=elev, azim=azim)
    text = [
        f"window {window_idx}",
        f"frame {source_frame_idx}",
        f"latency {latency_frames}f / {latency_sec:.2f}s",
    ]
    if detail:
        text.extend(
            [
                f"L elbow {fmt(angles['left_elbow'])}",
                f"R elbow {fmt(angles['right_elbow'])}",
                f"L knee {fmt(angles['left_knee'])}",
                f"R knee {fmt(angles['right_knee'])}",
            ],
        )
    ax.text2D(0.02, 0.98, "\n".join(text), transform=ax.transAxes, va="top", fontsize=7)
    fig.tight_layout()
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    image = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    plt.close(fig)
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def transform_for_view(joints, axis_preset):
    points = np.asarray(joints, dtype="float32")
    if axis_preset == "raw":
        return points.copy(), ("raw x", "raw y", "raw z")
    out = np.empty_like(points)
    out[:, 0] = points[:, 0]
    out[:, 1] = points[:, 2]
    out[:, 2] = -points[:, 1]
    return out, ("x: left-right", "y: depth", "z: up")


def set_equal_axes(ax, points):
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    centers = (mins + maxs) / 2.0
    radius = float(np.max(maxs - mins) / 2.0)
    if radius <= 1e-8:
        radius = 1.0
    ax.set_xlim(centers[0] - radius, centers[0] + radius)
    ax.set_ylim(centers[1] - radius, centers[1] + radius)
    ax.set_zlim(centers[2] - radius, centers[2] + radius)


def view_angles(view):
    if view == "side":
        return 12, 0
    if view == "top":
        return 85, -90
    return 12, -90


def fmt(value):
    return "None" if value is None else f"{float(value):.1f}"


if __name__ == "__main__":
    raise SystemExit(main())
