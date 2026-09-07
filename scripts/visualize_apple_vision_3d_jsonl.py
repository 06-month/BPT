import argparse
import json
import os
import re
from pathlib import Path

import numpy as np


os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mpl_cache")


# Canonical Apple Vision 3D body joints (17). Note: Apple has NO "neck" joint;
# the head chain is centerShoulder -> centerHead -> topHead. "neck" is kept in
# the requested edge list only so missing-edge accounting is explicit.
LEFT_JOINTS = {"leftHip", "leftKnee", "leftAnkle", "leftShoulder", "leftElbow", "leftWrist"}
RIGHT_JOINTS = {"rightHip", "rightKnee", "rightAnkle", "rightShoulder", "rightElbow", "rightWrist"}

# The skeleton mapping requested for Apple Vision 3D (root-relative, estimated pose).
REQUESTED_EDGES = [
    ("root", "spine"),
    ("spine", "centerShoulder"),
    ("centerShoulder", "neck"),
    ("neck", "topHead"),
    ("centerShoulder", "leftShoulder"),
    ("leftShoulder", "leftElbow"),
    ("leftElbow", "leftWrist"),
    ("centerShoulder", "rightShoulder"),
    ("rightShoulder", "rightElbow"),
    ("rightElbow", "rightWrist"),
    ("root", "leftHip"),
    ("leftHip", "leftKnee"),
    ("leftKnee", "leftAnkle"),
    ("root", "rightHip"),
    ("rightHip", "rightKnee"),
    ("rightKnee", "rightAnkle"),
]


def str2bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize Apple Vision 3D body pose JSONL with connected bones.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--jsonl", required=True)
    parser.add_argument("--output-video", default=None)
    parser.add_argument("--output-side-by-side", required=True)
    parser.add_argument("--max-frames", type=int, default=240)
    parser.add_argument("--draw-bones", nargs="?", const=True, default=True, type=str2bool,
                        help="Draw skeleton bone edges (default: true).")
    parser.add_argument("--draw-joint-labels", nargs="?", const=True, default=False, type=str2bool,
                        help="Draw joint name labels (default: false).")
    return parser.parse_args()


def main():
    args = parse_args()
    import cv2

    jsonl_path = Path(args.jsonl)
    if not jsonl_path.exists():
        print({"visualization_ran": False, "reason": "missing_jsonl", "jsonl": args.jsonl})
        return 0
    rows = load_jsonl(jsonl_path)
    if not rows:
        print({"visualization_ran": False, "reason": "empty_jsonl", "jsonl": args.jsonl})
        return 0

    # ---- inspect joint names (raw + canonical) ----
    raw_names = []
    canon_names = set()
    for row in rows:
        for raw in row.get("raw_joint_names", []) or []:
            if raw not in raw_names:
                raw_names.append(raw)
        for raw in row.get("joints", {}):
            if raw not in raw_names:
                raw_names.append(raw)
        for raw in row.get("joints", {}):
            canon_names.add(normalize_joint_name(raw))
    canon_names = sorted(n for n in canon_names if n)

    edges = canonical_edges(canon_names)
    missing_edges = missing_requested_edges(canon_names)
    print({
        "apple_vision_3d_visualization": True,
        "jsonl": args.jsonl,
        "raw_joint_name_example": raw_names[0] if raw_names else None,
        "available_joint_names": canon_names,
        "skeleton_edges_used": edges,
        "skeleton_edge_count": len(edges),
        "missing_requested_edges": missing_edges,
        "missing_edge_count": len(missing_edges),
        "draw_bones": bool(args.draw_bones),
        "draw_joint_labels": bool(args.draw_joint_labels),
    })

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print({"visualization_ran": False, "reason": "video_open_failed", "video": args.video})
        return 0
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    overlay_writer = None
    if args.output_video:
        overlay_writer = make_writer(Path(args.output_video), fps, width, height)
    side_writer = make_writer(Path(args.output_side_by_side), fps, width * 2, height)

    rows_by_frame = {int(row["frame_idx"]): row for row in rows}
    detected = 0
    rendered = 0
    bone_counts_2d = []
    bone_counts_3d = []

    for row in rows[: args.max_frames]:
        frame_idx = int(row["frame_idx"])
        ok, frame = read_frame(cap, frame_idx)
        if not ok:
            continue
        overlay = frame.copy()
        row = rows_by_frame.get(frame_idx, row)
        if row.get("body_detected"):
            detected += 1
            n2d = draw_2d_projection(overlay, row, edges, args.draw_bones, args.draw_joint_labels)
            bone_counts_2d.append(n2d)
        draw_text(overlay, frame_idx, row, args.draw_bones)
        panel, n3d = render_3d_panel_stack(row, width, height, edges, args.draw_bones, args.draw_joint_labels)
        if row.get("body_detected"):
            bone_counts_3d.append(n3d)
        side_writer.write(np.concatenate([overlay, panel], axis=1))
        if overlay_writer is not None:
            overlay_writer.write(overlay)
        rendered += 1

    cap.release()
    side_writer.release()
    if overlay_writer is not None:
        overlay_writer.release()

    def stat(values):
        if not values:
            return {"min": 0, "max": 0, "mean": 0.0}
        return {"min": int(min(values)), "max": int(max(values)), "mean": round(float(np.mean(values)), 2)}

    print({
        "visualization_ran": True,
        "total_frames": len(rows),
        "rendered_frames": rendered,
        "detected_frames": detected,
        "bones_2d_per_detected_frame": stat(bone_counts_2d),
        "bones_3d_per_detected_frame_per_panel": stat(bone_counts_3d),
        "drew_2d_bones": bool(args.draw_bones and any(bone_counts_2d)),
        "drew_3d_bones": bool(args.draw_bones and any(bone_counts_3d)),
        "output_video": args.output_video,
        "output_side_by_side": args.output_side_by_side,
    })
    return 0


