"""Compare Core ML RTMPose-s decoded 2D JSONL against existing MMPose JSONL."""

import argparse
import csv
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
COCO17_NAMES = [
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
UPPER_BODY = (5, 6, 7, 8, 9, 10)
LOWER_BODY = (11, 12, 13, 14, 15, 16)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coreml-jsonl", default="assets/coreml_pipeline/jsonl/vedio_1_coreml_rtmpose_s_2d.jsonl")
    parser.add_argument("--reference-jsonl", default="assets/smoke/vedio_1_rtmpose_2d_keypoints.jsonl")
    parser.add_argument("--output-csv", default="assets/coreml_pipeline/csv/vedio_1_coreml_vs_pytorch_rtmpose_2d_comparison.csv")
    parser.add_argument("--output-plot", default="assets/coreml_pipeline/plots/vedio_1_coreml_vs_pytorch_rtmpose_2d_error_plot.png")
    parser.add_argument("--valid-threshold", type=float, default=0.5)
    return parser.parse_args()


def main():
    args = parse_args()
    coreml_path = Path(args.coreml_jsonl)
    ref_path = Path(args.reference_jsonl)
    if not coreml_path.exists() or not ref_path.exists():
        print(
            {
                "comparison_ran": False,
                "reason": "missing_reference_or_coreml_jsonl",
                "coreml_jsonl": str(coreml_path),
                "reference_jsonl": str(ref_path),
            },
        )
        return 0

    coreml = load_jsonl(coreml_path, ("coco17_keypoints", "keypoints_coco17"))
    ref = load_jsonl(ref_path, ("keypoints_coco17", "coco17_keypoints"))
    common = sorted(set(coreml) & set(ref))
    if not common:
        print({"comparison_ran": False, "reason": "no_common_frames"})
        return 0

    core_arr = np.stack([coreml[idx] for idx in common]).astype("float32")
    ref_arr = np.stack([ref[idx] for idx in common]).astype("float32")
    distances = np.linalg.norm(core_arr[..., :2] - ref_arr[..., :2], axis=-1)
    conf_diff = core_arr[..., 2] - ref_arr[..., 2]

    rows = []
    for joint_idx, name in enumerate(COCO17_NAMES):
        rows.append(
            {
                "joint_index": joint_idx,
                "joint_name": name,
                "frames_compared": len(common),
                "mean_pixel_error": float(np.mean(distances[:, joint_idx])),
                "median_pixel_error": float(np.median(distances[:, joint_idx])),
                "p90_pixel_error": float(np.percentile(distances[:, joint_idx], 90)),
                "mean_confidence_diff": float(np.mean(conf_diff[:, joint_idx])),
                "median_confidence_diff": float(np.median(conf_diff[:, joint_idx])),
            },
        )

    summary = {
        "joint_index": "all",
        "joint_name": "all",
        "frames_compared": len(common),
        "mean_pixel_error": float(np.mean(distances)),
        "median_pixel_error": float(np.median(distances)),
        "p90_pixel_error": float(np.percentile(distances, 90)),
        "mean_confidence_diff": float(np.mean(conf_diff)),
        "median_confidence_diff": float(np.median(conf_diff)),
        "upper_body_valid_ratio": valid_ratio(core_arr, UPPER_BODY, args.valid_threshold),
        "lower_body_valid_ratio": valid_ratio(core_arr, LOWER_BODY, args.valid_threshold),
        "full_body_valid_ratio": valid_ratio(core_arr, tuple(range(17)), args.valid_threshold),
    }
    rows.append(summary)

    save_csv(Path(args.output_csv), rows)
    save_plot(Path(args.output_plot), rows[:-1])
    print(
        {
            "comparison_ran": True,
            "frames_compared": len(common),
            "output_csv": args.output_csv,
            "output_plot": args.output_plot,
            "mean_pixel_error_all": summary["mean_pixel_error"],
            "median_pixel_error_all": summary["median_pixel_error"],
            "p90_pixel_error_all": summary["p90_pixel_error"],
            "upper_body_valid_ratio": summary["upper_body_valid_ratio"],
            "lower_body_valid_ratio": summary["lower_body_valid_ratio"],
            "full_body_valid_ratio": summary["full_body_valid_ratio"],
        },
    )
    return 0


def load_jsonl(path, key_candidates):
    rows = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            keypoints = None
            for key in key_candidates:
                if row.get(key) is not None:
                    keypoints = row[key]
                    break
            if keypoints is None:
                continue
            frame_idx = row.get("frame_index", row.get("frame_idx"))
            rows[int(frame_idx)] = np.asarray(keypoints, dtype="float32")
    return rows


def valid_ratio(values, indices, threshold):
    conf = values[:, indices, 2]
    return float(np.mean(np.all(conf >= threshold, axis=1)))


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "joint_index",
        "joint_name",
        "frames_compared",
        "mean_pixel_error",
        "median_pixel_error",
        "p90_pixel_error",
        "mean_confidence_diff",
        "median_confidence_diff",
        "upper_body_valid_ratio",
        "lower_body_valid_ratio",
        "full_body_valid_ratio",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def save_plot(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas = np.full((720, 1280, 3), 255, dtype=np.uint8)
    margin_l, margin_r, margin_t, margin_b = 90, 40, 70, 150
    plot_w = canvas.shape[1] - margin_l - margin_r
    plot_h = canvas.shape[0] - margin_t - margin_b
    values = np.asarray([row["mean_pixel_error"] for row in rows], dtype="float32")
    max_value = max(float(values.max()), 1.0)
    cv2.line(canvas, (margin_l, margin_t), (margin_l, margin_t + plot_h), (0, 0, 0), 2)
    cv2.line(canvas, (margin_l, margin_t + plot_h), (margin_l + plot_w, margin_t + plot_h), (0, 0, 0), 2)
    bar_w = max(8, int(plot_w / (len(rows) * 1.5)))
    for idx, (row, value) in enumerate(zip(rows, values)):
        x = margin_l + int((idx + 0.5) * plot_w / len(rows))
        h = int((float(value) / max_value) * plot_h)
        cv2.rectangle(canvas, (x - bar_w // 2, margin_t + plot_h - h), (x + bar_w // 2, margin_t + plot_h), (60, 120, 220), -1)
        cv2.putText(canvas, str(row["joint_index"]), (x - 8, margin_t + plot_h + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    cv2.putText(canvas, "CoreML vs PyTorch RTMPose-s mean pixel error by COCO17 joint", (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(canvas, f"max plotted mean error: {max_value:.2f}px", (margin_l, canvas.shape[0] - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 1)
    cv2.imwrite(str(path), canvas)


if __name__ == "__main__":
    raise SystemExit(main())
