import unittest

import numpy as np

from pose_feedback.body.motionagformer_buffer import MotionAGFormerWindowBuilder


class MotionAGFormerWindowBuilderTests(unittest.TestCase):
    def test_full_window_shape_and_center(self):
        seq = np.arange(300, dtype="float32")[:, None]
        builder = MotionAGFormerWindowBuilder(window_size=243)
        window, indices = builder.build_full_centered(seq, 150)
        self.assertEqual(window.shape, (243, 1))
        self.assertEqual(indices[121], 150)

    def test_lookahead3_shape_and_current_position(self):
        seq = np.arange(300, dtype="float32")[:, None]
        builder = MotionAGFormerWindowBuilder(window_size=243)
        window, indices = builder.build_lookahead_padded(seq, 100, lookahead=3)
        self.assertEqual(window.shape, (243, 1))
        self.assertEqual(indices[-4], 100)
        self.assertEqual(indices[-1], 103)

    def test_lookahead5_shape(self):
        seq = np.arange(300, dtype="float32")[:, None]
        builder = MotionAGFormerWindowBuilder(window_size=243)
        window, indices = builder.build_lookahead_padded(seq, 100, lookahead=5)
        self.assertEqual(window.shape, (243, 1))
        self.assertEqual(indices[-1], 105)

    def test_beginning_padding(self):
        seq = np.arange(20, dtype="float32")[:, None]
        builder = MotionAGFormerWindowBuilder(window_size=9)
        _, indices = builder.build_lookahead_padded(seq, 0, lookahead=3)
        np.testing.assert_array_equal(indices[:5], np.zeros((5,), dtype=int))

    def test_end_padding_repeats_last_available_future(self):
        seq = np.arange(20, dtype="float32")[:, None]
        builder = MotionAGFormerWindowBuilder(window_size=9)
        _, indices = builder.build_lookahead_padded(seq, 18, lookahead=5)
        self.assertEqual(indices[-1], 19)
        self.assertEqual(indices[-2], 19)

    def test_latency_calculations(self):
        builder = MotionAGFormerWindowBuilder(window_size=243)
        self.assertEqual(builder.latency_frames("full"), 121)
        self.assertAlmostEqual(builder.latency_seconds(30, "full"), 4.033333333333333)
        self.assertEqual(builder.latency_frames("lookahead", lookahead=3), 3)
        self.assertAlmostEqual(builder.latency_seconds(30, "lookahead", lookahead=3), 0.1)
        self.assertEqual(builder.latency_frames("lookahead", lookahead=5), 5)
        self.assertAlmostEqual(builder.latency_seconds(30, "lookahead", lookahead=5), 0.16666666666666666)


if __name__ == "__main__":
    unittest.main()
