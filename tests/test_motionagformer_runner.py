import unittest

import numpy as np

from pose_feedback.body.motionagformer_runner import MotionAGFormerRunner


class FakeModel:
    def predict(self, batch):
        arr = np.asarray(batch, dtype="float32")
        out = np.zeros(arr.shape[:-1] + (3,), dtype="float32")
        out[..., :2] = arr[..., :2]
        return out


class MotionAGFormerRunnerTests(unittest.TestCase):
    def test_fake_model_predicts_shape(self):
        runner = MotionAGFormerRunner(model=FakeModel(), window_size=9)
        pred = runner.predict_3d(np.zeros((9, 17, 3), dtype="float32"))
        self.assertEqual(pred.shape, (9, 17, 3))

    def test_invalid_shape_raises(self):
        runner = MotionAGFormerRunner(model=FakeModel(), window_size=9)
        with self.assertRaises(ValueError):
            runner.predict_3d(np.zeros((8, 17, 3), dtype="float32"))

    def test_missing_repo_raises_clear_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            MotionAGFormerRunner(repo_dir="does/not/exist", checkpoint_path="missing.pth")


if __name__ == "__main__":
    unittest.main()
