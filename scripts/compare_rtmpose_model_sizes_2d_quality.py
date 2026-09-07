import argparse
import csv
import json
import os
from pathlib import Path

import numpy as np


os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mpl_cache")

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

MAJOR_INDICES = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
UPPER_BODY_INDICES = (5, 6, 7, 8, 9, 10)
LOWER_BODY_INDICES = (11, 12, 13, 14, 15, 16)


def parse_args():
    parser = argparse.ArgumentParser(description="Compare multiple RTMPose model-size 2D JSONL diagnostics.")
    parser.add_argument(
        "--jsonl",
        action="append",
        required=True,
        help="Model JSONL as name=path. Can be provided multiple times.",
    )
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-confidence-plot")
    parser.add_argument("--output-jitter-plot")
    parser.add_argument("--valid-conf-threshold", type=float, default=0.5)
    parser.add_argument("--low-conf-threshold", type=float, default=0.4)
    return parser.parse_args()


def main():
    args = parse_args()
    inputs = parse_named_paths(args.jsonl)
    metrics = {
        name: summarize_model(load_jsonl(path), args.valid_conf_threshold, args.low_conf_threshold)
        for name, path in inputs.items()
    }
    disagreements = pairwise_disagreements(inputs, args.valid_conf_threshold)
    save_comparison_csv(Path(args.output_csv), metrics, disagreements)
    if args.output_confidence_plot:
        save_confidence_plot(Path(args.output_confidence_plot), metrics)
    if args.output_jitter_plot:
        save_jitter_plot(Path(args.output_jitter_plot), metrics)
    print(
        {
            "models": list(inputs),
            "output_csv": args.output_csv,
            "output_confidence_plot": args.output_confidence_plot,
            "output_jitter_plot": args.output_jitter_plot,
            "valid_ratios": {
                name: {
                    "upper": data["upper_body_valid_ratio"],
                    "lower": data["lower_body_valid_ratio"],
                    "full": data["full_body_valid_ratio"],
                }
                for name, data in metrics.items()
            },
            "worst_keypoints": {
                name: compact_worst(data)
                for name, data in metrics.items()
            },
            "pairwise_major_disagreement_px": {
                key: value["major_joint_mean_disagreement_px"]
                for key, value in disagreements.items()
            },
        },
    )
    return 0


def parse_named_paths(values):
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected name=path for --jsonl, got: {value}")
        name, path = value.split("=", 1)
        result[name] = Path(path)
    return result


def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def summarize_model(records, valid_threshold, low_threshold):
    detected = [
        record
        for record in records
        if record.get("body_detected") and record.get("keypoints_coco17") is not None
    ]
    total = len(records)
    keypoint_rows = empty_keypoint_rows()
    if not detected or total == 0:
        return {
            "processed_frames": total,
            "detected_frames": 0,
            "upper_body_valid_ratio": 0.0,
            "lower_body_valid_ratio": 0.0,
            "full_body_valid_ratio": 0.0,
            "keypoints": keypoint_rows,
            "mean_jitter_px": {COCO17_NAMES[index]: None for index in MAJOR_INDICES},
        }

    keypoints = np.asarray([record["keypoints_coco17"] for record in detected], dtype="float32")
    confs = keypoints[:, :, 2]
    upper = np.all(confs[:, UPPER_BODY_INDICES] >= valid_threshold, axis=1)
    lower = np.all(confs[:, LOWER_BODY_INDICES] >= valid_threshold, axis=1)
    keypoint_rows = []
    for index, name in enumerate(COCO17_NAMES):
        values = confs[:, index]
        keypoint_rows.append(
            {
                "index": index,
                "name": name,
                "mean_confidence": float(np.mean(values)),
                "median_confidence": float(np.median(values)),
                "low_confidence_frame_count": int(np.sum(values < low_threshold)),
                "low_confidence_frame_ratio": float(np.mean(values < low_threshold)),
            },
        )
    return {
        "processed_frames": total,
        "detected_frames": len(detected),
        "upper_body_valid_ratio": float(np.sum(upper) / total),
        "lower_body_valid_ratio": float(np.sum(lower) / total),
        "full_body_valid_ratio": float(np.sum(upper & lower) / total),
        "keypoints": keypoint_rows,
        "mean_jitter_px": jitter_by_joint(detected, valid_threshold),
    }


def empty_keypoint_rows():
    return [
        {
            "index": index,
            "name": name,
            "mean_confidence": 0.0,
            "median_confidence": 0.0,
            "low_confidence_frame_count": 0,
            "low_confidence_frame_ratio": 1.0,
        }
        for index, name in enumerate(COCO17_NAMES)
    ]


def jitter_by_joint(records, valid_threshold):
    result = {}
    for index in MAJOR_INDICES:
        values = []
        previous = None
        for record in records:
            keypoints = record.get("keypoints_coco17")
            if keypoints is None:
                previous = None
                continue
            row = np.asarray(keypoints[index], dtype="float32")
            if float(row[2]) < valid_threshold:
                previous = None
                continue
            current = row[:2]
            if previous is not None:
                values.append(float(np.linalg.norm(current - previous)))
            previous = current
        result[COCO17_NAMES[index]] = float(np.mean(values)) if values else None
    return result


