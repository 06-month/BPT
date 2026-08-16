import argparse
import csv
import json
from pathlib import Path

import numpy as np


MAJOR_JOINTS = [
    "leftShoulder",
    "rightShoulder",
    "leftElbow",
    "rightElbow",
    "leftWrist",
    "rightWrist",
    "leftHip",
    "rightHip",
    "leftKnee",
    "rightKnee",
    "leftAnkle",
    "rightAnkle",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Diagnose Apple Vision 3D JSONL quality.")
    parser.add_argument("--jsonl", required=True)
    parser.add_argument("--output-csv", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    path = Path(args.jsonl)
    if not path.exists():
        print({"diagnostic_ran": False, "reason": "missing_jsonl", "jsonl": args.jsonl})
        return 0
    rows = load_jsonl(path)
    if not rows:
        print({"diagnostic_ran": False, "reason": "empty_jsonl", "jsonl": args.jsonl})
        return 0
    summary_rows, summary = summarize(rows)
    save_csv(Path(args.output_csv), summary_rows)
    print(
        {
            "diagnostic_ran": True,
            "jsonl": args.jsonl,
            "output_csv": args.output_csv,
            "total_frames": summary["total_frames"],
            "detected_frames": summary["detected_frames"],
            "detected_ratio": summary["detected_ratio"],
            "available_joint_names": summary["available_joint_names"],
            "major_joint_missing_rates": summary["major_joint_missing_rates"],
        },
    )
    return 0


def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def summarize(rows):
    detected_rows = [row for row in rows if row.get("body_detected")]
    joint_names = set()
    for row in rows:
        for name in row.get("raw_joint_names", []):
            joint_names.add(normalize_joint_name(name))
        for name in row.get("joints", {}):
            joint_names.add(normalize_joint_name(name))
    all_names = sorted(joint_names)
    if not all_names:
        all_names = MAJOR_JOINTS

    summary_rows = []
    for name in all_names:
        positions = []
        present = 0
        for row in rows:
            joint = normalized_joints(row).get(name)
            point = joint_3d(joint) if joint else None
            if point is not None:
                present += 1
                positions.append(point)
            else:
                positions.append(None)
        jitter_values = []
        previous = None
        for point in positions:
            if point is not None and previous is not None:
                jitter_values.append(float(np.linalg.norm(point - previous)))
            if point is not None:
                previous = point
        missing_rate = 1.0 - (present / len(rows))
        summary_rows.append(
            {
                "joint_name": name,
                "present_frame_count": present,
                "missing_frame_count": len(rows) - present,
                "missing_rate": missing_rate,
                "mean_frame_to_frame_jitter": mean_or_none(jitter_values),
                "median_frame_to_frame_jitter": median_or_none(jitter_values),
            },
        )
    major_rates = {
        row["joint_name"]: row["missing_rate"]
        for row in summary_rows
        if row["joint_name"] in MAJOR_JOINTS
    }
    return summary_rows, {
        "total_frames": len(rows),
        "detected_frames": len(detected_rows),
        "detected_ratio": len(detected_rows) / len(rows),
        "available_joint_names": all_names,
        "major_joint_missing_rates": major_rates,
    }


def normalized_joints(row):
    return {
        normalize_joint_name(name): joint
        for name, joint in row.get("joints", {}).items()
    }


def normalize_joint_name(name):
    text = str(name)
    prefix = "VNHumanBodyPose3DObservationJointName"
    if text.startswith(prefix):
        text = text[len(prefix):]
    if not text:
        return text
    return text[0].lower() + text[1:]


def joint_3d(joint):
    if joint is None or not all(key in joint for key in ("x", "y", "z")):
        return None
    return np.asarray([float(joint["x"]), float(joint["y"]), float(joint["z"])], dtype="float32")


def mean_or_none(values):
    return None if not values else float(np.mean(values))


def median_or_none(values):
    return None if not values else float(np.median(values))


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "joint_name",
        "present_frame_count",
        "missing_frame_count",
        "missing_rate",
        "mean_frame_to_frame_jitter",
        "median_frame_to_frame_jitter",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
