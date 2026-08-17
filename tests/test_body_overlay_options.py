import sys
import types
import unittest

import numpy as np

from scripts import visualize_rtmpose_body_and_both_hands as viz


class FakeCV2:
    LINE_AA = 16
    FONT_HERSHEY_SIMPLEX = 0

    def __init__(self):
        self.lines = []
        self.arrows = []
        self.rectangles = []
        self.text = []
        self.circles = []

    def line(self, image, a, b, color, thickness, line_type):
        self.lines.append((a, b))

    def arrowedLine(self, image, a, b, color, thickness, tipLength):
        self.arrows.append((a, b))

    def rectangle(self, image, a, b, color, thickness):
        self.rectangles.append((a, b))

    def circle(self, image, point, radius, color, fill):
        self.circles.append(point)

    def putText(self, image, text, origin, font, font_scale, color, thickness, line_type):
        self.text.append(text)


class BodyOverlayOptionsTests(unittest.TestCase):
    def setUp(self):
        self.original_cv2 = sys.modules.get("cv2")
        self.fake_cv2 = FakeCV2()
        sys.modules["cv2"] = self.fake_cv2

    def tearDown(self):
        if self.original_cv2 is None:
            sys.modules.pop("cv2", None)
        else:
            sys.modules["cv2"] = self.original_cv2

    def test_hide_body_wrist_limbs_skips_elbow_to_wrist_lines_only(self):
        keypoints = full_conf_keypoints()

        viz.draw_body(
            np.zeros((10, 10, 3), dtype="uint8"),
            keypoints,
            conf_threshold=0.3,
            sizes=sizes(),
            hide_wrist_limbs=True,
        )

        drawn = set(self.fake_cv2.lines)
        self.assertNotIn(((70, 71), (90, 91)), drawn)
        self.assertNotIn(((80, 81), (100, 101)), drawn)
        self.assertIn(((50, 51), (70, 71)), drawn)
        self.assertIn(((60, 61), (80, 81)), drawn)

    def test_hide_body_skeleton_skips_all_lines_but_keeps_points(self):
        keypoints = full_conf_keypoints()

        viz.draw_body(
            np.zeros((10, 10, 3), dtype="uint8"),
            keypoints,
            conf_threshold=0.3,
            sizes=sizes(),
            hide_skeleton=True,
        )

        self.assertEqual(self.fake_cv2.lines, [])
        self.assertGreater(len(self.fake_cv2.circles), 0)

    def test_hide_body_keypoint_labels_skips_text(self):
        keypoints = full_conf_keypoints()

        viz.draw_body(
            np.zeros((10, 10, 3), dtype="uint8"),
            keypoints,
            conf_threshold=0.3,
            sizes=sizes(),
            hide_keypoint_labels=True,
        )

        self.assertEqual(self.fake_cv2.text, [])

    def test_hide_hand_debug_vectors_keeps_hand_skeleton(self):
        side_result = hand_side_result()

        viz.draw_side_hand(
            np.zeros((100, 100, 3), dtype="uint8"),
            side_result,
            (255, 255, 0),
            sizes(),
            draw_crop=False,
            draw_debug_vectors=False,
        )

        self.assertEqual(self.fake_cv2.arrows, [])
        self.assertGreater(len(self.fake_cv2.lines), 0)
        self.assertGreater(len(self.fake_cv2.circles), 0)

    def test_hand_debug_vectors_draws_two_arrows_by_default(self):
        side_result = hand_side_result()

        viz.draw_side_hand(
            np.zeros((100, 100, 3), dtype="uint8"),
            side_result,
            (255, 255, 0),
            sizes(),
            draw_crop=False,
        )

        self.assertEqual(len(self.fake_cv2.arrows), 2)


def full_conf_keypoints():
    keypoints = np.zeros((17, 3), dtype="float32")
    for idx in range(17):
        keypoints[idx] = [idx * 10.0, idx * 10.0 + 1.0, 1.0]
    return keypoints


def sizes():
    return {
        "line_thickness": 1,
        "body_radius": 2,
        "hand_radius": 1,
        "highlight_radius": 3,
        "font_scale": 0.4,
        "text_thickness": 1,
    }


def hand_side_result():
    landmarks = [
        types.SimpleNamespace(x=0.1 + idx * 0.01, y=0.2 + idx * 0.01)
        for idx in range(21)
    ]
    return {
        "side": "left",
        "side_body": {
            "elbow_px": np.array([10.0, 20.0], dtype="float32"),
            "wrist_px": np.array([30.0, 40.0], dtype="float32"),
        },
        "crop_box": (0, 0, 100, 100),
        "hand_crop_mode": "wrist",
        "hand_result": {
            "hand_landmarks": types.SimpleNamespace(landmark=landmarks),
        },
    }


if __name__ == "__main__":
    unittest.main()
