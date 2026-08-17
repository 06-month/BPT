import tempfile
import unittest
from pathlib import Path

import numpy as np

from pose_feedback.body.coreml_motionagformer import CoreMLMotionAGFormerRunner
from scripts.visualize_rtmpose_body_and_both_hands_video import (
    run_coreml_motionagformer_sequence,
)


class FakeCoreMLModel:
    def __init__(self):
        self.inputs = []

    def predict(self, inputs):
        value = np.asarray(inputs["input_2d_sequence"], dtype="float32")
        self.inputs.append(value.copy())
        return {"pred_3d_sequence": value + 1.0}


class CoreMLMotionAGFormerTests(unittest.TestCase):
    def test_missing_model_fails_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.mlpackage"
            with self.assertRaises(FileNotFoundError):
                CoreMLMotionAGFormerRunner(model_path=missing)

    def test_predict_3d_uses_coreml_input_name_and_output(self):
        fake = FakeCoreMLModel()
        runner = CoreMLMotionAGFormerRunner(model=fake)
        window = np.zeros((27, 17, 3), dtype="float32")
        window[-1, 13] = [1.0, 2.0, 0.5]

        pred = runner.predict_3d(window)

        self.assertEqual(pred.shape, (27, 17, 3))
        self.assertEqual(len(fake.inputs), 1)
        self.assertEqual(fake.inputs[0].shape, (1, 27, 17, 3))
        np.testing.assert_allclose(fake.inputs[0][0, -1, 13], [1.0, 2.0, 0.5])
        np.testing.assert_allclose(pred[-1, 13], [2.0, 3.0, 1.5])

    def test_coreml_sequence_receives_motionagformer_input_copy(self):
        raw = synthetic_coco()
        modified = raw.copy()
        modified[9, :2] = [320.0, 240.0]
        fake = FakeCoreMLModel()
        runner = CoreMLMotionAGFormerRunner(model=fake)

        selected, timings = run_coreml_motionagformer_sequence(
            [modified],
            runner=runner,
            image_width=640,
            image_height=480,
            lookahead=0,
            window_size=27,
        )

        self.assertEqual(selected.shape, (1, 17, 3))
        self.assertEqual(len(timings), 1)
        self.assertEqual(len(fake.inputs), 1)
        # COCO left wrist index 9 maps to MotionAGFormer/H36M left wrist index 13.
        self.assertNotEqual(float(fake.inputs[0][0, -1, 13, 0]), float(raw[9, 0]))


def synthetic_coco():
    coco = np.zeros((17, 3), dtype="float32")
    for idx in range(17):
        coco[idx] = [idx * 10.0, idx * 10.0 + 1.0, 0.5 + idx * 0.01]
    return coco


if __name__ == "__main__":
    unittest.main()
