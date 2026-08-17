from dataclasses import dataclass
import unittest

from pose_feedback.config import PUSHUP_SIDE_CONFIG, WristExerciseConfig
from pose_feedback.feedback.engine import FeedbackEngine
from pose_feedback.wrist.geometry import (
    bend_angle_to_risk,
    crop_to_image_coords,
    valid_forearm_projection,
)
from pose_feedback.wrist.smoothing import ResultHolder


@dataclass
class Landmark:
    x: float
    y: float


class PushupSideMvpTest(unittest.TestCase):
    def test_crop_to_image_coords(self):
        point = crop_to_image_coords(Landmark(0.5, 0.5), 100, 100, 200, 200)
        self.assertEqual(point, (150.0, 150.0))

    def test_bend_angle_to_risk(self):
        self.assertEqual(bend_angle_to_risk(180), 0.0)
        self.assertEqual(bend_angle_to_risk(160), 20.0)
        self.assertEqual(bend_angle_to_risk(140), 40.0)

    def test_valid_forearm_projection(self):
        self.assertFalse(
            valid_forearm_projection(
                elbow_px=(0.0, 0.0),
                wrist_px=(10.0, 0.0),
                shoulder_width_px=100.0,
                min_forearm_ratio=0.15,
            ),
        )
        self.assertTrue(
            valid_forearm_projection(
                elbow_px=(0.0, 0.0),
                wrist_px=(20.0, 0.0),
                shoulder_width_px=100.0,
                min_forearm_ratio=0.15,
            ),
        )

    def test_result_holder_time_hold(self):
        holder = ResultHolder(max_hold_seconds=0.25)
        valid = {"valid": True, "bend_state": "good"}
        invalid = {"valid": False, "global_invalid_reason": "no_hand_landmarks"}

        first = holder.update(valid, current_time_sec=1.0)
        self.assertFalse(first["is_held"])

        held = holder.update(invalid, current_time_sec=1.2)
        self.assertTrue(held["is_held"])
        self.assertAlmostEqual(held["hold_duration_sec"], 0.2)
        self.assertEqual(held["global_invalid_reason"], "no_hand_landmarks")

        expired = holder.update(invalid, current_time_sec=1.3)
        self.assertFalse(expired["valid"])
        self.assertNotIn("is_held", expired)

    def test_feedback_engine_held_side_gate(self):
        config = WristExerciseConfig(
            name=PUSHUP_SIDE_CONFIG.name,
            use_bend=True,
            use_rotation=False,
            use_symmetry=True,
            use_rep_phase=False,
            feedback_min_interval_seconds=1.0,
        )
        left_held_bad = {
            "valid": True,
            "is_held": True,
            "bend_state": "bad",
        }
        right_bad = {
            "valid": True,
            "is_held": False,
            "bend_state": "bad",
        }
        left_bad = {
            "valid": True,
            "is_held": False,
            "bend_state": "bad",
        }
        right_held_bad = {
            "valid": True,
            "is_held": True,
            "bend_state": "bad",
        }
        symmetry_bad = {"valid": True, "symmetry_state": "bad"}

        engine = FeedbackEngine(config)
        feedbacks = engine.generate(
            left_result=left_held_bad,
            right_result=right_bad,
            symmetry_result=symmetry_bad,
            current_time_sec=10.0,
        )
        self.assertEqual([item["type"] for item in feedbacks], ["right:bend_bad"])

        engine.reset()
        feedbacks = engine.generate(
            left_result=left_bad,
            right_result=right_held_bad,
            symmetry_result=symmetry_bad,
            current_time_sec=10.0,
        )
        self.assertEqual([item["type"] for item in feedbacks], ["left:bend_bad"])

        engine.reset()
        feedbacks = engine.generate(
            left_result=left_held_bad,
            right_result=right_bad,
            symmetry_result=symmetry_bad,
            current_time_sec=10.0,
        )
        self.assertNotIn("symmetry_bad", [item["type"] for item in feedbacks])


if __name__ == "__main__":
    unittest.main()