def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
# Joint-name normalization + skeleton edge construction
# ---------------------------------------------------------------------------

def normalize_joint_name(name):
    """Map any Apple Vision 3D joint key to a canonical camelCase name.

    Handles all three encodings seen in our JSONL / APIs:
      - legacy VNRecognizedPointKey raw value: "VNRecognizedPointKey(_rawValue: human_left_elbow_3D)"
      - legacy observation joint name:        "VNHumanBodyPose3DObservationJointNameLeftElbow"
      - new Swift API raw value:              "leftElbow"
    """
    text = str(name)

    # 1) legacy "human_<snake>_3D" core
    m = re.search(r"human_([a-z0-9_]+?)_3[dD]", text)
    if m:
        return _snake_to_camel(m.group(1))

    # 2) strip the long observation-jointname prefix if present
    prefix = "VNHumanBodyPose3DObservationJointName"
    if prefix in text:
        text = text.split(prefix, 1)[-1]

    # 3) any leftover wrapper like "VNRecognizedPointKey(_rawValue: leftElbow)"
    m2 = re.search(r"_rawValue:\s*([A-Za-z0-9_]+)", text)
    if m2:
        text = m2.group(1)

    text = text.strip()
    if not text:
        return text
    if "_" in text:
        return _snake_to_camel(text)
    return text[0].lower() + text[1:]


def _snake_to_camel(snake):
    parts = [p for p in snake.split("_") if p]
    if not parts:
        return snake
    return parts[0].lower() + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def canonical_edges(available):
    """Build the drawable skeleton edge list for the joints that exist.

    Applies the requested Apple Vision body mapping with graceful fallbacks:
      - if `spine` is missing, root connects straight to centerShoulder
      - Apple has no `neck`; the head chain falls back to centerHead
      - if `centerShoulder` is missing, shoulders attach to the head mid joint
      - never reference a joint that is not present
    """
    av = set(available)
    edges = []

    def add(a, b):
        if a in av and b in av and (a, b) not in edges and (b, a) not in edges:
            edges.append((a, b))
            return True
        return False

    # torso
    if not add("root", "spine"):
        add("root", "centerShoulder")
    add("spine", "centerShoulder")

    # head chain (neck preferred if it ever exists, else centerHead)
    head_mid = "neck" if "neck" in av else "centerHead"
    if not add("centerShoulder", head_mid):
        add("spine", head_mid)
    if not add(head_mid, "topHead"):
        # if head_mid was neck but topHead unreachable, try centerHead bridge
        if add("neck", "centerHead"):
            add("centerHead", "topHead")

    # arms
    for side in ("left", "right"):
        sh, el, wr = side + "Shoulder", side + "Elbow", side + "Wrist"
        if not add("centerShoulder", sh):
            add(head_mid, sh)
        add(sh, el)
        add(el, wr)

    # legs
    for side in ("left", "right"):
        hip, kn, an = side + "Hip", side + "Knee", side + "Ankle"
        add("root", hip)
        add(hip, kn)
        add(kn, an)

    return edges


def missing_requested_edges(available):
    av = set(available)
    return [list(e) for e in REQUESTED_EDGES if not (e[0] in av and e[1] in av)]


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def make_writer(path, fps, width, height):
    import cv2

    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open writer: {path}")
    return writer


def read_frame(cap, frame_idx):
    cap.set(1, int(frame_idx))
    return cap.read()


def normalized_joints(row):
    result = {}
    for raw_name, joint in row.get("joints", {}).items():
        result[normalize_joint_name(raw_name)] = joint
    return result


