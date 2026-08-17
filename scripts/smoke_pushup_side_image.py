import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.yolo26_runner import (
    NoPersonDetectedError,
    UltralyticsYOLO26PoseRunner,
)
from pose_feedback.config import PUSHUP_SIDE_CONFIG
from pose_feedback.feedback.engine import FeedbackEngine
from pose_feedback.hand.hand_crop_selector import HandCropSelector
from pose_feedback.hand.mediapipe_hand_runner import (
    MediaPipeHandsRuntimeError,
    MediaPipeHandsRunner,
)
from pose_feedback.wrist.crop import CropBoxSmoother
from pose_feedback.wrist.estimator import WristEstimator


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke test one pushup_side image.")
    parser.add_argument("--model", required=True, help="Path to YOLO26 pose model.")
    parser.add_argument("--image", required=True, help="Path to input image.")
    parser.add_argument(
        "--side",
        default="left",
        choices=("left", "right"),
        help="Visible side to evaluate.",
    )
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
    image = read_image(Path(args.image))
    image_h, image_w = image.shape[:2]
    config = PUSHUP_SIDE_CONFIG

    try:
        body_runner = UltralyticsYOLO26PoseRunner(model_path=args.model)
        body = body_runner.predict_body(image)
    except ImportError as exc:
        print({"yolo_runtime": "unavailable", "reason": str(exc)})
        return 0
    except NoPersonDetectedError as exc:
        print({"body_detected": False, "reason": str(exc)})
        return 0

    side_body = body[args.side]
    crop_selector = HandCropSelector()
    crop_smoother = CropBoxSmoother(alpha=config.crop_smoothing_alpha)
    crop_box = crop_selector.select_crop(
        image_w=image_w,
        image_h=image_h,
        elbow_px=side_body["elbow_px"],
        wrist_px=side_body["wrist_px"],
        hand_bbox=None,
    )
    crop_box = crop_smoother.update(crop_box)

    hand_results = []
    mediapipe_runtime = "available"
    try:
        hand_runner = MediaPipeHandsRunner(
            static_image_mode=True,
            max_num_hands=1,
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3,
            cpu_only=True,
            input_color_format="BGR",
        )
        try:
            hand_results = hand_runner.run_crop(image, crop_box)
        finally:
            hand_runner.close()
    except (ImportError, MediaPipeHandsRuntimeError) as exc:
        mediapipe_runtime = "unavailable"
        print({"mediapipe_runtime": mediapipe_runtime, "reason": str(exc)})
    except Exception as exc:
        mediapipe_runtime = "failed"
        print({"mediapipe_runtime": mediapipe_runtime, "reason": str(exc)})

    hand_result = hand_results[0] if hand_results else None
    estimator = WristEstimator(config)
    result = estimator.estimate(
        elbow_px=side_body["elbow_px"],
        wrist_px=side_body["wrist_px"],
        elbow_conf=side_body["elbow_conf"],
        wrist_conf=side_body["wrist_conf"],
        shoulder_width_px=body["shoulder_width_px"],
        hand_landmarks=None if hand_result is None else hand_result["hand_landmarks"],
        hand_world_landmarks=(
            None if hand_result is None else hand_result["hand_world_landmarks"]
        ),
        crop_box=crop_box,
        is_right_hand=args.side == "right",
        current_time_sec=0.0,
    )
    feedbacks = FeedbackEngine(config).generate(
        left_result=result if args.side == "left" else None,
        right_result=result if args.side == "right" else None,
        current_time_sec=0.0,
    )

    print(
        {
            "body_detected": True,
            "side": args.side,
            "body_keypoints": {
                "shoulder_px": point_to_tuple(side_body["shoulder_px"]),
                "elbow_px": point_to_tuple(side_body["elbow_px"]),
                "wrist_px": point_to_tuple(side_body["wrist_px"]),
                "shoulder_conf": side_body["shoulder_conf"],
                "elbow_conf": side_body["elbow_conf"],
                "wrist_conf": side_body["wrist_conf"],
            },
            "shoulder_width_px": body["shoulder_width_px"],
            "selected_crop_box": crop_box,
            "mediapipe_runtime": mediapipe_runtime,
            "hand_detected": hand_result is not None,
            "handedness": None if hand_result is None else hand_result["handedness"],
            "mediapipe_wrist_px": (
                None if hand_result is None else point_to_tuple(hand_result["wrist_px"])
            ),
            "bend_valid": result["bend_valid"],
            "bend_angle_2d": result["bend_angle_2d"],
            "bend_risk": result["bend_risk"],
            "bend_state": result["bend_state"],
            "valid": result["valid"],
            "is_held": result["is_held"],
            "global_invalid_reason": result["global_invalid_reason"],
            "feedbacks": feedbacks,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
