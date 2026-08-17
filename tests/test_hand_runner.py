from dataclasses import dataclass
import unittest

from pose_feedback.hand.hand_runner import (
    HandRunner,
    mp_wrist_crop_to_image_coords,
    mp_wrist_to_image_coords,
)


@dataclass
class FakeLandmark:
    x: float
    y: float


class FakeHandLandmarks:
    def __init__(self, wrist_x, wrist_y):
        self.landmark = [FakeLandmark(0.0, 0.0) for _ in range(21)]
        self.landmark[0] = FakeLandmark(wrist_x, wrist_y)


class HandRunnerTest(unittest.TestCase):
    def test_fullframe_wrist_restoration(self):
        hand_landmarks = FakeHandLandmarks(0.5, 0.25)

        wrist_px = mp_wrist_to_image_coords(hand_landmarks, image_w=200, image_h=100)

        self.assertEqual(tuple(wrist_px), (100.0, 25.0))

    def test_crop_wrist_restoration(self):
        hand_landmarks = FakeHandLandmarks(0.5, 0.25)

        wrist_px = mp_wrist_crop_to_image_coords(
            hand_landmarks,
            crop_box=(100, 50, 300, 250),
        )

        self.assertEqual(tuple(wrist_px), (200.0, 100.0))

    def test_crop_mode_is_accepted(self):
        runner = HandRunner(mode="crop")

        self.assertEqual(runner.mode, "crop")

    def test_fullframe_mode_is_accepted(self):
        runner = HandRunner(mode="fullframe")

        self.assertEqual(runner.mode, "fullframe")

    def test_invalid_mode_raises_value_error(self):
        with self.assertRaises(ValueError):
            HandRunner(mode="invalid")

    def test_default_run_fullframe_raises_not_implemented(self):
        runner = HandRunner(mode="fullframe")

        with self.assertRaises(NotImplementedError):
            runner.run_fullframe(image=object())

    def test_default_run_crop_raises_not_implemented(self):
        runner = HandRunner(mode="crop")

        with self.assertRaises(NotImplementedError):
            runner.run_crop(image=object(), crop_box=(0, 0, 10, 10))


if __name__ == "__main__":
    unittest.main()
