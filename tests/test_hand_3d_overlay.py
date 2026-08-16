from types import SimpleNamespace
import unittest

import numpy as np

from pose_feedback.hand.hand_3d_overlay import (
    build_hand_3d_overlay,
    transform_hand_local_axes,
)


def landmarks(points):
    return SimpleNamespace(
        landmark=[SimpleNamespace(x=x, y=y, z=z) for x, y, z in points],
    )


class Hand3DOverlayTest(unittest.TestCase):
    def test_transform_axis_map_and_flips(self):
        points = np.asarray([[1.0, 2.0, 3.0], [-2.0, 4.0, -6.0]], dtype="float32")

        transformed = transform_hand_local_axes(points, axis_map="z,x,y", flip_y=True)

        self.assertTrue(
            np.allclose(
                transformed,
                np.asarray([[3.0, -1.0, 2.0], [-6.0, 2.0, 4.0]], dtype="float32"),
            ),
        )

    def test_wrist_anchored_subtracts_hand_wrist_and_attaches_to_body_wrist(self):
        pts = [(1.0, 2.0, 3.0)] * 21
        pts[9] = (1.5, 2.25, 2.5)
        body = np.zeros((17, 3), dtype="float32")
        body[13] = [10.0, 20.0, 30.0]

        result = build_hand_3d_overlay(
            hand_result={"hand_world_landmarks": landmarks(pts)},
            body_joints_3d=body,
            side="left",
            mode="wrist-anchored",
            scale=2.0,
        )

        self.assertTrue(result["available"])
        self.assertEqual(result["body_wrist_index"], 13)
        self.assertEqual(result["body_wrist_3d"], [10.0, 20.0, 30.0])
        self.assertEqual(result["attached_landmarks"][0], [10.0, 20.0, 30.0])
        self.assertEqual(result["attached_landmarks"][9], [11.0, 20.5, 29.0])
        self.assertEqual(result["anchor_error"], 0.0)
        self.assertTrue(result["anchor_matches_body_wrist"])

    def test_missing_world_landmarks_is_nonfatal(self):
        result = build_hand_3d_overlay(
            hand_result={"hand_world_landmarks": None},
            body_joints_3d=np.zeros((17, 3), dtype="float32"),
            side="right",
            mode="wrist-anchored",
            scale=1.0,
        )

        self.assertFalse(result["available"])
        self.assertEqual(result["skip_reason"], "no_hand_world_landmarks")


if __name__ == "__main__":
    unittest.main()
