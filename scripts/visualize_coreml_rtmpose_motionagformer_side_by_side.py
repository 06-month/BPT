import argparse
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np


os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mpl_cache")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/bpt_xdg_cache")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from pose_feedback.body.motionagformer_adapter import motionagformer_angles  # noqa: E402
from pose_feedback.hand.hand_3d_overlay import (  # noqa: E402
    HAND_3D_CONNECTIONS,
    build_hand_3d_overlay,
)
from visualize_2d_video_with_uplift_3d_side_by_side import (  # noqa: E402
    draw_coco17,
    drawing_sizes,
    make_writer,
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
    parser = argparse.ArgumentParser(
        description="Visualize CoreML RTMPose-s 2D and MotionAGFormer-XS 3D side-by-side.",
    )
    parser.add_argument("--video", default="assets/smoke/vedio_1.mp4")
    parser.add_argument(
        "--rtmpose-jsonl",
        default="assets/coreml_pipeline/jsonl/vedio_1_coreml_rtmpose_s_2d.jsonl",
    )
    parser.add_argument(
        "--motionagformer-npz",
        default="assets/coreml_pipeline/npz/vedio_1_coreml_motionagformer_xs_3d.npz",
    )
    parser.add_argument(
        "--output-video",
        default="assets/coreml_pipeline/videos/vedio_1_coreml_motionagformer_xs_lookahead5_preferred_style.mp4",
    )
    parser.add_argument("--view-preset", choices=("front", "side", "top", "stack"), default="front")
    parser.add_argument("--axis-preset", choices=("raw", "user"), default="user")
    parser.add_argument("--marker-scale", type=float, default=0.6)
    parser.add_argument("--max-frames", type=int, default=240)
    parser.add_argument("--hand-jsonl", default=None)
    parser.add_argument("--draw-3d-hands", action="store_true")
    parser.add_argument(
        "--hand-3d-mode",
        choices=("none", "local", "wrist-anchored"),
        default="none",
    )
    parser.add_argument("--hand-3d-scale", type=float, default=1.0)
    parser.add_argument("--hand-3d-axis-map", default="x,y,z")
    parser.add_argument("--hand-3d-flip-x", action="store_true")
    parser.add_argument("--hand-3d-flip-y", action="store_true")
    parser.add_argument("--hand-3d-flip-z", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    import cv2

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        print({"video_opened": False, "video": args.video})
        return 0

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0
    image_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    image_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sizes = drawing_sizes(image_w, image_h, args.marker_scale)
    rtmpose = load_rtmpose_jsonl(Path(args.rtmpose_jsonl))
    hand_rows = load_hand_jsonl(None if args.hand_jsonl is None else Path(args.hand_jsonl))
    joints_3d, source_frame_indices, key_used = load_coreml_motionagformer_npz(Path(args.motionagformer_npz))

    output_path = Path(args.output_video)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = make_writer(output_path, fps, image_w * 2, image_h)

    rendered = 0
    max_frames = min(args.max_frames, len(joints_3d), frame_count if frame_count > 0 else len(joints_3d))
    for idx in range(max_frames):
        source_frame_idx = int(source_frame_indices[idx]) if idx < len(source_frame_indices) else idx
        cap.set(cv2.CAP_PROP_POS_FRAMES, source_frame_idx)
        ok, frame = cap.read()
        if not ok:
            continue

        left = frame.copy()
        row = rtmpose.get(source_frame_idx)
        if row is not None:
            keypoints = row.get("coco17_keypoints") or row.get("keypoints_coco17")
            if keypoints is not None:
                draw_coco17(left, np.asarray(keypoints, dtype="float32"), sizes)
        draw_panel_label(left, f"RTMPose-s CoreML 2D | frame {source_frame_idx}", sizes)
        hand_3d = build_hand_3d_from_json_row(
            hand_rows.get(source_frame_idx),
            joints_3d[idx],
            args,
        )

        right = render_right_panel(
            joints=joints_3d[idx],
            window_idx=idx,
            source_frame_idx=source_frame_idx,
            width=image_w,
            height=image_h,
            view_preset=args.view_preset,
            axis_preset=args.axis_preset,
            hand_3d=hand_3d,
        )
        writer.write(np.concatenate([left, right], axis=1))
        rendered += 1

    cap.release()
    writer.release()
    print(
        {
            "video_created": True,
            "output_video": str(output_path),
            "rendered_frames": rendered,
            "fps": fps,
            "view_preset": args.view_preset,
            "npz_3d_key_used": key_used,
            "h36m17_skeleton": "MotionAGFormer H36M17",
            "hand_jsonl": None if args.hand_jsonl is None else args.hand_jsonl,
            "draw_3d_hands": args.draw_3d_hands,
            "hand_3d_mode": args.hand_3d_mode if args.draw_3d_hands else "none",
        },
    )
    return 0


def load_rtmpose_jsonl(path):
    rows = {}
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            frame_idx = row.get("frame_index", row.get("frame_idx"))
            if frame_idx is not None:
                rows[int(frame_idx)] = row
    return rows


def load_hand_jsonl(path):
    if path is None or not path.exists():
        return {}
    rows = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            frame_idx = row.get("frame_index", row.get("frame_idx"))
            if frame_idx is not None:
                rows[int(frame_idx)] = row
    return rows


def build_hand_3d_from_json_row(row, body_joints_3d, args):
    if not args.draw_3d_hands or args.hand_3d_mode == "none" or row is None:
        return None
    return {
        side: build_hand_3d_overlay(
            hand_result=json_hand_result(row.get(f"{side}_hand_world_landmarks")),
            body_joints_3d=body_joints_3d,
            side=side,
            mode=args.hand_3d_mode,
            scale=args.hand_3d_scale,
            axis_map=args.hand_3d_axis_map,
            flip_x=args.hand_3d_flip_x,
            flip_y=args.hand_3d_flip_y,
            flip_z=args.hand_3d_flip_z,
        )
        for side in ("left", "right")
    }


def json_hand_result(world_landmarks):
    if world_landmarks is None:
        return None
    landmarks = [
        SimpleNamespace(x=float(point[0]), y=float(point[1]), z=float(point[2]))
        for point in world_landmarks
    ]
    return {"hand_world_landmarks": SimpleNamespace(landmark=landmarks)}


def load_coreml_motionagformer_npz(path):
    if not path.exists():
        raise FileNotFoundError(f"MotionAGFormer CoreML NPZ not found: {path}")
    data = np.load(path, allow_pickle=True)
    if "frame_indices" in data.files:
        source_frame_indices = np.asarray(data["frame_indices"], dtype=int)
    else:
        source_frame_indices = np.arange(len(data["pred_3d"]), dtype=int)

    if "pred_3d_selected" in data.files:
        joints = np.asarray(data["pred_3d_selected"], dtype="float32")
        if joints.ndim != 3 or joints.shape[-2:] != (17, 3):
            raise ValueError(f"pred_3d_selected must have shape [N, 17, 3], got {joints.shape}")
        return joints, source_frame_indices, "pred_3d_selected"

    if "pred_3d" not in data.files:
        raise KeyError(f"No pred_3d_selected or pred_3d in {path}; keys={list(data.files)}")
    pred = np.asarray(data["pred_3d"], dtype="float32")
    if pred.ndim == 3 and pred.shape[-2:] == (17, 3):
        return pred, source_frame_indices, "pred_3d"
    if pred.ndim != 4 or pred.shape[-2:] != (17, 3):
        raise ValueError(f"pred_3d must have shape [N, 17, 3] or [N, T, 17, 3], got {pred.shape}")
    latency_frames = int(np.asarray(data["latency_frames"])[0]) if "latency_frames" in data.files else 5
    target_idx = int(np.clip(pred.shape[1] - latency_frames - 1, 0, pred.shape[1] - 1))
    return pred[:, target_idx], source_frame_indices, f"pred_3d[:, {target_idx}]"


def draw_panel_label(image, text, sizes):
    import cv2

    cv2.putText(
        image,
        text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        sizes["font_scale"],
        (255, 255, 255),
        sizes["text_thickness"] + 1,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        sizes["font_scale"],
        (0, 0, 0),
        sizes["text_thickness"],
        cv2.LINE_AA,
    )


def render_right_panel(joints, window_idx, source_frame_idx, width, height, view_preset, axis_preset, hand_3d=None):
    if view_preset == "stack":
        return render_3d_stack(
            joints=joints,
            window_idx=window_idx,
            source_frame_idx=source_frame_idx,
            width=width,
            height=height,
            axis_preset=axis_preset,
            hand_3d=hand_3d,
        )
    return render_3d_panel(
        joints=joints,
        window_idx=window_idx,
        source_frame_idx=source_frame_idx,
        width=width,
        height=height,
        view=view_preset,
        axis_preset=axis_preset,
        include_detail_text=True,
        hand_3d=hand_3d,
    )


def render_3d_stack(joints, window_idx, source_frame_idx, width, height, axis_preset, hand_3d=None):
    import numpy as _np

    top_h = height // 3
    mid_h = height // 3
    bottom_h = height - top_h - mid_h
    return _np.vstack(
        [
            render_3d_panel(joints, window_idx, source_frame_idx, width, top_h, "front", axis_preset, True, hand_3d),
            render_3d_panel(joints, window_idx, source_frame_idx, width, mid_h, "side", axis_preset, False, hand_3d),
            render_3d_panel(joints, window_idx, source_frame_idx, width, bottom_h, "top", axis_preset, False, hand_3d),
        ],
    )


def render_3d_panel(
    joints,
    window_idx,
    source_frame_idx,
    width,
    height,
    view,
    axis_preset,
    include_detail_text,
    hand_3d=None,
):
    import cv2
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    points, labels = transform_for_view(joints, axis_preset)
    angles = motionagformer_angles(joints)
    transformed_hands = transform_hands_for_view(hand_3d, axis_preset)
    fig = plt.figure(figsize=(width / 120.0, max(1.2, height / 120.0)), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    for a, b in H36M_SKELETON:
        color = "tab:gray"
        if {a, b}.issubset({1, 2, 3, 14, 15, 16}):
            color = "tab:red"
        elif {a, b}.issubset({4, 5, 6, 11, 12, 13}):
            color = "tab:green"
        segment = points[[a, b]]
        ax.plot(segment[:, 0], segment[:, 1], segment[:, 2], color=color, linewidth=2.4)
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], c="black", s=14)
    for side, hand_points in transformed_hands.items():
        color = "tab:blue" if side == "left" else "tab:purple"
        draw_hand_3d(ax, hand_points, color=color, label=f"{side} hand")
    all_points = points
    if transformed_hands:
        all_points = np.vstack([points, *transformed_hands.values()])
    set_equal_axes(ax, all_points)
    ax.set_xlabel(labels[0], fontsize=8)
    ax.set_ylabel(labels[1], fontsize=8)
    ax.set_zlabel(labels[2], fontsize=8)
    ax.set_title(f"MotionAGFormer-XS CoreML 3D / lookahead5 | {view}", fontsize=10)
    elev, azim = view_angles(view)
    ax.view_init(elev=elev, azim=azim)
    text = [
        f"window {window_idx}",
        f"frame {source_frame_idx}",
        "latency 5f / 0.17s",
    ]
    if include_detail_text:
        text.extend(
            [
                f"L elbow {fmt(angles['left_elbow'])}",
                f"R elbow {fmt(angles['right_elbow'])}",
                f"L knee {fmt(angles['left_knee'])}",
                f"R knee {fmt(angles['right_knee'])}",
            ],
        )
    ax.text2D(0.02, 0.98, "\n".join(text), transform=ax.transAxes, va="top", fontsize=8)
    fig.tight_layout()
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    image = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    plt.close(fig)
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def transform_for_view(joints, axis_preset):
    points = np.asarray(joints, dtype="float32")
    return transform_points_for_view(points, axis_preset)


def transform_points_for_view(points, axis_preset):
    points = np.asarray(points, dtype="float32")
    if axis_preset == "raw":
        return points.copy(), ("raw x", "raw y", "raw z")
    out = np.empty_like(points)
    out[:, 0] = points[:, 0]
    out[:, 1] = points[:, 2]
    out[:, 2] = -points[:, 1]
    return out, ("x: left-right", "y: depth", "z: up")


def transform_hands_for_view(hand_3d, axis_preset):
    if not hand_3d:
        return {}
    transformed = {}
    for side, payload in hand_3d.items():
        if not payload or not payload.get("available") or payload.get("draw_landmarks") is None:
            continue
        points, _ = transform_points_for_view(payload["draw_landmarks"], axis_preset)
        if points.shape == (21, 3):
            transformed[side] = points
    return transformed


def draw_hand_3d(ax, points, color, label):
    for a, b in HAND_3D_CONNECTIONS:
        segment = points[[a, b]]
        ax.plot(segment[:, 0], segment[:, 1], segment[:, 2], color=color, linewidth=1.6, alpha=0.95)
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], c=color, s=8, label=label)


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
