import argparse
import csv
import json
from pathlib import Path

import numpy as np


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
    parser = argparse.ArgumentParser(description="Compare RTMPose-s and RTMPose-m 2D diagnostics.")
    parser.add_argument("--s-jsonl", required=True)
    parser.add_argument("--m-jsonl", required=True)
    parser.add_argument("--s-video", required=True)
    parser.add_argument("--m-video", required=True)
    parser.add_argument("--output-video", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--valid-conf-threshold", type=float, default=0.5)
    parser.add_argument("--low-conf-threshold", type=float, default=0.4)
    return parser.parse_args()


def main():
    args = parse_args()
    s_records = load_jsonl(Path(args.s_jsonl))
    m_records = load_jsonl(Path(args.m_jsonl))
    s_metrics = summarize_model(s_records, args.valid_conf_threshold, args.low_conf_threshold)
    m_metrics = summarize_model(m_records, args.valid_conf_threshold, args.low_conf_threshold)
    comparison = compare_models(s_records, m_records, args.valid_conf_threshold)
    create_side_by_side_video(Path(args.s_video), Path(args.m_video), Path(args.output_video))
    save_csv(Path(args.output_csv), s_metrics, m_metrics, comparison)

    recommendation = recommend(s_metrics, m_metrics, comparison)
    result = {
        "s_jsonl": args.s_jsonl,
        "m_jsonl": args.m_jsonl,
        "output_video": args.output_video,
        "output_csv": args.output_csv,
        "rtmpose_s": compact_metrics(s_metrics),
        "rtmpose_m": compact_metrics(m_metrics),
        "major_joint_mean_disagreement_px": comparison["major_joint_mean_disagreement_px"],
        "largest_disagreements": comparison["largest_disagreements"],
        "recommendation": recommendation,
    }
    print(result)
    return 0


def load_jsonl(path):
    records = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                records.append(json.loads(line))
    return records


def summarize_model(records, valid_threshold, low_threshold):
    detected = [
        record
        for record in records
        if record.get("body_detected") and record.get("keypoints_coco17") is not None
    ]
    total = len(records)
    if not detected or total == 0:
        return {
            "processed_frames": total,
            "detected_frames": 0,
            "upper_body_valid_ratio": 0.0,
            "lower_body_valid_ratio": 0.0,
            "full_body_valid_ratio": 0.0,
            "keypoints": empty_keypoint_rows(),
            "mean_jitter_px": {},
        }

    keypoints = np.asarray([record["keypoints_coco17"] for record in detected], dtype="float32")
    confs = keypoints[:, :, 2]
    upper = np.all(confs[:, UPPER_BODY_INDICES] >= valid_threshold, axis=1)
    lower = np.all(confs[:, LOWER_BODY_INDICES] >= valid_threshold, axis=1)
    rows = []
    for index, name in enumerate(COCO17_NAMES):
        values = confs[:, index]
        rows.append(
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
        "keypoints": rows,
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
        distances = []
        prev = None
        for record in records:
            keypoints = record.get("keypoints_coco17")
            if keypoints is None:
                prev = None
                continue
            row = np.asarray(keypoints[index], dtype="float32")
            if float(row[2]) < valid_threshold:
                prev = None
                continue
            current = row[:2]
            if prev is not None:
                distances.append(float(np.linalg.norm(current - prev)))
            prev = current
        result[COCO17_NAMES[index]] = float(np.mean(distances)) if distances else None
    return result


def compare_models(s_records, m_records, valid_threshold):
    s_by_frame = {int(record["frame_idx"]): record for record in s_records}
    m_by_frame = {int(record["frame_idx"]): record for record in m_records}
    rows = []
    for index in MAJOR_INDICES:
        distances = []
        for frame_idx in sorted(set(s_by_frame) & set(m_by_frame)):
            s_kp = s_by_frame[frame_idx].get("keypoints_coco17")
            m_kp = m_by_frame[frame_idx].get("keypoints_coco17")
            if s_kp is None or m_kp is None:
                continue
            s_row = np.asarray(s_kp[index], dtype="float32")
            m_row = np.asarray(m_kp[index], dtype="float32")
            if float(s_row[2]) < valid_threshold or float(m_row[2]) < valid_threshold:
                continue
            distances.append(float(np.linalg.norm(s_row[:2] - m_row[:2])))
        rows.append(
            {
                "index": index,
                "name": COCO17_NAMES[index],
                "mean_disagreement_px": float(np.mean(distances)) if distances else None,
                "median_disagreement_px": float(np.median(distances)) if distances else None,
                "comparable_frame_count": len(distances),
            },
        )
    valid_distances = [row["mean_disagreement_px"] for row in rows if row["mean_disagreement_px"] is not None]
    largest = sorted(
        [row for row in rows if row["mean_disagreement_px"] is not None],
        key=lambda row: row["mean_disagreement_px"],
        reverse=True,
    )[:5]
    return {
        "rows": rows,
        "major_joint_mean_disagreement_px": float(np.mean(valid_distances)) if valid_distances else None,
        "largest_disagreements": largest,
    }


def create_side_by_side_video(s_video, m_video, output_video):
    import cv2

    s_cap = cv2.VideoCapture(str(s_video))
    m_cap = cv2.VideoCapture(str(m_video))
    if not s_cap.isOpened() or not m_cap.isOpened():
        raise RuntimeError("Could not open RTMPose overlay videos for side-by-side comparison")
    fps = float(s_cap.get(cv2.CAP_PROP_FPS) or m_cap.get(cv2.CAP_PROP_FPS) or 30.0)
    width = int(s_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(s_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output_video.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width * 2, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not open side-by-side writer: {output_video}")
    while True:
        s_ok, s_frame = s_cap.read()
        m_ok, m_frame = m_cap.read()
        if not s_ok or not m_ok:
            break
        if s_frame.shape[:2] != m_frame.shape[:2]:
            m_frame = cv2.resize(m_frame, (width, height), interpolation=cv2.INTER_AREA)
        draw_title(s_frame, "RTMPose-s")
        draw_title(m_frame, "RTMPose-m")
        writer.write(np.concatenate([s_frame, m_frame], axis=1))
    s_cap.release()
    m_cap.release()
    writer.release()


def draw_title(frame, title):
    import cv2

    cv2.rectangle(frame, (8, 8), (180, 40), (0, 0, 0), -1)
    cv2.putText(frame, title, (16, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)


def save_csv(path, s_metrics, m_metrics, comparison):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "metric_type",
        "index",
        "name",
        "rtmpose_s",
        "rtmpose_m",
        "delta_m_minus_s",
        "mean_disagreement_px",
        "median_disagreement_px",
        "comparable_frame_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for key in ("upper_body_valid_ratio", "lower_body_valid_ratio", "full_body_valid_ratio"):
            writer.writerow(
                {
                    "metric_type": key,
                    "rtmpose_s": s_metrics[key],
                    "rtmpose_m": m_metrics[key],
                    "delta_m_minus_s": m_metrics[key] - s_metrics[key],
                },
            )
        for s_row, m_row in zip(s_metrics["keypoints"], m_metrics["keypoints"]):
            writer.writerow(
                {
                    "metric_type": "mean_confidence",
                    "index": s_row["index"],
                    "name": s_row["name"],
                    "rtmpose_s": s_row["mean_confidence"],
                    "rtmpose_m": m_row["mean_confidence"],
                    "delta_m_minus_s": m_row["mean_confidence"] - s_row["mean_confidence"],
                },
            )
        for name in [COCO17_NAMES[index] for index in MAJOR_INDICES]:
            s_value = s_metrics["mean_jitter_px"].get(name)
            m_value = m_metrics["mean_jitter_px"].get(name)
            writer.writerow(
                {
                    "metric_type": "mean_jitter_px",
                    "name": name,
                    "rtmpose_s": s_value,
                    "rtmpose_m": m_value,
                    "delta_m_minus_s": None if s_value is None or m_value is None else m_value - s_value,
                },
            )
        for row in comparison["rows"]:
            writer.writerow(
                {
                    "metric_type": "s_vs_m_disagreement_px",
                    "index": row["index"],
                    "name": row["name"],
                    "mean_disagreement_px": row["mean_disagreement_px"],
                    "median_disagreement_px": row["median_disagreement_px"],
                    "comparable_frame_count": row["comparable_frame_count"],
                },
            )


def compact_metrics(metrics):
    worst = sorted(metrics["keypoints"], key=lambda row: row["mean_confidence"])[:5]
    return {
        "processed_frames": metrics["processed_frames"],
        "detected_frames": metrics["detected_frames"],
        "upper_body_valid_ratio": metrics["upper_body_valid_ratio"],
        "lower_body_valid_ratio": metrics["lower_body_valid_ratio"],
        "full_body_valid_ratio": metrics["full_body_valid_ratio"],
        "worst_keypoints": [
            {
                "name": row["name"],
                "mean_confidence": row["mean_confidence"],
                "low_confidence_frame_count": row["low_confidence_frame_count"],
            }
            for row in worst
        ],
        "mean_jitter_px": metrics["mean_jitter_px"],
    }


def recommend(s_metrics, m_metrics, comparison):
    valid_gain = m_metrics["full_body_valid_ratio"] - s_metrics["full_body_valid_ratio"]
    upper_gain = m_metrics["upper_body_valid_ratio"] - s_metrics["upper_body_valid_ratio"]
    lower_gain = m_metrics["lower_body_valid_ratio"] - s_metrics["lower_body_valid_ratio"]
    mean_s = np.mean([row["mean_confidence"] for row in s_metrics["keypoints"]])
    mean_m = np.mean([row["mean_confidence"] for row in m_metrics["keypoints"]])
    confidence_gain = float(mean_m - mean_s)
    disagreement = comparison["major_joint_mean_disagreement_px"]
    if valid_gain > 0.05 or confidence_gain > 0.03:
        return (
            "RTMPose-m shows a measurable confidence/validity improvement. Keep it as a candidate, "
            "but use visual review because confidence is not ground truth."
        )
    if upper_gain < -0.05 or lower_gain < -0.05 or confidence_gain < -0.03:
        return "RTMPose-m does not improve this clip by confidence/validity metrics."
    if disagreement is not None and disagreement > 25.0:
        return (
            "RTMPose-m differs substantially from RTMPose-s, but metrics alone do not prove better accuracy. "
            "The remaining issue is likely view/occlusion-sensitive and needs visual review."
        )
    return (
        "RTMPose-m is similar to RTMPose-s on confidence/validity metrics. "
        "Any remaining error is more likely view/occlusion related than model-size related."
    )


if __name__ == "__main__":
    raise SystemExit(main())
