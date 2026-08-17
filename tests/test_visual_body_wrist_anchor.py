import unittest

import numpy as np

from pose_feedback.body.motionagformer_wrist_source import build_motionagformer_input_2d
from pose_feedback.body.visual_body_wrist_anchor import build_visual_body_2d


class VisualBodyWristAnchorTests(unittest.TestCase):
    def test_raw_rtmpose_keypoints_are_not_mutated(self):
        raw = synthetic_coco()
        original = raw.copy()

        visual, _ = build_visual_body_2d(
            raw,
            mediapipe_wrists_px={"left": [101.0, 202.0]},
            body_wrist_anchor="mediapipe",
        )

        np.testing.assert_allclose(raw, original)
        self.assertFalse(np.shares_memory(raw, visual))

    def test_rtmpose_mode_leaves_visual_body_wrist_unchanged(self):
        raw = synthetic_coco()

        visual, debug = build_visual_body_2d(
            raw,
            mediapipe_wrists_px={"left": [101.0, 202.0], "right": [303.0, 404.0]},
            body_wrist_anchor="rtmpose",
        )

        np.testing.assert_allclose(visual, raw)
        self.assertEqual(debug["left"]["source_used"], "rtmpose")
        self.assertEqual(debug["right"]["source_used"], "rtmpose")

    def test_mediapipe_mode_replaces_left_visual_wrist_when_left_exists(self):
        raw = synthetic_coco()

        visual, debug = build_visual_body_2d(
            raw,
            mediapipe_wrists_px={"left": [101.0, 202.0]},
            body_wrist_anchor="mediapipe",
        )

        np.testing.assert_allclose(visual[9, :2], [101.0, 202.0])
        np.testing.assert_allclose(visual[10, :2], raw[10, :2])
        self.assertEqual(visual[9, 2], raw[9, 2])
        self.assertEqual(debug["left"]["source_used"], "mediapipe")
        self.assertEqual(debug["right"]["source_used"], "fallback")

    def test_mediapipe_mode_replaces_right_visual_wrist_when_right_exists(self):
        raw = synthetic_coco()

        visual, debug = build_visual_body_2d(
            raw,
            mediapipe_wrists_px={"right": [303.0, 404.0]},
            body_wrist_anchor="mediapipe",
        )

        np.testing.assert_allclose(visual[9, :2], raw[9, :2])
        np.testing.assert_allclose(visual[10, :2], [303.0, 404.0])
        self.assertEqual(visual[10, 2], raw[10, 2])
        self.assertEqual(debug["left"]["source_used"], "fallback")
        self.assertEqual(debug["right"]["source_used"], "mediapipe")

    def test_mediapipe_mode_falls_back_when_hand_missing(self):
        raw = synthetic_coco()

        visual, debug = build_visual_body_2d(
            raw,
            mediapipe_wrists_px={},
            body_wrist_anchor="mediapipe",
        )

        np.testing.assert_allclose(visual, raw)
        self.assertEqual(debug["left"]["source_used"], "fallback")
        self.assertEqual(debug["right"]["source_used"], "fallback")

    def test_body_wrist_anchor_does_not_affect_motionagformer_input(self):
        raw = synthetic_coco()
        visual, _ = build_visual_body_2d(
            raw,
            mediapipe_wrists_px={"left": [101.0, 202.0]},
            body_wrist_anchor="mediapipe",
        )
        motion_input, _ = build_motionagformer_input_2d(
            raw,
            mediapipe_wrists_px={"left": [101.0, 202.0]},
            wrist_source="rtmpose",
        )

        np.testing.assert_allclose(visual[9, :2], [101.0, 202.0])
        np.testing.assert_allclose(motion_input[9, :2], raw[9, :2])

    def test_motionagformer_wrist_source_does_not_affect_visual_body_wrist(self):
        raw = synthetic_coco()
        visual, _ = build_visual_body_2d(
            raw,
            mediapipe_wrists_px={"right": [303.0, 404.0]},
            body_wrist_anchor="rtmpose",
        )
        motion_input, _ = build_motionagformer_input_2d(
            raw,
            mediapipe_wrists_px={"right": [303.0, 404.0]},
            wrist_source="mediapipe",
        )

        np.testing.assert_allclose(visual[10, :2], raw[10, :2])
        np.testing.assert_allclose(motion_input[10, :2], [303.0, 404.0])


def synthetic_coco():
    coco = np.zeros((17, 3), dtype="float32")
    for idx in range(17):
        coco[idx] = [idx * 10.0, idx * 10.0 + 1.0, 0.5 + idx * 0.01]
    return coco


if __name__ == "__main__":
    unittest.main()