def pairwise_disagreements(inputs, valid_threshold):
    loaded = {name: load_jsonl(path) for name, path in inputs.items()}
    result = {}
    names = list(inputs)
    for i, name_a in enumerate(names):
        for name_b in names[i + 1:]:
            result[f"{name_a}_vs_{name_b}"] = compare_pair(loaded[name_a], loaded[name_b], valid_threshold)
    return result


def compare_pair(records_a, records_b, valid_threshold):
    by_a = {int(row["frame_idx"]): row for row in records_a}
    by_b = {int(row["frame_idx"]): row for row in records_b}
    rows = []
    for index in MAJOR_INDICES:
        distances = []
        for frame_idx in sorted(set(by_a) & set(by_b)):
            kp_a = by_a[frame_idx].get("keypoints_coco17")
            kp_b = by_b[frame_idx].get("keypoints_coco17")
            if kp_a is None or kp_b is None:
                continue
            row_a = np.asarray(kp_a[index], dtype="float32")
            row_b = np.asarray(kp_b[index], dtype="float32")
            if float(row_a[2]) < valid_threshold or float(row_b[2]) < valid_threshold:
                continue
            distances.append(float(np.linalg.norm(row_a[:2] - row_b[:2])))
        rows.append(
            {
                "index": index,
                "name": COCO17_NAMES[index],
                "mean_disagreement_px": float(np.mean(distances)) if distances else None,
                "median_disagreement_px": float(np.median(distances)) if distances else None,
                "comparable_frame_count": len(distances),
            },
        )
    valid = [row["mean_disagreement_px"] for row in rows if row["mean_disagreement_px"] is not None]
    return {
        "rows": rows,
        "major_joint_mean_disagreement_px": float(np.mean(valid)) if valid else None,
    }


def save_comparison_csv(path, metrics, disagreements):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "section",
        "model",
        "pair",
        "index",
        "name",
        "metric",
        "value",
        "mean_disagreement_px",
        "median_disagreement_px",
        "comparable_frame_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for model, data in metrics.items():
            for metric in ("processed_frames", "detected_frames", "upper_body_valid_ratio", "lower_body_valid_ratio", "full_body_valid_ratio"):
                writer.writerow({"section": "model_summary", "model": model, "metric": metric, "value": data[metric]})
            for row in data["keypoints"]:
                for metric in ("mean_confidence", "median_confidence", "low_confidence_frame_count", "low_confidence_frame_ratio"):
                    writer.writerow(
                        {
                            "section": "keypoint_confidence",
                            "model": model,
                            "index": row["index"],
                            "name": row["name"],
                            "metric": metric,
                            "value": row[metric],
                        },
                    )
            for name, value in data["mean_jitter_px"].items():
                writer.writerow({"section": "jitter", "model": model, "name": name, "metric": "mean_jitter_px", "value": value})
        for pair, data in disagreements.items():
            writer.writerow(
                {
                    "section": "pair_summary",
                    "pair": pair,
                    "metric": "major_joint_mean_disagreement_px",
                    "value": data["major_joint_mean_disagreement_px"],
                },
            )
            for row in data["rows"]:
                writer.writerow(
                    {
                        "section": "pair_disagreement",
                        "pair": pair,
                        "index": row["index"],
                        "name": row["name"],
                        "mean_disagreement_px": row["mean_disagreement_px"],
                        "median_disagreement_px": row["median_disagreement_px"],
                        "comparable_frame_count": row["comparable_frame_count"],
                    },
                )


def save_confidence_plot(path, metrics):
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    x = np.arange(len(COCO17_NAMES))
    width = 0.8 / max(1, len(metrics))
    fig, ax = plt.subplots(figsize=(13, 5))
    for offset, (model, data) in enumerate(metrics.items()):
        values = [row["mean_confidence"] for row in data["keypoints"]]
        ax.bar(x + offset * width, values, width, label=model)
    ax.axhline(0.5, color="black", linestyle="--", linewidth=1, label="valid threshold")
    ax.set_xticks(x + width * (len(metrics) - 1) / 2)
    ax.set_xticklabels(COCO17_NAMES, rotation=60, ha="right")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("mean confidence")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def save_jitter_plot(path, metrics):
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    names = [COCO17_NAMES[index] for index in MAJOR_INDICES]
    x = np.arange(len(names))
    width = 0.8 / max(1, len(metrics))
    fig, ax = plt.subplots(figsize=(12, 5))
    for offset, (model, data) in enumerate(metrics.items()):
        values = [np.nan if data["mean_jitter_px"].get(name) is None else data["mean_jitter_px"][name] for name in names]
        ax.bar(x + offset * width, values, width, label=model)
    ax.set_xticks(x + width * (len(metrics) - 1) / 2)
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_ylabel("mean frame-to-frame jitter (px)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def compact_worst(data):
    return [
        {
            "name": row["name"],
            "mean_confidence": row["mean_confidence"],
            "low_confidence_frame_count": row["low_confidence_frame_count"],
        }
        for row in sorted(data["keypoints"], key=lambda item: item["mean_confidence"])[:5]
    ]


if __name__ == "__main__":
    raise SystemExit(main())
