import unittest

import numpy as np

from pose_feedback.body.live_motionagformer import (
    motionagformer_body_3d_debug,
    run_live_motionagformer_sequence,
)


class FakeRunner:
    def __init__(self):
        self.windows = []

    def predict_3d(self, window):
        self.windows.append(np.asarray(window, dtype="float32").copy())
        out = np.zeros((window.shape[0], 17, 3), dtype="float32")
        out[:, :, :2] = window[:, :, :2]
        out[:, :, 2] = window[:, :, 2]
        return out


class LiveMotionAGFormerTests(unittest.TestCase):
    def test_runner_receives_selected_motionagformer_input_sequence(self):
        raw = synthetic_coco()
        modified = raw.copy()
        modified[9, :2] = [320.0, 240.0]
        runner = FakeRunner()

        selected, windows, indices, normalized = run_live_motionagformer_sequence(
            [modified],
            runner=runner,
            image_width=640,
            image_height=480,
            lookahead=0,
            window_size=27,
        )

        self.assertEqual(selected.shape, (1, 17, 3))
        self.assertEqual(windows.shape, (1, 27, 17, 3))
        self.assertEqual(indices.shape, (1, 27))
        self.assertEqual(len(runner.windows), 1)
        expected_left_wrist = normalized[0, 13]
        np.testing.assert_allclose(runner.windows[0][-1, 13], expected_left_wrist)

    def test_body_3d_debug_reports_wrist_elbow_lengths(self):
        joints = np.zeros((17, 3), dtype="float32")
        joints[12] = [1.0, 0.0, 0.0]
        joints[13] = [4.0, 0.0, 0.0]
        joints[15] = [0.0, 2.0, 0.0]
        joints[16] = [0.0, 6.0, 0.0]

        debug = motionagformer_body_3d_debug(joints)

        self.assertEqual(debug["left"]["wrist_3d"], [4.0, 0.0, 0.0])
        self.assertAlmostEqual(debug["left"]["elbow_wrist_length_3d"], 3.0)
        self.assertEqual(debug["right"]["wrist_3d"], [0.0, 6.0, 0.0])
        self.assertAlmostEqual(debug["right"]["elbow_wrist_length_3d"], 4.0)


def synthetic_coco():
    coco = np.zeros((17, 3), dtype="float32")
    for idx in range(17):
        coco[idx] = [idx * 10.0, idx * 10.0 + 1.0, 0.5 + idx * 0.01]
    return coco


if __name__ == "__main__":
    unittest.main()
