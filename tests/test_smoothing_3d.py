import unittest

import numpy as np

from pose_feedback.geometry.smoothing_3d import EMA3DSmoother


class Smoothing3DTests(unittest.TestCase):
    def test_first_value_passthrough(self):
        smoother = EMA3DSmoother(alpha=0.5)
        value = np.ones((2, 3), dtype="float32")
        np.testing.assert_allclose(smoother.update(value), value)

    def test_ema_update(self):
        smoother = EMA3DSmoother(alpha=0.25)
        smoother.update(np.zeros((1, 3), dtype="float32"))
        out = smoother.update(np.ones((1, 3), dtype="float32") * 4)
        np.testing.assert_allclose(out, np.ones((1, 3), dtype="float32"))

    def test_reset(self):
        smoother = EMA3DSmoother(alpha=0.5)
        smoother.update(np.zeros((1, 3), dtype="float32"))
        smoother.reset()
        np.testing.assert_allclose(smoother.update(np.ones((1, 3), dtype="float32") * 3), [[3, 3, 3]])


if __name__ == "__main__":
    unittest.main()
