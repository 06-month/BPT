import unittest
from types import SimpleNamespace

from pose_feedback.hand.wrist_crop import (
    build_wrist_hand_crop,
    crop_frame,
    map_crop_landmarks_to_frame,
)


class WristCropTest(unittest.TestCase):
    def test_build_wrist_crop_centers_on_wrist(self):
        crop = build_wrist_hand_crop(
            frame_shape=(480, 640, 3),
            wrist_xy=(320.0, 240.0),
            crop_size=256,
            side="left",
            confidence=0.9,
            confidence_threshold=0.3,
        )

        self.assertIsNotNone(crop)
        self.assertEqual(crop.crop_box, (192, 112, 448, 368))
        self.assertEqual(crop.crop_width, 256)
        self.assertEqual(crop.crop_height, 256)
        self.assertEqual(crop.side, "left")
        self.assertEqual(crop.image_width, 640)
        self.assertEqual(crop.image_height, 480)

    def test_low_confidence_skips_crop(self):
        crop = build_wrist_hand_crop(
            frame_shape=(480, 640, 3),
            wrist_xy=(320.0, 240.0),
            crop_size=256,
            side="right",
            confidence=0.1,
            confidence_threshold=0.3,
        )

        self.assertIsNone(crop)

    def test_crop_is_clamped_to_frame_bounds(self):
        crop = build_wrist_hand_crop(
            frame_shape=(100, 120, 3),
            wrist_xy=(10.0, 8.0),
            crop_size=64,
            side="left",
            confidence=1.0,
        )

        self.assertIsNotNone(crop)
        self.assertEqual(crop.crop_box, (0, 0, 42, 40))
        self.assertEqual(crop.crop_width, 42)
        self.assertEqual(crop.crop_height, 40)

    def test_crop_frame_slices_numpy_like_frame(self):
        frame = [[(x, y) for x in range(10)] for y in range(8)]
        crop = build_wrist_hand_crop(
            frame_shape=(8, 10, 3),
            wrist_xy=(5.0, 4.0),
            crop_size=4,
            side="right",
            confidence=1.0,
        )

        cropped = crop_frame(frame, crop)

        self.assertEqual(len(cropped), 4)
        self.assertEqual(len(cropped[0]), 4)
        self.assertEqual(cropped[0][0], (3, 2))

    def test_landmarks_map_from_crop_normalized_to_frame_pixels(self):
        crop = build_wrist_hand_crop(
            frame_shape=(480, 640, 3),
            wrist_xy=(320.0, 240.0),
            crop_size=200,
            side="left",
            confidence=1.0,
        )
        landmarks = SimpleNamespace(
            landmark=[
                SimpleNamespace(x=0.0, y=0.0, z=0.1),
                SimpleNamespace(x=0.5, y=0.25, z=-0.2),
            ],
        )

        mapped = map_crop_landmarks_to_frame(landmarks, crop)

        self.assertEqual(mapped[0], [220.0, 140.0, 0.1])
        self.assertEqual(mapped[1], [320.0, 190.0, -0.2])


if __name__ == "__main__":
    unittest.main()
