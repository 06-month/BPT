import unittest

from pose_feedback.hand.hand_detector import select_best_hand_bbox_for_wrist


class HandDetectorHelperTest(unittest.TestCase):
    def test_valid_detection_bbox_is_returned(self):
        bbox = select_best_hand_bbox_for_wrist(
            [{"bbox": (10, 20, 50, 80), "confidence": 0.9, "class_name": "hand"}],
            wrist_px=(30.0, 50.0),
        )

        self.assertEqual(bbox, (10, 20, 50, 80))

    def test_closest_bbox_to_wrist_is_selected(self):
        bbox = select_best_hand_bbox_for_wrist(
            [
                {"bbox": (300, 300, 360, 360), "confidence": 0.95, "class_name": "hand"},
                {"bbox": (90, 90, 130, 130), "confidence": 0.90, "class_name": "hand"},
            ],
            wrist_px=(100.0, 100.0),
        )

        self.assertEqual(bbox, (90, 90, 130, 130))

    def test_low_confidence_detection_is_ignored(self):
        bbox = select_best_hand_bbox_for_wrist(
            [{"bbox": (10, 20, 50, 80), "confidence": 0.49, "class_name": "hand"}],
            wrist_px=(30.0, 50.0),
        )

        self.assertIsNone(bbox)

    def test_invalid_bbox_is_ignored(self):
        bbox = select_best_hand_bbox_for_wrist(
            [{"bbox": (50, 20, 10, 80), "confidence": 0.9, "class_name": "hand"}],
            wrist_px=(30.0, 50.0),
        )

        self.assertIsNone(bbox)

    def test_no_detections_returns_none(self):
        bbox = select_best_hand_bbox_for_wrist([], wrist_px=(30.0, 50.0))

        self.assertIsNone(bbox)

    def test_far_bbox_is_rejected_with_shoulder_width_threshold(self):
        bbox = select_best_hand_bbox_for_wrist(
            [{"bbox": (500, 500, 540, 540), "confidence": 0.9, "class_name": "hand"}],
            wrist_px=(30.0, 50.0),
            shoulder_width_px=100.0,
            max_distance_ratio=0.75,
        )

        self.assertIsNone(bbox)


if __name__ == "__main__":
    unittest.main()
