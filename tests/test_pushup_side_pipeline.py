from dataclasses import dataclass
from math import cos, radians, sin
import unittest

from pose_feedback.app.pushup_side_pipeline import PushupSidePipeline
from pose_feedback.body.body_adapter import coco_yolo_keypoints_to_body
from pose_feedback.config import PUSHUP_SIDE_CONFIG
from pose_feedback.feedback.engine import FeedbackEngine
from pose_feedback.wrist.estimator import WristEstimator


@dataclass
class FakeLandmark:
    x: float = 0.0
    y: float = 0.0


class FakeHandLandmarks:
    def __init__(self, middle_mcp_px, crop_box):
        x1, y1, x2, y2 = crop_box
        self.landmark = [FakeLandmark() for _ in range(21)]
        self.landmark[9] = FakeLandmark(
            x=(middle_mcp_px[0] - x1) / (x2 - x1),
            y=(middle_mcp_px[1] - y1) / (y2 - y1),
        )


class FakeBodyRunner:
    def __init__(self, elbow_conf=1.0, wrist_conf=1.0):
        self.elbow_conf = elbow_conf
        self.wrist_conf = wrist_conf

    def predict_body(self, image):
        keypoints = [[0.0, 0.0, 0.0] for _ in range(17)]
        keypoints[5] = [120.0, 180.0, 1.0]
        keypoints[6] = [520.0, 180.0, 1.0]
        keypoints[7] = [220.0, 240.0, self.elbow_conf]
        keypoints[8] = [420.0, 240.0, 1.0]
        keypoints[9] = [320.0, 240.0, self.wrist_conf]
        keypoints[10] = [480.0, 240.0, 1.0]
        return coco_yolo_keypoints_to_body(keypoints)


class FakeHandRunner:
    def __init__(self, bend_angle_deg=None):
        self.bend_angle_deg = bend_angle_deg

    def run_crop(self, image, crop_box):
        if self.bend_angle_deg is None:
            return []
        wrist_px = image["wrist_px"]
        theta = radians(180.0 - self.bend_angle_deg)
        middle_mcp_px = (
            wrist_px[0] + 100.0 * cos(theta),
            wrist_px[1] + 100.0 * sin(theta),
        )
        return [
            {
                "hand_landmarks": FakeHandLandmarks(middle_mcp_px, crop_box),
                "hand_world_landmarks": None,
                "handedness": None,
                "wrist_px": wrist_px,
                "crop_box": crop_box,
            },
        ]


class FakeHandDetector:
    def __init__(self, detections):
        self.detections = detections

    def detect(self, image):
        return self.detections


def make_pipeline(body_runner=None, hand_runner=None, hand_detector=None):
    config = PUSHUP_SIDE_CONFIG
    return PushupSidePipeline(
        config=config,
        body_runner=body_runner or FakeBodyRunner(),
        hand_runner=hand_runner or FakeHandRunner(180.0),
        wrist_estimator=WristEstimator(config),
        feedback_engine=FeedbackEngine(config),
        hand_detector=hand_detector,
    )


def image():
    return {
        "image_w": 640,
        "image_h": 480,
        "wrist_px": (320.0, 240.0),
    }


class PushupSidePipelineTest(unittest.TestCase):
    def test_good_synthetic_frame_returns_good_bend_state(self):
        pipeline = make_pipeline(hand_runner=FakeHandRunner(180.0))

        result = pipeline.run_frame(image(), timestamp_sec=0.0)

        self.assertEqual(result["bend_state"], "good")
        self.assertTrue(result["valid"])
        self.assertTrue(result["hand_detected"])

    def test_bad_synthetic_frame_returns_bad_and_feedback(self):
        pipeline = make_pipeline(hand_runner=FakeHandRunner(90.0))

        result = pipeline.run_frame(image(), timestamp_sec=0.0)

        self.assertEqual(result["bend_state"], "bad")
        self.assertEqual([item["type"] for item in result["feedbacks"]], ["left:bend_bad"])

    def test_temporary_missing_hand_returns_held_result(self):
        pipeline = make_pipeline(hand_runner=FakeHandRunner(180.0))
        pipeline.run_frame(image(), timestamp_sec=0.0)
        pipeline.hand_runner = FakeHandRunner(None)

        result = pipeline.run_frame(image(), timestamp_sec=0.1)

        self.assertTrue(result["valid"])
        self.assertTrue(result["is_held"])
        self.assertEqual(result["global_invalid_reason"], "no_hand_landmarks")

    def test_missing_hand_after_hold_timeout_returns_invalid(self):
        pipeline = make_pipeline(hand_runner=FakeHandRunner(180.0))
        pipeline.run_frame(image(), timestamp_sec=0.0)
        pipeline.hand_runner = FakeHandRunner(None)

        result = pipeline.run_frame(image(), timestamp_sec=0.3)

        self.assertFalse(result["valid"])
        self.assertFalse(result["is_held"])
        self.assertEqual(result["global_invalid_reason"], "no_hand_landmarks")

    def test_low_body_confidence_invalid_or_held(self):
        pipeline = make_pipeline(hand_runner=FakeHandRunner(180.0))
        pipeline.run_frame(image(), timestamp_sec=0.0)
        pipeline.body_runner = FakeBodyRunner(elbow_conf=0.1)

        held = pipeline.run_frame(image(), timestamp_sec=0.1)
        self.assertTrue(held["valid"])
        self.assertTrue(held["is_held"])
        self.assertEqual(held["global_invalid_reason"], "low_body_confidence")

        invalid = pipeline.run_frame(image(), timestamp_sec=0.3)
        self.assertFalse(invalid["valid"])
        self.assertFalse(invalid["is_held"])
        self.assertEqual(invalid["global_invalid_reason"], "low_body_confidence")

    def test_detector_bbox_path_is_used_for_crop(self):
        pipeline = make_pipeline(
            hand_runner=FakeHandRunner(180.0),
            hand_detector=FakeHandDetector(
                [
                    {
                        "bbox": (300, 220, 340, 260),
                        "confidence": 0.9,
                        "class_name": "hand",
                    },
                ],
            ),
        )

        result = pipeline.run_frame(image(), timestamp_sec=0.0)

        self.assertEqual(result["crop_box"], (290, 210, 350, 270))
        self.assertEqual(result["bend_state"], "good")

    def test_detector_no_bbox_uses_fallback_crop(self):
        pipeline = make_pipeline(
            hand_runner=FakeHandRunner(180.0),
            hand_detector=FakeHandDetector([]),
        )

        result = pipeline.run_frame(image(), timestamp_sec=0.0)

        self.assertEqual(result["crop_box"], (255, 130, 475, 350))
        self.assertEqual(result["bend_state"], "good")


if __name__ == "__main__":
    unittest.main()
