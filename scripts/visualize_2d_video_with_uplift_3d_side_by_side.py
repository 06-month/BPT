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

from pose_feedback.geometry.angles_3d import angle_3d


COCO_NAMES = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]
COCO_SKELETON = [
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (0, 1),
    (0, 2),
    (1, 3),
    (2, 4),
]

H36M17_NAMES = [
    "r_ankle",
    "r_knee",
    "r_hip",
    "l_hip",
    "l_knee",
    "l_ankle",
    "pelvis",
    "neck",
    "torso",
    "head",
    "head_top",
    "r_wrist",
    "r_elbow",
    "r_shoulder",
    "l_shoulder",
    "l_elbow",
    "l_wrist",
]
H36M17_SKELETON = [
    (6, 2),
    (2, 1),
    (1, 0),
    (6, 3),
    (3, 4),
    (4, 5),
    (6, 8),
    (8, 7),
    (7, 9),
    (9, 10),
    (7, 13),
    (13, 12),
    (12, 11),
    (7, 14),
    (14, 15),
    (15, 16),
]
HAND_CONNECTIONS = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (0, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (0, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (0, 17),
    (17, 18),
    (18, 19),
    (19, 20),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create synchronized 2D RTMPose/MediaPipe and Uplift 3D side-by-side video.",
    )
    parser.add_argument("--video", default="assets/smoke/vedio_1.mp4")
    parser.add_argument(
        "--rtmpose-log-jsonl",
        default="assets/smoke/vedio_1_rtmpose_body_both_hands_log.jsonl",
    )
    parser.add_argument(
        "--uplift-input-npz",
        default="assets/smoke/vedio_1_uplift_input_debug.npz",
    )
    parser.add_argument(
        "--uplift-output-npz",
        default="assets/smoke/vedio_1_uplift_3d_output_debug.npz",
    )
    parser.add_argument(
        "--output-video",
        default="assets/smoke/vedio_1_2d_3d_side_by_side.mp4",
    )
    parser.add_argument("--max-frames", type=int, default=240)
    parser.add_argument("--marker-scale", type=float, default=0.6)
    parser.add_argument("--view-preset", choices=("front", "side", "top"), default="front")
    parser.add_argument("--axis-preset", choices=("raw", "user"), default="user")
    parser.add_argument("--fps", type=float, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.max_frames < 1:
        raise ValueError("--max-frames must be >= 1")

    import cv2

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        print({"video_opened": False, "video": args.video})
        return 0

    video_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if video_fps <= 1e-6:
        video_fps = 30.0
    output_fps = args.fps if args.fps is not None else video_fps
    image_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    image_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sizes = drawing_sizes(image_w, image_h, args.marker_scale)

    uplift_input = load_uplift_input(Path(args.uplift_input_npz))
    pred_key, pred_3d = load_uplift_predictions(Path(args.uplift_output_npz))
    frame_indices = center_frame_indices(uplift_input, len(pred_3d))
    log_by_frame, log_fields = load_jsonl_by_frame(Path(args.rtmpose_log_jsonl))

    output_path = Path(args.output_video)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = make_writer(output_path, output_fps, image_w * 2, image_h)

    composed = 0
    source_frame_values = []
    body_keypoints_drawn = False
    crop_boxes_drawn = False
    hand_landmarks_drawn = False
    missing_fields = set()

    for window_idx, source_frame_idx in enumerate(frame_indices[: args.max_frames]):
        ok, frame = read_frame(cap, source_frame_idx)
        if not ok:
            missing_fields.add("video_frame")
            continue

        left_panel = frame.copy()
        log_row = log_by_frame.get(int(source_frame_idx))
        coco17 = keypoints_for_source_frame(uplift_input, int(source_frame_idx))
        if coco17 is not None:
            draw_coco17(left_panel, coco17, sizes)
            body_keypoints_drawn = True
        else:
            missing_fields.add("raw_coco17")

        if log_row is not None:
            crop_boxes_drawn |= draw_log_crop_boxes(left_panel, log_row, sizes)
            if not log_has_hand_landmarks(log_row):
                missing_fields.add("hand_landmarks")
        else:
            missing_fields.add("rtmpose_log_frame")

        if log_has_hand_landmarks(log_row):
            hand_landmarks_drawn |= draw_logged_hand_landmarks(left_panel, log_row, sizes)

        timestamp_sec = float(source_frame_idx) / video_fps
        left_lines = [
            "2D RTMPose + MediaPipe",
            f"source_frame_idx: {source_frame_idx}",
            f"timestamp_sec: {timestamp_sec:.3f}",
        ]
        if coco17 is None:
            left_lines.append("RTMPose keypoints unavailable in inputs")
        if not log_has_hand_landmarks(log_row):
            left_lines.append("MediaPipe landmarks unavailable in JSONL")
        draw_text_box(left_panel, left_lines, (10, 10), sizes)

        joints = np.asarray(pred_3d[window_idx], dtype=np.float32)
        angles = compute_angles(joints)
        right_panel = render_3d_stack(
            joints=joints,
            angles=angles,
            window_idx=window_idx,
            source_frame_idx=int(source_frame_idx),
            width=image_w,
            height=image_h,
            axis_preset=args.axis_preset,
        )

        combined = np.concatenate([left_panel, right_panel], axis=1)
        writer.write(combined)
        composed += 1
        source_frame_values.append(int(source_frame_idx))

    cap.release()
    writer.release()

    summary = {
        "video_opened": True,
        "video": args.video,
        "uplift_prediction_key": pred_key,
        "uplift_predictions": int(len(pred_3d)),
        "composed_frames": composed,
        "first_source_frame_idx": source_frame_values[0] if source_frame_values else None,
        "last_source_frame_idx": source_frame_values[-1] if source_frame_values else None,
        "output_video": str(output_path),
        "body_2d_keypoints_drawn": body_keypoints_drawn,
        "crop_boxes_drawn": crop_boxes_drawn,
        "mediapipe_hand_landmarks_drawn": hand_landmarks_drawn,
        "front_side_top_3d_panels_drawn": composed > 0,
        "missing_2d_fields": sorted(missing_fields),
        "jsonl_fields": sorted(log_fields),
    }
    print(summary)
    return 0


def load_uplift_predictions(path):
    if not path.exists():
        raise FileNotFoundError(f"Uplift output NPZ not found: {path}")
    data = np.load(path, allow_pickle=True)
    for key in ("pred_3d_central", "pred_3d", "output", "predictions", "pred_3d_full"):
        if key not in data.files:
            continue
        arr = np.asarray(data[key])
        if arr.ndim == 3 and arr.shape[-2:] == (17, 3):
            return key, arr.astype(np.float32)
        if arr.ndim == 4 and arr.shape[-2:] == (17, 3):
            center_idx = arr.shape[1] // 2
            return key, arr[:, center_idx].astype(np.float32)
    raise ValueError(
        f"No supported Uplift 3D prediction key found in {path}; keys={list(data.files)}",
    )


def load_uplift_input(path):
    if not path.exists():
        raise FileNotFoundError(f"Uplift input NPZ not found: {path}")
    return np.load(path, allow_pickle=True)


def center_frame_indices(uplift_input, count):
    if "frame_indices" not in uplift_input.files:
        return list(range(count))
    frame_indices = np.asarray(uplift_input["frame_indices"])
    if frame_indices.ndim == 2:
        center_idx = frame_indices.shape[1] // 2
        values = frame_indices[:, center_idx]
    else:
        values = frame_indices
    return [int(value) for value in values[:count]]


def keypoints_for_source_frame(uplift_input, source_frame_idx):
    if "raw_coco17" not in uplift_input.files:
        return None
    raw = np.asarray(uplift_input["raw_coco17"])
    if raw.ndim != 3 or raw.shape[1:] != (17, 3):
        return None
    if source_frame_idx < 0 or source_frame_idx >= len(raw):
        return None
    return raw[source_frame_idx]


def load_jsonl_by_frame(path):
    if not path.exists():
        return {}, set()
    rows = {}
    fields = set()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            fields.update(row.keys())
            if "frame_idx" in row:
                rows[int(row["frame_idx"])] = row
    return rows, fields


def read_frame(cap, frame_idx):
    import cv2

    cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_idx))
    return cap.read()


