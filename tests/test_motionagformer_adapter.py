import unittest

import numpy as np

from pose_feedback.body.motionagformer_adapter import (
    coco17_to_motionagformer_h36m17,
    denormalize_motionagformer_2d,
    normalize_motionagformer_2d,
)


class MotionAGFormerAdapterTests(unittest.TestCase):
    def test_output_shape_and_pelvis_average(self):
        coco = synthetic_coco()
        h36m, conf = coco17_to_motionagformer_h36m17(coco)
        self.assertEqual(h36m.shape, (17, 2))
        self.assertEqual(conf.shape, (17,))
        expected = (coco[11, :2] + coco[12, :2]) * 0.5
        np.testing.assert_allclose(h36m[0], expected)

    def test_left_right_ordering_from_2d_estimator_eval_mapping(self):
        coco = synthetic_coco()
        h36m, _ = coco17_to_motionagformer_h36m17(coco)
        np.testing.assert_allclose(h36m[1], coco[12, :2])
        np.testing.assert_allclose(h36m[4], coco[11, :2])
        np.testing.assert_allclose(h36m[13], coco[9, :2])
        np.testing.assert_allclose(h36m[16], coco[10, :2])

    def test_deterministic_mapping_batch(self):
        coco = np.stack([synthetic_coco(), synthetic_coco() + 1.0], axis=0)
        h36m, conf = coco17_to_motionagformer_h36m17(coco)
        self.assertEqual(h36m.shape, (2, 17, 2))
        self.assertEqual(conf.shape, (2, 17))

    def test_normalization_round_trip(self):
        points = np.asarray([[[0.0, 0.0], [640.0, 360.0]]], dtype="float32")
        norm = normalize_motionagformer_2d(points, image_width=640, image_height=360)
        restored = denormalize_motionagformer_2d(norm, image_width=640, image_height=360)
        np.testing.assert_allclose(restored, points, atol=1e-5)


def synthetic_coco():
    coco = np.zeros((17, 3), dtype="float32")
    for idx in range(17):
        coco[idx] = [idx * 10.0, idx * 10.0 + 1.0, 0.5 + idx * 0.01]
    return coco


if __name__ == "__main__":
    unittest.main()
