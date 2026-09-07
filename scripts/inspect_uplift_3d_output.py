import argparse
import csv
import os
from pathlib import Path
import sys

import numpy as np


os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mpl_cache")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.geometry.angles_3d import elbow_flexion_3d, knee_flexion_3d


JOINT_NAMES = [
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

SKELETON = [
    (10, 9),
    (9, 7),
    (7, 8),
    (8, 6),
    (7, 13),
    (13, 12),
    (12, 11),
    (7, 14),
    (14, 15),
    (15, 16),
    (6, 2),
    (2, 1),
    (1, 0),
    (6, 3),
    (3, 4),
    (4, 5),
]


def parse_args():
    parser = argparse.ArgumentParser(description="Inspect Uplift-Upsample 3D output angles.")
    parser.add_argument("--input-npz", default="assets/smoke/vedio_1_uplift_3d_output_debug.npz")
    parser.add_argument("--input-2d-npz", default="assets/smoke/vedio_1_uplift_input_debug.npz")
    parser.add_argument("--output-csv", default="assets/smoke/vedio_1_uplift_3d_angles_debug.csv")
    parser.add_argument("--output-skeleton", default="assets/smoke/vedio_1_uplift_3d_first_frame.png")
    parser.add_argument("--output-angle-plot", default="assets/smoke/vedio_1_uplift_3d_angles_plot.png")
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input_npz)
    if not input_path.exists():
        print({"input_exists": False, "input_npz": str(input_path)})
        return 0

    data = np.load(input_path, allow_pickle=True)
    shapes = {key: tuple(data[key].shape) for key in data.files}
    print({"input_keys": list(data.files), "input_shapes": shapes})
    pred_key, pred = select_prediction_array(data)
    if pred is None:
        print({"prediction_key": None, "reason": "no supported 3D prediction array found"})
        return 0
    print({"prediction_key": pred_key, "prediction_shape": tuple(pred.shape)})

    frame_indices = load_frame_indices(Path(args.input_2d_npz), len(pred))
    rows = compute_angle_rows(pred, frame_indices)

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    save_csv(output_csv, rows)

    output_skeleton = Path(args.output_skeleton)
    output_skeleton.parent.mkdir(parents=True, exist_ok=True)
    save_skeleton_plot(pred[0], output_skeleton)

    output_angle_plot = Path(args.output_angle_plot)
    output_angle_plot.parent.mkdir(parents=True, exist_ok=True)
    save_angle_plot(rows, output_angle_plot)

    print(
        {
            "output_csv": str(output_csv),
            "output_skeleton": str(output_skeleton),
            "output_angle_plot": str(output_angle_plot),
            "first_angles": rows[:5],
        },
    )
    return 0


def select_prediction_array(data):
    candidates = [
        "pred_3d_central",
        "predictions_3d",
        "pred_3d",
        "output_3d",
        "pred_3d_full",
    ]
    for key in candidates:
        if key not in data.files:
            continue
        arr = np.asarray(data[key])
        if arr.ndim == 3 and arr.shape[-2:] == (17, 3):
            return key, arr.astype("float32")
        if arr.ndim == 4 and arr.shape[-2:] == (17, 3):
            return key, arr[:, arr.shape[1] // 2].astype("float32")
    return None, None


def load_frame_indices(path, count):
    if not path.exists():
        return list(range(count))
    data = np.load(path, allow_pickle=True)
    if "frame_indices" not in data.files:
        return list(range(count))
    frame_indices = np.asarray(data["frame_indices"])
    if frame_indices.ndim == 2:
        centers = frame_indices[:, frame_indices.shape[1] // 2]
    else:
        centers = frame_indices
    return [int(value) for value in centers[:count]]


def compute_angle_rows(pred, frame_indices):
    rows = []
    for index, joints in enumerate(pred):
        rows.append(
            {
                "prediction_index": index,
                "frame_idx": frame_indices[index] if index < len(frame_indices) else index,
                "right_elbow_angle": elbow_flexion_3d(joints[13], joints[12], joints[11]),
                "left_elbow_angle": elbow_flexion_3d(joints[14], joints[15], joints[16]),
                "right_knee_angle": knee_flexion_3d(joints[2], joints[1], joints[0]),
                "left_knee_angle": knee_flexion_3d(joints[3], joints[4], joints[5]),
            },
        )
    return rows


def save_csv(path, rows):
    fieldnames = [
        "prediction_index",
        "frame_idx",
        "right_elbow_angle",
        "left_elbow_angle",
        "right_knee_angle",
        "left_knee_angle",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_skeleton_plot(joints, output_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(8, 7), dpi=180)
    ax = fig.add_subplot(111, projection="3d")
    for a, b in SKELETON:
        segment = joints[[a, b]]
        ax.plot(segment[:, 0], segment[:, 1], segment[:, 2], color="tab:blue", linewidth=2.4)
    ax.scatter(joints[:, 0], joints[:, 1], joints[:, 2], c="tab:orange", s=25)
    for idx, name in enumerate(JOINT_NAMES):
        ax.text(joints[idx, 0], joints[idx, 1], joints[idx, 2], name, fontsize=7)
    set_equal_axes(ax, joints)
    ax.set_title("Uplift 3D first predicted frame")
    ax.view_init(elev=18, azim=-70)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def save_angle_plot(rows, output_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = [row["prediction_index"] for row in rows]
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=160)
    for key, label in [
        ("right_elbow_angle", "right elbow"),
        ("left_elbow_angle", "left elbow"),
        ("right_knee_angle", "right knee"),
        ("left_knee_angle", "left knee"),
    ]:
        ax.plot(x, [none_to_nan(row[key]) for row in rows], label=label, linewidth=2)
    ax.set_xlabel("prediction index")
    ax.set_ylabel("angle (deg)")
    ax.set_title("Uplift 3D angle inspection")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


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


def none_to_nan(value):
    return np.nan if value is None else float(value)


if __name__ == "__main__":
    raise SystemExit(main())
