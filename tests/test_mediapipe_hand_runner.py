from dataclasses import dataclass
import builtins
import importlib
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pose_feedback.hand.mediapipe_hand_runner import (
    MediaPipeHandsRunner,
    MediaPipeHandsRuntimeError,
)


@dataclass
class FakeLandmark:
    x: float
    y: float
    z: float = 0.0


class FakeHandLandmarks:
    def __init__(self, wrist_x, wrist_y):
        self.landmark = [FakeLandmark(0.0, 0.0) for _ in range(21)]
        self.landmark[0] = FakeLandmark(wrist_x, wrist_y)


class FakeClassification:
    def __init__(self, label):
        self.label = label


class FakeHandedness:
    def __init__(self, label):
        self.classification = [FakeClassification(label)]


class FakeResults:
    def __init__(self, hand_landmarks=None, hand_world_landmarks=None, handedness=None):
        self.multi_hand_landmarks = hand_landmarks
        self.multi_hand_world_landmarks = hand_world_landmarks
        self.multi_handedness = handedness


class FakeHands:
    def __init__(self, results):
        self.results = results
        self.processed_crop = None
        self.closed = False

    def process(self, image):
        self.processed_crop = image
        return self.results

    def close(self):
        self.closed = True


class MediaPipeHandsRunnerTest(unittest.TestCase):
    def test_module_import_does_not_import_mediapipe(self):
        module = sys.modules["pose_feedback.hand.mediapipe_hand_runner"]
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "mediapipe":
                raise AssertionError("mediapipe should not be imported at module import time")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded_import):
            importlib.reload(module)

    def test_run_crop_returns_normalized_hand_result(self):
        hand_landmarks = FakeHandLandmarks(0.5, 0.25)
        hand_world_landmarks = object()
        fake_hands = FakeHands(
            FakeResults(
                hand_landmarks=[hand_landmarks],
                hand_world_landmarks=[hand_world_landmarks],
                handedness=[FakeHandedness("Right")],
            ),
        )
        runner = MediaPipeHandsRunner(hands=fake_hands)
        image = [[(x, y) for x in range(400)] for y in range(300)]

        results = runner.run_crop(image, crop_box=(100, 50, 300, 250))

        self.assertEqual(len(results), 1)
        self.assertIs(results[0]["hand_landmarks"], hand_landmarks)
        self.assertIs(results[0]["hand_world_landmarks"], hand_world_landmarks)
        self.assertEqual(results[0]["handedness"], "Right")
        self.assertEqual(tuple(results[0]["wrist_px"]), (200.0, 100.0))
        self.assertEqual(results[0]["crop_box"], (100, 50, 300, 250))
        self.assertEqual(len(fake_hands.processed_crop), 200)
        self.assertEqual(len(fake_hands.processed_crop[0]), 200)

    def test_run_crop_returns_empty_list_when_no_hand_detected(self):
        runner = MediaPipeHandsRunner(hands=FakeHands(FakeResults()))

        results = runner.run_crop(image=[[0] * 10 for _ in range(10)], crop_box=(0, 0, 5, 5))

        self.assertEqual(results, [])

    def test_invalid_handedness_label_is_normalized_to_none(self):
        hand_landmarks = FakeHandLandmarks(0.0, 0.0)
        runner = MediaPipeHandsRunner(
            hands=FakeHands(
                FakeResults(
                    hand_landmarks=[hand_landmarks],
                    handedness=[FakeHandedness("Unknown")],
                ),
            ),
        )

        results = runner.run_crop(image=[[0] * 10 for _ in range(10)], crop_box=(0, 0, 5, 5))

        self.assertIsNone(results[0]["handedness"])

    def test_close_delegates_to_injected_hands(self):
        fake_hands = FakeHands(FakeResults())
        runner = MediaPipeHandsRunner(hands=fake_hands)

        runner.close()

        self.assertTrue(fake_hands.closed)

    def test_constructor_passes_static_image_mode_to_mediapipe(self):
        calls = []

        class FakeHandsFactory:
            def __init__(self, **kwargs):
                calls.append(kwargs)

        fake_mediapipe = SimpleNamespace(
            solutions=SimpleNamespace(
                hands=SimpleNamespace(Hands=FakeHandsFactory),
            ),
        )

        with patch.dict(sys.modules, {"mediapipe": fake_mediapipe}):
            MediaPipeHandsRunner(
                static_image_mode=True,
                max_num_hands=1,
                min_detection_confidence=0.3,
                min_tracking_confidence=0.3,
            )

        self.assertEqual(
            calls,
            [
                {
                    "static_image_mode": True,
                    "max_num_hands": 1,
                    "min_detection_confidence": 0.3,
                    "min_tracking_confidence": 0.3,
                },
            ],
        )

    def test_legacy_construction_failure_has_clear_message(self):
        class FailingHandsFactory:
            def __init__(self, **kwargs):
                raise RuntimeError("raw graph failure")

        fake_mediapipe = SimpleNamespace(
            solutions=SimpleNamespace(
                hands=SimpleNamespace(Hands=FailingHandsFactory),
            ),
        )

        with patch.dict(sys.modules, {"mediapipe": fake_mediapipe}):
            with self.assertRaises(MediaPipeHandsRuntimeError) as context:
                MediaPipeHandsRunner(static_image_mode=True)

        message = str(context.exception)
        self.assertIn("Legacy mp.solutions.hands.Hands failed", message)
        self.assertIn("macOS/GL", message)
        self.assertIn("MediaPipe Tasks HandLandmarker", message)
        self.assertIsInstance(context.exception.__cause__, RuntimeError)


if __name__ == "__main__":
    unittest.main()
