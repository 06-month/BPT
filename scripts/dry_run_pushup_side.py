from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.config import PUSHUP_SIDE_CONFIG
from pose_feedback.body.body_adapter import coco_yolo_keypoints_to_body
from pose_feedback.feedback.engine import FeedbackEngine
from pose_feedback.wrist.estimator import WristEstimator


@dataclass
class FakeLandmark:
    x: float = 0.0
    y: float = 0.0


class FakeHandLandmarks:
    def __init__(self, middle_mcp_px, crop_box):
        x1, y1, x2, y2 = crop_box
        middle_mcp = FakeLandmark(
            x=(middle_mcp_px[0] - x1) / (x2 - x1),
            y=(middle_mcp_px[1] - y1) / (y2 - y1),
        )
        self.landmark = [FakeLandmark() for _ in range(21)]
        self.landmark[9] = middle_mcp


def middle_mcp_for_bend_angle(wrist_px, angle_deg, length_px=100.0):
    theta = radians(180.0 - angle_deg)
    return (
        wrist_px[0] + length_px * cos(theta),
        wrist_px[1] + length_px * sin(theta),
    )


def make_frame(timestamp_sec, bend_angle_deg=None, elbow_conf=1.0, wrist_conf=1.0):
    keypoints = synthetic_coco_keypoints(elbow_conf=elbow_conf, wrist_conf=wrist_conf)
    body = coco_yolo_keypoints_to_body(keypoints)
    left_body = body["left"]
    wrist_px = left_body["wrist_px"]
    crop_box = (0, 0, 640, 480)
    hand_landmarks = None
    if bend_angle_deg is not None:
        middle_mcp_px = middle_mcp_for_bend_angle(wrist_px, bend_angle_deg)
        hand_landmarks = FakeHandLandmarks(middle_mcp_px, crop_box)
    return {
        "timestamp_sec": timestamp_sec,
        "body": body,
        "hand_landmarks": hand_landmarks,
        "hand_world_landmarks": None,
        "crop_box": crop_box,
    }


def synthetic_coco_keypoints(elbow_conf=1.0, wrist_conf=1.0):
    keypoints = [[0.0, 0.0, 0.0] for _ in range(17)]
    keypoints[5] = [120.0, 180.0, 1.0]
    keypoints[6] = [520.0, 180.0, 1.0]
    keypoints[7] = [220.0, 240.0, elbow_conf]
    keypoints[8] = [420.0, 240.0, 1.0]
    keypoints[9] = [320.0, 240.0, wrist_conf]
    keypoints[10] = [480.0, 240.0, 1.0]
    return keypoints


def main():
    config = PUSHUP_SIDE_CONFIG
    estimator = WristEstimator(config)
    feedback_engine = FeedbackEngine(config)
    frames = [
        make_frame(0.0, bend_angle_deg=180.0),
        make_frame(0.4, bend_angle_deg=110.0),
        make_frame(0.8, bend_angle_deg=100.0),
        make_frame(0.95, bend_angle_deg=None, elbow_conf=0.0),
        make_frame(1.2, bend_angle_deg=None, elbow_conf=0.0),
    ]

    for frame in frames:
        left_body = frame["body"]["left"]
        result = estimator.estimate(
            elbow_px=left_body["elbow_px"],
            wrist_px=left_body["wrist_px"],
            elbow_conf=left_body["elbow_conf"],
            wrist_conf=left_body["wrist_conf"],
            shoulder_width_px=frame["body"]["shoulder_width_px"],
            hand_landmarks=frame["hand_landmarks"],
            hand_world_landmarks=frame["hand_world_landmarks"],
            crop_box=frame["crop_box"],
            is_right_hand=True,
            current_time_sec=frame["timestamp_sec"],
        )
        feedbacks = feedback_engine.generate(
            left_result=result,
            current_time_sec=frame["timestamp_sec"],
        )
        print(
            {
                "timestamp_sec": frame["timestamp_sec"],
                "bend_valid": result["bend_valid"],
                "bend_angle_2d": result["bend_angle_2d"],
                "bend_risk": result["bend_risk"],
                "bend_state": result["bend_state"],
                "valid": result["valid"],
                "is_held": result["is_held"],
                "hold_duration_sec": result["hold_duration_sec"],
                "global_invalid_reason": result["global_invalid_reason"],
                "feedbacks": feedbacks,
            },
        )


if __name__ == "__main__":
    main()
