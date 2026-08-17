import argparse
from importlib.util import find_spec
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.yolo26_runner import (
    NoPersonDetectedError,
    UltralyticsYOLO26PoseRunner,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke test YOLO26 pose adapter.")
    parser.add_argument("--model", required=True, help="Path to an Ultralytics pose model.")
    parser.add_argument("--image", required=True, help="Path to an input image.")
    return parser.parse_args()


def read_image(path):
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise ImportError("cv2 is required for this smoke script.") from exc

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def point_to_tuple(point):
    if point is None:
        return None
    return tuple(float(value) for value in point)


def main():
    args = parse_args()
    if find_spec("ultralytics") is None:
        print("ultralytics is not installed; skipping YOLO26 pose smoke test.")
        return 0

    try:
        image = read_image(Path(args.image))
        runner = UltralyticsYOLO26PoseRunner(model_path=args.model)
        body = runner.predict_body(image)
    except NoPersonDetectedError as exc:
        print({"person_detected": False, "reason": str(exc)})
        return 0

    print({"shoulder_width_px": body["shoulder_width_px"]})
    for side in ("left", "right"):
        side_body = body[side]
        print(
            {
                "side": side,
                "shoulder_px": point_to_tuple(side_body["shoulder_px"]),
                "elbow_px": point_to_tuple(side_body["elbow_px"]),
                "wrist_px": point_to_tuple(side_body["wrist_px"]),
                "shoulder_conf": side_body["shoulder_conf"],
                "elbow_conf": side_body["elbow_conf"],
                "wrist_conf": side_body["wrist_conf"],
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
