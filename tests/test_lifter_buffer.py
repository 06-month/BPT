import unittest

from pose_feedback.body.lifter_buffer import SlidingWindowLifterBuffer


class SlidingWindowLifterBufferTests(unittest.TestCase):
    def test_readiness(self):
        buf = SlidingWindowLifterBuffer(window_size=3)
        buf.push("a")
        buf.push("b")
        self.assertFalse(buf.ready())
        buf.push("c")
        self.assertTrue(buf.ready())

    def test_window_contents(self):
        buf = SlidingWindowLifterBuffer(window_size=3)
        for item in [1, 2, 3, 4]:
            buf.push(item)
        self.assertEqual(buf.get_window(), [2, 3, 4])

    def test_latency_calculation(self):
        centered = SlidingWindowLifterBuffer(window_size=5, centered=True)
        causal = SlidingWindowLifterBuffer(window_size=5, centered=False)
        self.assertEqual(centered.latency_frames, 2)
        self.assertEqual(causal.latency_frames, 4)
        self.assertAlmostEqual(centered.latency_seconds(30), 2 / 30)

    def test_reset(self):
        buf = SlidingWindowLifterBuffer(window_size=2)
        buf.push(1)
        buf.push(2)
        self.assertTrue(buf.ready())
        buf.reset()
        self.assertFalse(buf.ready())


if __name__ == "__main__":
    unittest.main()
