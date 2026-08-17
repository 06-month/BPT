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


ANGLE_NAMES = ["left_elbow", "right_elbow", "left_knee", "right_knee"]


def parse_args():
    parser = argparse.ArgumentParser(description="Compare MotionAGFormer XS/S full vs lookahead outputs.")
    parser.add_argument("--xs-full", required=True)
    parser.add_argument("--xs-lookahead3", required=True)
    parser.add_argument("--xs-lookahead5", required=True)
    parser.add_argument("--s-full", required=True)
    parser.add_argument("--s-lookahead3", required=True)
    parser.add_argument("--s-lookahead5", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-angle-plot", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    series = {
        "xs_full": load_series(args.xs_full),
        "xs_lookahead3": load_series(args.xs_lookahead3),
        "xs_lookahead5": load_series(args.xs_lookahead5),
        "s_full": load_series(args.s_full),
        "s_lookahead3": load_series(args.s_lookahead3),
        "s_lookahead5": load_series(args.s_lookahead5),
    }
    rows = build_rows(series)
    save_csv(Path(args.output_csv), rows)
    save_angle_plot(Path(args.output_angle_plot), series)
    print(
        {
            "output_csv": args.output_csv,
            "output_angle_plot": args.output_angle_plot,
            "summary": compact_summary(rows),
        },
    )
    return 0


def load_series(path):
    data = np.load(path, allow_pickle=True)
    pred = np.asarray(data["pred_3d"], dtype="float32")
    frame_indices = np.asarray(data["frame_indices"])
    latency_frames = int(np.asarray(data["latency_frames"])[0]) if "latency_frames" in data.files else 0
    mode = str(np.asarray(data["mode"])[0]) if "mode" in data.files else Path(path).stem
    if pred.ndim == 4:
        if frame_indices.ndim == 2:
            output_idx = int(np.clip(pred.shape[1] - latency_frames - 1, 0, pred.shape[1] - 1))
            joints = pred[:, output_idx]
            source_frames = frame_indices[:, output_idx]
        else:
            output_idx = pred.shape[1] // 2
            joints = pred[:, output_idx]
            source_frames = frame_indices
    else:
        joints = pred
        source_frames = frame_indices[:, frame_indices.shape[1] // 2] if frame_indices.ndim == 2 else frame_indices
    angles = {name: [] for name in ANGLE_NAMES}
    for item in joints:
        values = motionagformer_angles(item)
        for name in ANGLE_NAMES:
            angles[name].append(values[name])
    return {
        "path": path,
        "mode": mode,
        "frames": np.asarray(source_frames, dtype=int),
        "joints": np.asarray(joints, dtype="float32"),
        "angles": {name: np.asarray(values, dtype="float32") for name, values in angles.items()},
        "skeleton_jitter": skeleton_jitter(joints),
    }


def skeleton_jitter(joints):
    if len(joints) < 2:
        return None
    deltas = np.linalg.norm(np.diff(joints, axis=0), axis=-1)
    return float(np.mean(deltas))


def build_rows(series):
    rows = []
    for name, data in series.items():
        rows.append(
            {
                "section": "series_summary",
                "series": name,
                "frames": len(data["frames"]),
                "skeleton_jitter": data["skeleton_jitter"],
            },
        )
        for angle_name in ANGLE_NAMES:
            values = data["angles"][angle_name]
            rows.append(
                {
                    "section": "angle_summary",
                    "series": name,
                    "angle": angle_name,
                    "mean_angle": float(np.mean(values)),
                    "std_angle": float(np.std(values)),
                },
            )
    for model in ("xs", "s"):
        full = series[f"{model}_full"]
        for lookahead in ("lookahead3", "lookahead5"):
            candidate = series[f"{model}_{lookahead}"]
            rows.extend(angle_mae_rows(f"{model}_{lookahead}_vs_full", full, candidate))
    rows.extend(angle_mae_rows("xs_lookahead5_vs_s_lookahead5", series["xs_lookahead5"], series["s_lookahead5"]))
    return rows


def angle_mae_rows(label, reference, candidate):
    rows = []
    ref_by_frame = {int(frame): idx for idx, frame in enumerate(reference["frames"])}
    cand_by_frame = {int(frame): idx for idx, frame in enumerate(candidate["frames"])}
    shared = sorted(set(ref_by_frame) & set(cand_by_frame))
    for angle_name in ANGLE_NAMES:
        diffs = []
        for frame in shared:
            ref_value = float(reference["angles"][angle_name][ref_by_frame[frame]])
            cand_value = float(candidate["angles"][angle_name][cand_by_frame[frame]])
            diffs.append(abs(cand_value - ref_value))
        rows.append(
            {
                "section": "angle_mae",
                "series": label,
                "angle": angle_name,
                "shared_frames": len(shared),
                "mae_deg": float(np.mean(diffs)) if diffs else None,
                "max_abs_error_deg": float(np.max(diffs)) if diffs else None,
            },
        )
    return rows


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "section",
        "series",
        "angle",
        "frames",
        "shared_frames",
        "skeleton_jitter",
        "mean_angle",
        "std_angle",
        "mae_deg",
        "max_abs_error_deg",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save_angle_plot(path, series):
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    for axis, angle_name in zip(axes.ravel(), ANGLE_NAMES):
        for key in ("xs_full", "xs_lookahead5", "s_full", "s_lookahead5"):
            data = series[key]
            axis.plot(data["frames"], data["angles"][angle_name], label=key, linewidth=1.2)
        axis.set_title(angle_name)
        axis.set_ylabel("deg")
        axis.grid(True, alpha=0.25)
    axes[-1, 0].set_xlabel("source frame")
    axes[-1, 1].set_xlabel("source frame")
    axes[0, 0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def compact_summary(rows):
    return [
        row
        for row in rows
        if row.get("section") in {"series_summary", "angle_mae"}
    ]


if __name__ == "__main__":
    raise SystemExit(main())
