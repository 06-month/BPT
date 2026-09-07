import unittest

import numpy as np

from pose_feedback.body.uplift_upsample_adapter import (
    coco17_to_uplift_h36m17,
    denormalize_uplift_2d,
    make_stride_mask,
    normalize_uplift_2d,
)


class UpliftUpsampleAdapterTests(unittest.TestCase):
    def test_output_shape(self):
        converted, conf = coco17_to_uplift_h36m17(sample_coco())
        self.assertEqual(converted.shape, (17, 2))
        self.assertEqual(conf.shape, (17,))

    def test_pelvis_average(self):
        coco = sample_coco()
        coco[11, :2] = [10.0, 20.0]
        coco[12, :2] = [30.0, 40.0]
        converted, _ = coco17_to_uplift_h36m17(coco)
        np.testing.assert_allclose(converted[6], [20.0, 30.0])

    def test_confidence_propagation(self):
        coco = sample_coco()
        coco[11, 2] = 0.8
        coco[12, 2] = 0.4
        _, conf = coco17_to_uplift_h36m17(coco)
        self.assertAlmostEqual(float(conf[6]), 0.6, places=5)

    def test_low_confidence_synthetic_joint_falls_back_dense(self):
        coco = sample_coco()
        coco[11, 2] = 0.1
        coco[12, 2] = 0.2
        converted, conf = coco17_to_uplift_h36m17(coco)
        self.assertEqual(converted.shape, (17, 2))
        self.assertLess(float(conf[6]), 0.3)

    def test_normalization_round_trip(self):
        points = np.array([[0.0, 0.0], [640.0, 360.0], [320.0, 180.0]], dtype="float32")
        norm = normalize_uplift_2d(points, image_width=640, image_height=360)
        restored = denormalize_uplift_2d(norm, image_width=640, image_height=360)
        np.testing.assert_allclose(restored, points, atol=1e-5)

    def test_normalization_matches_video_pose_3d_formula(self):
        norm = normalize_uplift_2d(np.array([[0.0, 0.0]], dtype="float32"), 640, 360)
        np.testing.assert_allclose(norm[0], [-1.0, -0.5625], atol=1e-6)

    def test_stride_mask_centered(self):
        mask = make_stride_mask(7, 3)
        self.assertEqual(mask.tolist(), [True, False, False, True, False, False, True])


def sample_coco():
    rows = np.zeros((17, 3), dtype="float32")
    for idx in range(17):
        rows[idx] = [idx * 10.0, idx * 10.0 + 5.0, 1.0]
    return rows


if __name__ == "__main__":
    unittest.main()
