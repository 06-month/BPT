import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.body_adapter import coco_yolo_keypoints_to_body
from pose_feedback.body.yolo26_runner import (
    NoPersonDetectedError,
    UltralyticsYOLO26PoseRunner,
)


KEYPOINT_NAMES = [
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


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize YOLO26 COCO body keypoints.")
    parser.add_argument("--model", required=True, help="Path to YOLO26 pose model.")
    parser.add_argument("--image", required=True, help="Path to input image.")
    parser.add_argument(
        "--output",
        default="assets/smoke/yolo26_full_body_overlay.jpg",
        help="Path for output overlay image.",
    )
    parser.add_argument(
        "--conf-threshold",
        type=float,
        default=0.3,
        help="Minimum confidence for visible keypoints and skeleton lines.",
    )
    return parser.parse_args()


def read_image(path):
    import cv2

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def main():
    args = parse_args()
    image = read_image(Path(args.image))
    try:
        runner = UltralyticsYOLO26PoseRunner(model_path=args.model)
        keypoints = runner.predict_keypoints(image)
    except ImportError as exc:
        print({"body_detected": False, "yolo_runtime": "unavailable", "reason": str(exc)})
        return 0
    except NoPersonDetectedError as exc:
        print({"body_detected": False, "reason": str(exc)})
        return 0

    body = coco_yolo_keypoints_to_body(keypoints)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    draw_overlay(
        image=image,
        keypoints=keypoints,
        output=output,
        conf_threshold=args.conf_threshold,
    )
    print(
        {
            "body_detected": True,
            "output": str(output),
            "keypoints": keypoints_to_records(keypoints),
            "shoulder_width_px": body["shoulder_width_px"],
        },
    )
    return 0


def draw_overlay(image, keypoints, output, conf_threshold):
    import cv2

    overlay = image.copy()
    for a, b in SKELETON:
        if confidence(keypoints, a) < conf_threshold or confidence(keypoints, b) < conf_threshold:
            continue
        cv2.line(
            overlay,
            point_to_int(keypoints[a]),
            point_to_int(keypoints[b]),
            skeleton_color(a, b),
            3,
            cv2.LINE_AA,
        )

    for index, name in enumerate(KEYPOINT_NAMES):
        conf = confidence(keypoints, index)
        if conf < conf_threshold:
            draw_low_confidence_point(overlay, keypoints[index], index, name, conf)
            continue
        point = point_to_int(keypoints[index])
        color = keypoint_color(index)
        cv2.circle(overlay, point, 8, color, -1)
        cv2.circle(overlay, point, 10, (255, 255, 255), 2)
        cv2.putText(
            overlay,
            f"{index} {short_name(name)} {conf:.2f}",
            (point[0] + 8, point[1] - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            color,
            2,
            cv2.LINE_AA,
        )
    cv2.imwrite(str(output), overlay)


def draw_low_confidence_point(image, row, index, name, conf):
    import cv2

    point = point_to_int(row)
    cv2.circle(image, point, 5, (150, 150, 150), 1)
    cv2.putText(
        image,
        f"{index} {short_name(name)} {conf:.2f}",
        (point[0] + 6, point[1] - 6),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (150, 150, 150),
        1,
        cv2.LINE_AA,
    )


def keypoint_color(index):
    if index in LEFT_INDICES:
        return (255, 0, 0)
    if index in RIGHT_INDICES:
        return (0, 165, 255)
    return (0, 200, 0)


def skeleton_color(a, b):
    if a in LEFT_INDICES and b in LEFT_INDICES:
        return (255, 0, 0)
    if a in RIGHT_INDICES and b in RIGHT_INDICES:
        return (0, 165, 255)
    return (0, 200, 0)


def short_name(name):
    return (
        name.replace("left_", "L_")
        .replace("right_", "R_")
        .replace("shoulder", "sho")
        .replace("elbow", "elb")
        .replace("wrist", "wri")
        .replace("ankle", "ank")
        .replace("knee", "kne")
    )


def confidence(keypoints, index):
    return float(keypoints[index][2])


def point_to_int(row):
    return int(round(float(row[0]))), int(round(float(row[1])))


def keypoints_to_records(keypoints):
    records = []
    for index, name in enumerate(KEYPOINT_NAMES):
        records.append(
            {
                "index": index,
                "name": name,
                "x": float(keypoints[index][0]),
                "y": float(keypoints[index][1]),
                "confidence": float(keypoints[index][2]),
            },
        )
    return records


if __name__ == "__main__":
    raise SystemExit(main())