def make_writer(path, fps, width, height):
    import cv2

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, float(fps), (int(width), int(height)))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {path}")
    return writer


def drawing_sizes(image_w, image_h, marker_scale):
    base = max(1.0, min(image_w, image_h) / 300.0)
    return {
        "body_radius": max(2, int(3 * base * marker_scale)),
        "hand_radius": max(1, int(2 * base * marker_scale)),
        "highlight_radius": max(3, int(4 * base * marker_scale)),
        "line_thickness": max(1, int(2 * base * marker_scale)),
        "font_scale": max(0.35, 0.45 * base * marker_scale),
        "text_thickness": max(1, int(1 * base * marker_scale)),
    }


def draw_coco17(image, keypoints, sizes, conf_threshold=0.3):
    import cv2

    left_color = (255, 90, 40)
    right_color = (0, 165, 255)
    center_color = (80, 220, 80)
    low_color = (130, 130, 130)
    left_indices = {1, 3, 5, 7, 9, 11, 13, 15}
    right_indices = {2, 4, 6, 8, 10, 12, 14, 16}

    for a, b in COCO_SKELETON:
        if keypoints[a, 2] < conf_threshold or keypoints[b, 2] < conf_threshold:
            continue
        pt_a = tuple(np.round(keypoints[a, :2]).astype(int))
        pt_b = tuple(np.round(keypoints[b, :2]).astype(int))
        color = center_color
        if a in left_indices and b in left_indices:
            color = left_color
        elif a in right_indices and b in right_indices:
            color = right_color
        cv2.line(image, pt_a, pt_b, color, sizes["line_thickness"], cv2.LINE_AA)

    for idx, (x, y, conf) in enumerate(keypoints):
        color = low_color
        if conf >= conf_threshold:
            if idx in left_indices:
                color = left_color
            elif idx in right_indices:
                color = right_color
            else:
                color = center_color
        point = (int(round(float(x))), int(round(float(y))))
        cv2.circle(image, point, sizes["body_radius"], color, -1, cv2.LINE_AA)
        if conf >= conf_threshold and idx in {5, 6, 7, 8, 9, 10, 13, 14, 15, 16}:
            cv2.putText(
                image,
                f"{idx}",
                (point[0] + 4, point[1] - 4),
                cv2.FONT_HERSHEY_SIMPLEX,
                sizes["font_scale"],
                (255, 255, 255),
                sizes["text_thickness"],
                cv2.LINE_AA,
            )


