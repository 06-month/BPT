from types import SimpleNamespace
import unittest

from pose_feedback.hand.mediapipe_hand_landmarker_runner import (
    MediaPipeHandLandmarkerRunner,
)
from scripts import visualize_rtmpose_body_and_both_hands_video as video_script


class FakeLandmarker:
    def __init__(self, result):
        self.result = result
        self.detected_image = None
        self.video_calls = []
        self.closed = False

    def detect(self, image):
        self.detected_image = image
        return self.result

    def detect_for_video(self, image, timestamp_ms):
        self.video_calls.append((image, timestamp_ms))
        return self.result

    def close(self):
        self.closed = True


class MediaPipeHandLandmarkerRunnerTest(unittest.TestCase):
    def test_run_crop_normalizes_tasks_result(self):
        landmarks = [
            SimpleNamespace(x=0.5, y=0.25, z=0.0),
            *[SimpleNamespace(x=0.0, y=0.0, z=0.0) for _ in range(20)],
        ]
        result = SimpleNamespace(
            hand_landmarks=[landmarks],
            hand_world_landmarks=[landmarks],
            handedness=[[SimpleNamespace(category_name="Left")]],
        )
        fake_landmarker = FakeLandmarker(result)
        runner = MediaPipeHandLandmarkerRunner(
            task_model_path="unused.task",
            input_color_format="RGB",
            running_mode="image",
            landmarker=fake_landmarker,
        )

        output = runner.run_crop(
            image=[[(x, y) for x in range(400)] for y in range(300)],
            crop_box=(100, 50, 300, 250),
        )

        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]["handedness"], "Left")
        self.assertEqual(tuple(output[0]["wrist_px"]), (200.0, 100.0))
        self.assertEqual(output[0]["crop_box"], (100, 50, 300, 250))
        self.assertIsNotNone(fake_landmarker.detected_image)
        self.assertEqual(fake_landmarker.video_calls, [])

    def test_video_mode_calls_detect_for_video_with_timestamp(self):
        landmarks = [
            SimpleNamespace(x=0.25, y=0.5, z=0.0),
            *[SimpleNamespace(x=0.0, y=0.0, z=0.0) for _ in range(20)],
        ]
        result = SimpleNamespace(
            hand_landmarks=[landmarks],
            hand_world_landmarks=[landmarks],
            handedness=[[SimpleNamespace(category_name="Right")]],
        )
        fake_landmarker = FakeLandmarker(result)
        runner = MediaPipeHandLandmarkerRunner(
            task_model_path="unused.task",
            input_color_format="RGB",
            running_mode="video",
            landmarker=fake_landmarker,
        )

        output = runner.run_crop(
            image=[[(x, y) for x in range(400)] for y in range(300)],
            crop_box=(100, 50, 300, 250),
            timestamp_ms=1234,
        )

        self.assertEqual(len(output), 1)
        self.assertEqual(output[0]["handedness"], "Right")
        self.assertEqual(len(fake_landmarker.video_calls), 1)
        self.assertEqual(fake_landmarker.video_calls[0][1], 1234)
        self.assertIsNone(fake_landmarker.detected_image)

    def test_video_mode_rejects_non_increasing_timestamps(self):
        fake_landmarker = FakeLandmarker(SimpleNamespace())
        runner = MediaPipeHandLandmarkerRunner(
            task_model_path="unused.task",
            input_color_format="RGB",
            running_mode="video",
            landmarker=fake_landmarker,
        )

        runner.run_crop(
            image=[[(x, y) for x in range(20)] for y in range(20)],
            crop_box=(0, 0, 10, 10),
            timestamp_ms=100,
        )

        with self.assertRaises(ValueError):
            runner.run_crop(
                image=[[(x, y) for x in range(20)] for y in range(20)],
                crop_box=(0, 0, 10, 10),
                timestamp_ms=100,
            )

    def test_video_mode_requires_timestamp(self):
        runner = MediaPipeHandLandmarkerRunner(
            task_model_path="unused.task",
            input_color_format="RGB",
            running_mode="video",
            landmarker=FakeLandmarker(SimpleNamespace()),
        )

        with self.assertRaises(ValueError):
            runner.run_crop(
                image=[[(x, y) for x in range(20)] for y in range(20)],
                crop_box=(0, 0, 10, 10),
            )

    def test_close_delegates_to_landmarker(self):
        runner = MediaPipeHandLandmarkerRunner(
            task_model_path="unused.task",
            landmarker=FakeLandmarker(SimpleNamespace()),
        )

        runner.close()

        self.assertTrue(runner.landmarker.closed)

    def test_video_script_creates_independent_tasks_runners_per_side(self):
        created = []

        class FakeRunner:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                created.append(self)

        original = video_script.MediaPipeHandLandmarkerRunner
        try:
            video_script.MediaPipeHandLandmarkerRunner = FakeRunner
            runners = video_script.create_tasks_hand_runners(
                task_model_path="unused.task",
                running_mode="video",
            )
        finally:
            video_script.MediaPipeHandLandmarkerRunner = original

        self.assertEqual(set(runners), {"left", "right"})
        self.assertIsNot(runners["left"], runners["right"])
        self.assertEqual(len(created), 2)
        self.assertEqual(created[0].kwargs["running_mode"], "video")
        self.assertEqual(created[1].kwargs["running_mode"], "video")


if __name__ == "__main__":
    unittest.main()
