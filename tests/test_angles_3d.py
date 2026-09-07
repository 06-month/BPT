import unittest

from pose_feedback.geometry.angles_3d import angle_3d, elbow_flexion_3d, knee_flexion_3d


class Angles3DTests(unittest.TestCase):
    def test_180_degree_line(self):
        self.assertAlmostEqual(angle_3d([-1, 0, 0], [0, 0, 0], [1, 0, 0]), 180.0)

    def test_90_degree_angle(self):
        self.assertAlmostEqual(angle_3d([1, 0, 0], [0, 0, 0], [0, 1, 0]), 90.0)

    def test_zero_vector_behavior(self):
        self.assertIsNone(angle_3d([0, 0, 0], [0, 0, 0], [1, 0, 0]))

    def test_named_helpers(self):
        self.assertAlmostEqual(elbow_flexion_3d([-1, 0, 0], [0, 0, 0], [1, 0, 0]), 180.0)
        self.assertAlmostEqual(knee_flexion_3d([1, 0, 0], [0, 0, 0], [0, 1, 0]), 90.0)


if __name__ == "__main__":
    unittest.main()
