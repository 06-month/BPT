import argparse
import csv
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from compare_yolo26_rtmpose_full_body import legacy_openmmlab_checkpoint_load
from pose_feedback.body.rtmpose_runner import RTMPoseNoPersonDetectedError, RTMPoseRunner


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

SKELETON = [
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

LEFT_INDICES = {1, 3, 5, 7, 9, 11, 13, 15}
RIGHT_INDICES = {2, 4, 6, 8, 10, 12, 14, 16}
UPPER_BODY_INDICES = (5, 6, 7, 8, 9, 10)
LOWER_BODY_INDICES = (11, 12, 13, 14, 15, 16)


def parse_args():
    parser = argparse.ArgumentParser(description="Diagnose RTMPose 2D confidence quality on video.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--rtmpose-config", default="models/rtmpose/rtmpose-s_8xb256-420e_coco-256x192.py")
    parser.add_argument("--rtmpose-checkpoint", default="models/rtmpose/rtmpose-s_coco.pth")
    parser.add_argument("--output-video", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--conf-valid-threshold", type=float, default=0.5)
    parser.add_argument("--low-conf-threshold", type=float, default=0.4)
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
    output_video = Path(args.output_video)
    output_jsonl = Path(args.output_jsonl)
    output_csv = Path(args.output_csv)
    for path in (output_video, output_jsonl, output_csv):
        path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with legacy_openmmlab_checkpoint_load():
            runner = RTMPoseRunner(args.rtmpose_config, args.rtmpose_checkpoint, device=args.device)
    except Exception as exc:
        print({"rtmpose_runtime": "unavailable", "reason": f"{type(exc).__name__}: {exc}"})
        cap.release()
        return 0

    writer = make_writer(output_video, fps, image_w, image_h)
    records = []
    processed = 0
    frame_idx = 0
    with output_jsonl.open("w", encoding="utf-8") as fh:
        while args.max_frames <= 0 or processed < args.max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            record = base_record(frame_idx, fps, image_w, image_h)
            try:
                keypoints = runner.predict_keypoints(frame)
                record.update(record_from_keypoints(keypoints, args.conf_valid_threshold))
                draw_overlay(frame, keypoints, record)
            except RTMPoseNoPersonDetectedError:
                draw_no_body(frame, frame_idx)
            fh.write(json.dumps(record, sort_keys=True) + "\n")
            writer.write(frame)
            records.append(record)
            processed += 1
            frame_idx += 1

    cap.release()
    writer.release()

    summary_rows, summary = summarize(records, args.low_conf_threshold)
    save_summary_csv(output_csv, summary_rows)
    print(
        {
            "video_opened": True,
            "video": args.video,
            "processed_frames": processed,
            "output_video": str(output_video),
            "output_jsonl": str(output_jsonl),
            "output_csv": str(output_csv),
            "mean_confidence_per_keypoint": summary["mean_confidence_per_keypoint"],
            "worst_keypoints": summary["worst_keypoints"],
            "upper_body_valid_ratio": summary["upper_body_valid_ratio"],
            "lower_body_valid_ratio": summary["lower_body_valid_ratio"],
            "full_body_valid_ratio": summary["full_body_valid_ratio"],
            "upper_body_only_suitable": summary["upper_body_only_suitable"],
            "suitable_for_3d_lifting": summary["suitable_for_3d_lifting"],
        },
    )
    return 0


def make_writer(path, fps, image_w, image_h):
    import cv2

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (image_w, image_h))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {path}")
    return writer


def base_record(frame_idx, fps, image_w, image_h):
    return {
        "frame_idx": frame_idx,
        "timestamp_sec": frame_idx / fps,
        "image_width": image_w,
        "image_height": image_h,
        "body_detected": False,
        "keypoints_coco17": None,
        "keypoints": [],
        "upper_body_valid": False,
        "lower_body_valid": False,
        "full_body_valid": False,
    }


def record_from_keypoints(keypoints, valid_threshold):
    keypoints = np.asarray(keypoints, dtype="float32")
    upper_valid = all(float(keypoints[index, 2]) >= valid_threshold for index in UPPER_BODY_INDICES)
    lower_valid = all(float(keypoints[index, 2]) >= valid_threshold for index in LOWER_BODY_INDICES)
    return {
        "body_detected": True,
        "keypoints_coco17": keypoints.tolist(),
        "keypoints": keypoint_records(keypoints),
        "upper_body_valid": bool(upper_valid),
        "lower_body_valid": bool(lower_valid),
        "full_body_valid": bool(upper_valid and lower_valid),
    }


def keypoint_records(keypoints):
    records = []
    for index, name in enumerate(COCO17_NAMES):
        records.append(
            {
                "index": index,
                "name": name,
                "x": float(keypoints[index, 0]),
                "y": float(keypoints[index, 1]),
                "confidence": float(keypoints[index, 2]),
            },
        )
    return records


def draw_overlay(image, keypoints, record):
    import cv2

    keypoints = np.asarray(keypoints, dtype="float32")
    for a, b in SKELETON:
        conf = min(confidence(keypoints, a), confidence(keypoints, b))
        cv2.line(
            image,
            point_to_int(keypoints[a]),
            point_to_int(keypoints[b]),
            color_for_conf(conf, a, b),
            thickness_for_conf(conf),
            cv2.LINE_AA,
        )
    for index, name in enumerate(COCO17_NAMES):
        conf = confidence(keypoints, index)
        point = point_to_int(keypoints[index])
        color = color_for_conf(conf, index, index)
        radius = radius_for_conf(conf)
        thickness = -1 if conf >= 0.4 else 1
        cv2.circle(image, point, radius, color, thickness, cv2.LINE_AA)
        cv2.putText(
            image,
            f"{index}:{conf:.2f}",
            (point[0] + 5, point[1] - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            color,
            1,
            cv2.LINE_AA,
        )
    draw_status_text(image, record)


def draw_no_body(image, frame_idx):
    import cv2

    cv2.putText(
        image,
        f"frame {frame_idx} | no RTMPose body",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2,
        cv2.LINE_AA,
    )


def draw_status_text(image, record):
    import cv2

    lines = [
        f"frame {record['frame_idx']} RTMPose COCO17",
        f"upper_valid={record['upper_body_valid']}",
        f"lower_valid={record['lower_body_valid']}",
        f"full_valid={record['full_body_valid']}",
    ]
    x, y = 10, 22
    for line in lines:
        cv2.putText(image, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 0), 1, cv2.LINE_AA)
        y += 18


def color_for_conf(conf, a, b):
    if conf < 0.4:
        return (145, 145, 145)
    if a in LEFT_INDICES and b in LEFT_INDICES:
        base = (255, 80, 40)
    elif a in RIGHT_INDICES and b in RIGHT_INDICES:
        base = (40, 165, 255)
    else:
        base = (40, 220, 80)
    if conf < 0.7:
        return tuple(int(channel * 0.7 + 90 * 0.3) for channel in base)
    return base


def thickness_for_conf(conf):
    if conf >= 0.7:
        return 3
    if conf >= 0.4:
        return 2
    return 1


def radius_for_conf(conf):
    if conf >= 0.7:
        return 5
    if conf >= 0.4:
        return 4
    return 3


def confidence(keypoints, index):
    return float(keypoints[index, 2])


def point_to_int(row):
    return int(round(float(row[0]))), int(round(float(row[1])))


def summarize(records, low_conf_threshold):
    detected = [record for record in records if record["body_detected"] and record["keypoints_coco17"] is not None]
    if not records or not detected:
        return [], empty_summary()
    confs = np.asarray([[kp["confidence"] for kp in record["keypoints"]] for record in detected], dtype="float32")
    summary_rows = []
    for index, name in enumerate(COCO17_NAMES):
        values = confs[:, index]
        summary_rows.append(
            {
                "index": index,
                "name": name,
                "mean_confidence": float(np.mean(values)),
                "median_confidence": float(np.median(values)),
                "low_confidence_frame_count": int(np.sum(values < low_conf_threshold)),
                "low_confidence_frame_ratio": float(np.mean(values < low_conf_threshold)),
            },
        )
    worst = sorted(summary_rows, key=lambda row: row["mean_confidence"])[:5]
    total = len(records)
    upper_count = sum(1 for record in records if record["upper_body_valid"])
    lower_count = sum(1 for record in records if record["lower_body_valid"])
    full_count = sum(1 for record in records if record["full_body_valid"])
    summary = {
        "mean_confidence_per_keypoint": {
            row["name"]: row["mean_confidence"]
            for row in summary_rows
        },
        "median_confidence_per_keypoint": {
            row["name"]: row["median_confidence"]
            for row in summary_rows
        },
        "worst_keypoints": [
            {
                "index": row["index"],
                "name": row["name"],
                "mean_confidence": row["mean_confidence"],
                "low_confidence_frame_count": row["low_confidence_frame_count"],
            }
            for row in worst
        ],
        "upper_body_valid_frame_count": upper_count,
        "lower_body_valid_frame_count": lower_count,
        "full_body_valid_frame_count": full_count,
        "upper_body_valid_ratio": upper_count / total,
        "lower_body_valid_ratio": lower_count / total,
        "full_body_valid_ratio": full_count / total,
        "upper_body_only_suitable": (upper_count / total) >= 0.8,
        "suitable_for_3d_lifting": (full_count / total) >= 0.8,
    }
    return summary_rows, summary


def empty_summary():
    return {
        "mean_confidence_per_keypoint": {},
        "median_confidence_per_keypoint": {},
        "worst_keypoints": [],
        "upper_body_valid_frame_count": 0,
        "lower_body_valid_frame_count": 0,
        "full_body_valid_frame_count": 0,
        "upper_body_valid_ratio": 0.0,
        "lower_body_valid_ratio": 0.0,
        "full_body_valid_ratio": 0.0,
        "upper_body_only_suitable": False,
        "suitable_for_3d_lifting": False,
    }


def save_summary_csv(path, rows):
    fieldnames = [
        "index",
        "name",
        "mean_confidence",
        "median_confidence",
        "low_confidence_frame_count",
        "low_confidence_frame_ratio",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
