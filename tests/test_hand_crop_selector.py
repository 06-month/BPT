import unittest

from pose_feedback.hand.hand_crop_selector import HandCropSelector
from pose_feedback.wrist.crop import make_forward_hand_crop_box


class HandCropSelectorTest(unittest.TestCase):
    def test_detector_bbox_is_expanded_by_margin_ratio(self):
        selector = HandCropSelector(margin_ratio=0.25)

        crop = selector.select_crop(
            image_w=640,
            image_h=480,
            elbow_px=(100.0, 100.0),
            wrist_px=(200.0, 100.0),
            hand_bbox=(100, 100, 200, 180),
        )

        self.assertEqual(crop, (75, 75, 225, 205))

    def test_expanded_bbox_is_clamped_to_image_boundaries(self):
        selector = HandCropSelector(margin_ratio=0.5)

        crop = selector.select_crop(
            image_w=300,
            image_h=200,
            elbow_px=(100.0, 100.0),
            wrist_px=(200.0, 100.0),
            hand_bbox=(250, 10, 290, 50),
        )

        self.assertEqual(crop, (230, 0, 300, 70))

    def test_no_hand_bbox_uses_wrist_anchor_fallback(self):
        selector = HandCropSelector(margin_ratio=0.25)

        crop = selector.select_crop(
            image_w=640,
            image_h=480,
            elbow_px=(220.0, 240.0),
            wrist_px=(320.0, 240.0),
            hand_bbox=None,
        )

        self.assertEqual(
            crop,
            make_forward_hand_crop_box(
                elbow=(220.0, 240.0),
                wrist=(320.0, 240.0),
                image_w=640,
                image_h=480,
            ),
        )

    def test_fallback_crop_returns_valid_box_inside_image_boundaries(self):
        selector = HandCropSelector()

        x1, y1, x2, y2 = selector.select_crop(
            image_w=120,
            image_h=100,
            elbow_px=(80.0, 50.0),
            wrist_px=(110.0, 50.0),
        )

        self.assertGreaterEqual(x1, 0)
        self.assertGreaterEqual(y1, 0)
        self.assertLessEqual(x2, 120)
        self.assertLessEqual(y2, 100)
        self.assertGreater(x2, x1)
        self.assertGreater(y2, y1)

    def test_invalid_bbox_raises_value_error(self):
        selector = HandCropSelector()

        with self.assertRaises(ValueError):
            selector.select_crop(
                image_w=640,
                image_h=480,
                elbow_px=(0.0, 0.0),
                wrist_px=(1.0, 1.0),
                hand_bbox=(100, 100, 90, 120),
            )

    def test_zero_area_bbox_raises_value_error(self):
        selector = HandCropSelector()

        with self.assertRaises(ValueError):
            selector.select_crop(
                image_w=640,
                image_h=480,
                elbow_px=(0.0, 0.0),
                wrist_px=(1.0, 1.0),
                hand_bbox=(100, 100, 100, 120),
            )


if __name__ == "__main__":
    unittest.main()
