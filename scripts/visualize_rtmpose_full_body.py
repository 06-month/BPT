import argparse
from contextlib import contextmanager
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.body_adapter import coco_yolo_keypoints_to_body
from pose_feedback.body.rtmpose_runner import (
    RTMPoseNoPersonDetectedError,
    RTMPoseRunner,
)


KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]
SKELETON = [
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12), (11, 13), (13, 15),
    (12, 14), (14, 16), (0, 1), (0, 2), (1, 3), (2, 4),
]
LEFT_INDICES = {1, 3, 5, 7, 9, 11, 13, 15}
RIGHT_INDICES = {2, 4, 6, 8, 10, 12, 14, 16}


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize RTMPose COCO body keypoints.")
    parser.add_argument("--pose-config", required=True)
    parser.add_argument("--pose-checkpoint", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="cpu", choices=("cpu", "mps", "cuda"))
    parser.add_argument("--conf-threshold", type=float, default=0.3)
    parser.add_argument("--marker-scale", type=float, default=1.0)
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
        with legacy_openmmlab_checkpoint_load():
            runner = RTMPoseRunner(
                pose_config=args.pose_config,
                pose_checkpoint=args.pose_checkpoint,
                device=args.device,
            )
            keypoints = runner.predict_keypoints(image)
    except ImportError as exc:
        print({"body_detected": False, "rtmpose_runtime": "unavailable", "reason": str(exc)})
        return 0
    except RTMPoseNoPersonDetectedError as exc:
        print({"body_detected": False, "reason": str(exc)})
        return 0

    body = coco_yolo_keypoints_to_body(keypoints)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    sizes = drawing_sizes(image.shape[1], image.shape[0], args.marker_scale)
    draw_overlay(image, keypoints, output, args.conf_threshold, sizes)
    print(
        {
            "body_detected": True,
            "output": str(output),
            "shoulder_width_px": body["shoulder_width_px"],
            "keypoints": keypoints_to_records(keypoints),
        },
    )
    return 0


@contextmanager
def legacy_openmmlab_checkpoint_load():
    try:
        import torch
    except Exception:
        yield
        return

    original_load = torch.load

    def load_with_legacy_default(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)

    torch.load = load_with_legacy_default
    try:
        yield
    finally:
        torch.load = original_load


def drawing_sizes(image_w, image_h, marker_scale):
    base = max(1.0, min(image_w, image_h) / 300.0)
    return {
        "radius": max(2, int(3 * base * marker_scale)),
        "line": max(1, int(2 * base * marker_scale)),
        "font": max(0.35, 0.45 * base * marker_scale),
        "text": max(1, int(1 * base * marker_scale)),
    }


def draw_overlay(image, keypoints, output, conf_threshold, sizes):
    import cv2

    overlay = image.copy()
    for a, b in SKELETON:
        if confidence(keypoints, a) < conf_threshold or confidence(keypoints, b) < conf_threshold:
            continue
        cv2.line(overlay, point_to_int(keypoints[a]), point_to_int(keypoints[b]), skeleton_color(a, b), sizes["line"], cv2.LINE_AA)

    for index, name in enumerate(KEYPOINT_NAMES):
        point = point_to_int(keypoints[index])
        conf = confidence(keypoints, index)
        if conf < conf_threshold:
            cv2.circle(overlay, point, sizes["radius"], (150, 150, 150), 1)
            continue
        color = keypoint_color(index)
        cv2.circle(overlay, point, sizes["radius"], color, -1)
        cv2.circle(overlay, point, sizes["radius"] + 2, (255, 255, 255), 1)
        cv2.putText(
            overlay,
            f"{index} {short_name(name)} {conf:.2f}",
            (point[0] + sizes["radius"] + 3, point[1] - sizes["radius"] - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            sizes["font"],
            color,
            sizes["text"],
            cv2.LINE_AA,
        )
    cv2.imwrite(str(output), overlay)


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
    return [
        {
            "index": index,
            "name": name,
            "x": float(keypoints[index][0]),
            "y": float(keypoints[index][1]),
            "confidence": float(keypoints[index][2]),
        }
        for index, name in enumerate(KEYPOINT_NAMES)
    ]


if __name__ == "__main__":
    raise SystemExit(main())
