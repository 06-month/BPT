import builtins
from dataclasses import dataclass
import unittest
from unittest.mock import patch

from pose_feedback.body.rtmpose_runner import (
    RTMPoseNoPersonDetectedError,
    RTMPoseRunner,
)


@dataclass
class FakePredInstances:
    keypoints: list
    keypoint_scores: list


@dataclass
class FakeSample:
    pred_instances: FakePredInstances


class FakeImage:
    shape = (480, 640, 3)


def fake_keypoints(count=17):
    keypoints = [[[float(index), float(index + 100)] for index in range(count)]]
    scores = [[0.9 for _ in range(count)]]
    keypoints[0][5] = [10.0, 20.0]
    keypoints[0][6] = [40.0, 20.0]
    keypoints[0][9] = [12.0, 22.0]
    return keypoints, scores


class RTMPoseRunnerTest(unittest.TestCase):
    def test_predict_keypoints_returns_17_by_3(self):
        keypoints, scores = fake_keypoints()

        def inference_fn(model, image, bboxes=None):
            return [FakeSample(FakePredInstances(keypoints, scores))]

        runner = RTMPoseRunner(
            pose_config="config.py",
            pose_checkpoint="checkpoint.pth",
            pose_model=object(),
            inference_fn=inference_fn,
        )

        result = runner.predict_keypoints(FakeImage())

        self.assertEqual(result.shape, (17, 3))
        self.assertEqual(tuple(result[5][:2]), (10.0, 20.0))
        self.assertAlmostEqual(float(result[5][2]), 0.9)

    def test_predict_body_uses_body_adapter_path(self):
        keypoints, scores = fake_keypoints()

        def inference_fn(model, image, bboxes=None):
            return [FakeSample(FakePredInstances(keypoints, scores))]

        runner = RTMPoseRunner(
            pose_config="config.py",
            pose_checkpoint="checkpoint.pth",
            pose_model=object(),
            inference_fn=inference_fn,
        )

        body = runner.predict_body(FakeImage())

        self.assertEqual(tuple(body["left"]["shoulder_px"]), (10.0, 20.0))
        self.assertEqual(tuple(body["left"]["wrist_px"]), (12.0, 22.0))
        self.assertEqual(body["shoulder_width_px"], 30.0)

    def test_invalid_keypoint_count_raises_value_error(self):
        keypoints, scores = fake_keypoints(count=16)

        def inference_fn(model, image, bboxes=None):
            return [FakeSample(FakePredInstances(keypoints, scores))]

        runner = RTMPoseRunner(
            pose_config="config.py",
            pose_checkpoint="checkpoint.pth",
            pose_model=object(),
            inference_fn=inference_fn,
        )

        with self.assertRaises(ValueError):
            runner.predict_keypoints(FakeImage())

    def test_no_person_raises_clear_error(self):
        runner = RTMPoseRunner(
            pose_config="config.py",
            pose_checkpoint="checkpoint.pth",
            pose_model=object(),
            inference_fn=lambda model, image, bboxes=None: [],
        )

        with self.assertRaises(RTMPoseNoPersonDetectedError):
            runner.predict_keypoints(FakeImage())

    def test_missing_dependency_raises_clear_import_error(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "mmpose.apis" or name.startswith("mmpose"):
                raise ModuleNotFoundError("No module named 'mmpose'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded_import):
            with self.assertRaises(ImportError) as context:
                RTMPoseRunner(
                    pose_config="config.py",
                    pose_checkpoint="checkpoint.pth",
                )

        self.assertIn("mmpose is required", str(context.exception))


if __name__ == "__main__":
    unittest.main()