def draw_2d_projection(image, row, edges, draw_bones, draw_labels):
    import cv2

    joints = normalized_joints(row)
    drawn = 0
    if draw_bones:
        for a, b in edges:
            pa = image_point(joints.get(a))
            pb = image_point(joints.get(b))
            if pa is None or pb is None:
                continue
            cv2.line(image, pa, pb, color_for_joint_pair(a, b), 3, cv2.LINE_AA)
            drawn += 1
    for name, joint in joints.items():
        point = image_point(joint)
        if point is None:
            continue
        cv2.circle(image, point, 4, color_for_joint(name), -1, cv2.LINE_AA)
        if draw_labels:
            cv2.putText(image, short_name(name), (point[0] + 5, point[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, color_for_joint(name), 1, cv2.LINE_AA)
    return drawn


def draw_text(image, frame_idx, row, draw_bones):
    import cv2

    lines = [
        f"frame {frame_idx}",
        f"Apple Vision 3D detected={bool(row.get('body_detected'))} bones={'on' if draw_bones else 'off'}",
        "root-relative, meter-scale, estimated (not mocap-grade)",
    ]
    y = 22
    for line in lines:
        cv2.putText(image, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        y += 18


def render_3d_panel_stack(row, width, height, edges, draw_bones, draw_labels):
    heights = [height // 3, height // 3, height - 2 * (height // 3)]
    counts = []
    panels = []
    for h, view in zip(heights, ("front", "side", "top")):
        panel, n = render_3d_panel(row, width, h, view, edges, draw_bones, draw_labels)
        panels.append(panel)
        counts.append(n)
    return np.vstack(panels), (counts[0] if counts else 0)


def render_3d_panel(row, width, height, view, edges, draw_bones, draw_labels):
    import cv2
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    joints = normalized_joints(row)
    points = {name: joint_3d(joint) for name, joint in joints.items() if joint_3d(joint) is not None}
    drawn = 0
    fig = plt.figure(figsize=(width / 120.0, max(1.2, height / 120.0)), dpi=120)
    ax = fig.add_subplot(111, projection="3d")
    if points:
        arr = np.stack(list(points.values()), axis=0)
        if draw_bones:
            for a, b in edges:
                if a in points and b in points:
                    seg = np.stack([points[a], points[b]], axis=0)
                    ax.plot(seg[:, 0], seg[:, 1], seg[:, 2], color=mpl_color_for_pair(a, b), linewidth=2.2)
                    drawn += 1
        for name, point in points.items():
            ax.scatter(point[0], point[1], point[2], c=mpl_color_for_joint(name), s=14)
            if draw_labels:
                ax.text(point[0], point[1], point[2], short_name(name), fontsize=6)
        set_equal_axes(ax, arr)
    ax.set_title(f"Apple Vision 3D {view}", fontsize=9)
    ax.set_xlabel("x")
    ax.set_ylabel("depth")
    ax.set_zlabel("up")
    elev, azim = view_angles(view)
    ax.view_init(elev=elev, azim=azim)
    ax.text2D(0.02, 0.97, f"frame {row.get('frame_idx')}\ndetected={row.get('body_detected')}",
              transform=ax.transAxes, va="top", fontsize=7)
    fig.tight_layout()
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    image = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    plt.close(fig)
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA), drawn


def image_point(joint):
    if joint is None or "image_x" not in joint or "image_y" not in joint:
        return None
    return int(round(float(joint["image_x"]))), int(round(float(joint["image_y"])))


def joint_3d(joint):
    if joint is None or not all(key in joint for key in ("x", "y", "z")):
        return None
    # Visualization-only axis transform: x left/right, y depth, z up.
    return np.asarray([float(joint["x"]), float(joint["z"]), -float(joint["y"])], dtype="float32")


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


def color_for_joint(name):
    if name in LEFT_JOINTS:
        return (255, 100, 40)
    if name in RIGHT_JOINTS:
        return (40, 165, 255)
    return (40, 220, 80)


def color_for_joint_pair(a, b):
    if a in LEFT_JOINTS or b in LEFT_JOINTS:
        return (255, 100, 40)
    if a in RIGHT_JOINTS or b in RIGHT_JOINTS:
        return (40, 165, 255)
    return (40, 220, 80)


def mpl_color_for_joint(name):
    if name in LEFT_JOINTS:
        return "tab:blue"
    if name in RIGHT_JOINTS:
        return "tab:orange"
    return "tab:green"


def mpl_color_for_pair(a, b):
    if a in LEFT_JOINTS or b in LEFT_JOINTS:
        return "tab:blue"
    if a in RIGHT_JOINTS or b in RIGHT_JOINTS:
        return "tab:orange"
    return "tab:green"


def short_name(name):
    return (
        name.replace("left", "L")
        .replace("right", "R")
        .replace("Shoulder", "Sho")
        .replace("Elbow", "Elb")
        .replace("Wrist", "Wri")
        .replace("Knee", "Kne")
        .replace("Ankle", "Ank")
    )


if __name__ == "__main__":
    raise SystemExit(main())
