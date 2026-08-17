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

from pose_feedback.body.motionagformer_adapter import motionagformer_angles


def parse_args():
    parser = argparse.ArgumentParser(description="Compare MotionAGFormer full-window and lookahead outputs.")
    parser.add_argument("--full-npz", default="assets/smoke/vedio_1_motionagformer_full_debug.npz")
    parser.add_argument("--lookahead3-npz", default="assets/smoke/vedio_1_motionagformer_lookahead3_debug.npz")
    parser.add_argument("--lookahead5-npz", default="assets/smoke/vedio_1_motionagformer_lookahead5_debug.npz")
    parser.add_argument("--output-csv", default="assets/smoke/vedio_1_motionagformer_lookahead_comparison.csv")
    parser.add_argument("--output-plot", default="assets/smoke/vedio_1_motionagformer_lookahead_angle_plot.png")
    parser.add_argument("--fps", type=float, default=30.0)
    return parser.parse_args()


def main():
    args = parse_args()
    paths = {
        "full": Path(args.full_npz),
        "lookahead3": Path(args.lookahead3_npz),
        "lookahead5": Path(args.lookahead5_npz),
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        print({"comparison_ran": False, "missing_outputs": missing, "latency_table": latency_table(args.fps)})
        return 0

    outputs = {name: load_output(path) for name, path in paths.items()}
    rows, summary = compare(outputs, args.fps)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    save_csv(output_csv, rows)
    save_plot(Path(args.output_plot), rows)
    print(
        {
            "comparison_ran": True,
            "output_csv": str(output_csv),
            "output_plot": args.output_plot,
            "summary": summary,
            "latency_table": latency_table(args.fps),
        },
    )
    return 0


def load_output(path):
    data = np.load(path, allow_pickle=True)
    if "pred_3d" not in data.files:
        raise ValueError(f"{path} missing pred_3d")
    pred = np.asarray(data["pred_3d"], dtype="float32")
    frame_indices = data["frame_indices"]
    latency_frames = int(np.asarray(data["latency_frames"])[0]) if "latency_frames" in data.files else None
    if frame_indices.ndim == 2:
        if pred.ndim == 4:
            output_idx = frame_indices.shape[1] // 2 if latency_frames is None else frame_indices.shape[1] - latency_frames - 1
            output_idx = int(np.clip(output_idx, 0, frame_indices.shape[1] - 1))
            source = frame_indices[:, output_idx]
            pred = pred[:, output_idx]
        else:
            source = frame_indices[:, frame_indices.shape[1] // 2]
    else:
        source = frame_indices
    if pred.ndim != 3 or pred.shape[-2:] != (17, 3):
        raise ValueError(f"{path} pred_3d must resolve to shape (N, 17, 3), got {pred.shape}")
    return {
        "pred": pred,
        "frame_idx": np.asarray(source, dtype=int),
    }


def compare(outputs, fps):
    full_by_frame = angles_by_frame(outputs["full"])
    rows = []
    for method, output in outputs.items():
        method_angles = angles_by_frame(output)
        for frame_idx, angles in method_angles.items():
            row = {"method": method, "frame_idx": frame_idx}
            for key, value in angles.items():
                row[key] = value
                row[f"{key}_abs_error_vs_full"] = (
                    None if method == "full" or frame_idx not in full_by_frame else abs(value - full_by_frame[frame_idx][key])
                )
            rows.append(row)
    summary = []
    for method in ("full", "lookahead3", "lookahead5"):
        method_rows = [row for row in rows if row["method"] == method]
        elbow_errors = collect_errors(method_rows, ("left_elbow", "right_elbow"))
        knee_errors = collect_errors(method_rows, ("left_knee", "right_knee"))
        summary.append(
            {
                "method": method,
                "latency_frames": latency_frames(method),
                "latency_sec": latency_frames(method) / fps,
                "elbow_mae_vs_full": mean_or_none(elbow_errors),
                "knee_mae_vs_full": mean_or_none(knee_errors),
                "jitter": jitter(method_rows),
            },
        )
    return rows, summary


def angles_by_frame(output):
    result = {}
    for idx, joints in zip(output["frame_idx"], output["pred"]):
        result[int(idx)] = motionagformer_angles(joints)
    return result


def collect_errors(rows, keys):
    values = []
    for row in rows:
        for key in keys:
            value = row.get(f"{key}_abs_error_vs_full")
            if value is not None:
                values.append(float(value))
    return values


def mean_or_none(values):
    return None if not values else float(np.mean(values))


def jitter(rows):
    if len(rows) < 2:
        return None
    values = []
    for key in ("left_elbow", "right_elbow", "left_knee", "right_knee"):
        series = [row[key] for row in sorted(rows, key=lambda row: row["frame_idx"]) if row[key] is not None]
        if len(series) >= 2:
            values.extend(np.abs(np.diff(series)).tolist())
    return mean_or_none(values)


def save_csv(path, rows):
    fieldnames = [
        "method",
        "frame_idx",
        "left_elbow",
        "right_elbow",
        "left_knee",
        "right_knee",
        "left_elbow_abs_error_vs_full",
        "right_elbow_abs_error_vs_full",
        "left_knee_abs_error_vs_full",
        "right_knee_abs_error_vs_full",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_plot(path, rows):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
    for method in ("full", "lookahead3", "lookahead5"):
        method_rows = sorted([row for row in rows if row["method"] == method], key=lambda row: row["frame_idx"])
        if method_rows:
            ax.plot([row["frame_idx"] for row in method_rows], [row["left_elbow"] for row in method_rows], label=f"{method} left elbow")
    ax.set_xlabel("source frame")
    ax.set_ylabel("angle (deg)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def latency_frames(method):
    if method == "full":
        return 121
    if method == "lookahead3":
        return 3
    if method == "lookahead5":
        return 5
    raise ValueError(method)


def latency_table(fps):
    return [
        {"method": method, "latency_frames": latency_frames(method), "latency_sec": latency_frames(method) / fps}
        for method in ("full", "lookahead3", "lookahead5")
    ]


if __name__ == "__main__":
    raise SystemExit(main())