def draw_log_crop_boxes(image, row, sizes):
    import cv2

    drawn = False
    for side, color in (("left", (255, 255, 0)), ("right", (255, 0, 255))):
        side_row = row.get(side) or {}
        crop_box = side_row.get("crop_box")
        if not crop_box:
            continue
        x1, y1, x2, y2 = [int(round(float(v))) for v in crop_box]
        cv2.rectangle(image, (x1, y1), (x2, y2), color, sizes["line_thickness"], cv2.LINE_AA)
        label = f"{side} crop hand={side_row.get('hand_detected')}"
        cv2.putText(
            image,
            label,
            (x1 + 4, max(16, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            sizes["font_scale"],
            color,
            sizes["text_thickness"],
            cv2.LINE_AA,
        )
        drawn = True
    return drawn


def log_has_hand_landmarks(row):
    if not row:
        return False
    for side in ("left", "right"):
        if get_side_hand_landmarks(row, side):
            return True
    return False


def draw_logged_hand_landmarks(image, row, sizes):
    import cv2

    drawn = False
    for side, base_color in (("left", (0, 220, 80)), ("right", (0, 180, 255))):
        landmarks = get_side_hand_landmarks(row, side)
        if not landmarks:
            continue
        points = []
        for item in landmarks:
            if len(item) < 2:
                continue
            point = (int(round(float(item[0]))), int(round(float(item[1]))))
            points.append(point)
        if len(points) != 21:
            continue
        for a, b in HAND_CONNECTIONS:
            cv2.line(
                image,
                points[a],
                points[b],
                base_color,
                sizes["line_thickness"],
                cv2.LINE_AA,
            )
        for point in points:
            cv2.circle(image, point, sizes["hand_radius"], base_color, -1, cv2.LINE_AA)
        for idx, color in ((0, (0, 0, 255)), (5, (0, 120, 255)), (9, (0, 80, 255)), (17, (0, 160, 255))):
            cv2.circle(
                image,
                points[idx],
                sizes["highlight_radius"],
                color,
                -1,
                cv2.LINE_AA,
            )
        cv2.putText(
            image,
            f"{side} MP wrist",
            (points[0][0] + 5, points[0][1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            sizes["font_scale"],
            (255, 255, 255),
            sizes["text_thickness"],
            cv2.LINE_AA,
        )
        cv2.putText(
            image,
            f"{side} middle",
            (points[9][0] + 5, points[9][1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            sizes["font_scale"],
            (255, 255, 255),
            sizes["text_thickness"],
            cv2.LINE_AA,
        )
        drawn = True
    return drawn


def get_side_hand_landmarks(row, side):
    if not row:
        return None
    top_level = row.get(f"{side}_hand_landmarks_px")
    if top_level:
        return top_level
    side_row = row.get(side) or {}
    nested = side_row.get("hand_landmarks_px") or side_row.get("hand_landmarks")
    if nested:
        return nested
    return None


def draw_text_box(image, lines, origin, sizes):
    import cv2

    x, y = origin
    line_h = max(16, int(24 * sizes["font_scale"]))
    width = min(image.shape[1] - x - 8, 520)
    height = line_h * len(lines) + 12
    y2 = min(image.shape[0] - 4, y + height)
    roi = image[y:y2, x : x + width]
    if roi.size:
        black = np.zeros_like(roi)
        cv2.addWeighted(black, 0.68, roi, 0.32, 0, dst=roi)
    for i, line in enumerate(lines):
        cv2.putText(
            image,
            str(line)[:80],
            (x + 8, y + 18 + i * line_h),
            cv2.FONT_HERSHEY_SIMPLEX,
            sizes["font_scale"],
            (255, 255, 255),
            sizes["text_thickness"],
            cv2.LINE_AA,
        )


def compute_angles(joints):
    return {
        "right_elbow": angle_3d(joints[13], joints[12], joints[11]),
        "left_elbow": angle_3d(joints[14], joints[15], joints[16]),
        "right_knee": angle_3d(joints[2], joints[1], joints[0]),
        "left_knee": angle_3d(joints[3], joints[4], joints[5]),
    }


def transform_for_view(joints, axis_preset):
    joints = np.asarray(joints, dtype=np.float32)
    if axis_preset == "raw":
        return joints.copy(), ("raw x", "raw y", "raw z")
    # Visualization-only transform. Uplift output is root-relative model space,
    # not camera-calibrated world coordinates. This makes axes easier to inspect.
    transformed = np.empty_like(joints)
    transformed[:, 0] = joints[:, 0]
    transformed[:, 1] = joints[:, 2]
    transformed[:, 2] = -joints[:, 1]
    return transformed, ("x: left-right", "y: depth", "z: up")


def render_3d_stack(
    joints,
    angles,
    window_idx,
    source_frame_idx,
    width,
    height,
    axis_preset,
):
    import cv2

    top_h = height // 3
    mid_h = height // 3
    bottom_h = height - top_h - mid_h
    panels = [
        render_3d_panel(
            joints=joints,
            angles=angles,
            window_idx=window_idx,
            source_frame_idx=source_frame_idx,
            width=width,
            height=top_h,
            view_preset="front",
            axis_preset=axis_preset,
            include_detail_text=True,
        ),
        render_3d_panel(
            joints=joints,
            angles=angles,
            window_idx=window_idx,
            source_frame_idx=source_frame_idx,
            width=width,
            height=mid_h,
            view_preset="side",
            axis_preset=axis_preset,
            include_detail_text=False,
        ),
        render_3d_panel(
            joints=joints,
            angles=angles,
            window_idx=window_idx,
            source_frame_idx=source_frame_idx,
            width=width,
            height=bottom_h,
            view_preset="top",
            axis_preset=axis_preset,
            include_detail_text=False,
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
    view_preset,
    axis_preset,
    include_detail_text,
):
    import cv2
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    points, axis_labels = transform_for_view(joints, axis_preset)
    fig = plt.figure(figsize=(width / 120.0, max(1.2, height / 120.0)), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    for a, b in H36M17_SKELETON:
        segment = points[[a, b]]
        color = "tab:gray"
        if {a, b}.issubset({0, 1, 2, 11, 12, 13}):
            color = "tab:red"
        elif {a, b}.issubset({3, 4, 5, 14, 15, 16}):
            color = "tab:green"
        ax.plot(segment[:, 0], segment[:, 1], segment[:, 2], color=color, linewidth=2.5)
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], c="black", s=14)
    for idx in (0, 1, 2, 5, 6, 11, 12, 13, 14, 15, 16):
        ax.text(points[idx, 0], points[idx, 1], points[idx, 2], H36M17_NAMES[idx], fontsize=6)
    set_equal_axes(ax, points)
    ax.set_xlabel(axis_labels[0], fontsize=8)
    ax.set_ylabel(axis_labels[1], fontsize=8)
    ax.set_zlabel(axis_labels[2], fontsize=8)
    ax.set_title(f"3D {view_preset}", fontsize=10)
    elev, azim = view_angles(view_preset)
    ax.view_init(elev=elev, azim=azim)
    text_lines = [f"window_idx: {window_idx}", f"source_frame_idx: {source_frame_idx}"]
    if include_detail_text:
        text_lines.extend(
            [
                f"right_elbow: {fmt_angle(angles['right_elbow'])}",
                f"left_elbow: {fmt_angle(angles['left_elbow'])}",
                f"right_knee: {fmt_angle(angles['right_knee'])}",
                f"left_knee: {fmt_angle(angles['left_knee'])}",
                f"axis: {axis_preset}",
            ],
        )
    ax.text2D(
        0.02,
        0.98,
        "\n".join(text_lines),
        transform=ax.transAxes,
        va="top",
        fontsize=7,
        bbox={"facecolor": "white", "alpha": 0.78, "edgecolor": "none"},
    )
    fig.tight_layout()
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    image = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    plt.close(fig)
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def view_angles(view_preset):
    if view_preset == "side":
        return 12, 0
    if view_preset == "top":
        return 85, -90
    return 12, -90


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


def fmt_angle(value):
    return "None" if value is None else f"{float(value):.1f}"


if __name__ == "__main__":
    raise SystemExit(main())
