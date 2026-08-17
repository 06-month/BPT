import unittest

from pose_feedback.body.body_adapter import coco_yolo_keypoints_to_body


def make_keypoints(dims=3):
    rows = []
    for index in range(17):
        if dims == 2:
            rows.append([float(index), float(index + 100)])
        else:
            rows.append([float(index), float(index + 100), 0.9])
    rows[5] = [10.0, 20.0] if dims == 2 else [10.0, 20.0, 0.91]
    rows[6] = [40.0, 60.0] if dims == 2 else [40.0, 60.0, 0.92]
    rows[7] = [11.0, 21.0] if dims == 2 else [11.0, 21.0, 0.71]
    rows[8] = [41.0, 61.0] if dims == 2 else [41.0, 61.0, 0.72]
    rows[9] = [12.0, 22.0] if dims == 2 else [12.0, 22.0, 0.81]
    rows[10] = [42.0, 62.0] if dims == 2 else [42.0, 62.0, 0.82]
    return rows


class BodyAdapterTest(unittest.TestCase):
    def test_correct_left_right_mapping(self):
        body = coco_yolo_keypoints_to_body(make_keypoints())

        self.assertEqual(tuple(body["left"]["shoulder_px"]), (10.0, 20.0))
        self.assertEqual(tuple(body["left"]["elbow_px"]), (11.0, 21.0))
        self.assertEqual(tuple(body["left"]["wrist_px"]), (12.0, 22.0))
        self.assertEqual(tuple(body["right"]["shoulder_px"]), (40.0, 60.0))
        self.assertEqual(tuple(body["right"]["elbow_px"]), (41.0, 61.0))
        self.assertEqual(tuple(body["right"]["wrist_px"]), (42.0, 62.0))
        self.assertEqual(body["left"]["shoulder_conf"], 0.91)
        self.assertEqual(body["right"]["wrist_conf"], 0.82)

    def test_shoulder_width_px_calculation(self):
        body = coco_yolo_keypoints_to_body(make_keypoints())

        self.assertEqual(body["shoulder_width_px"], 50.0)

    def test_xy_input_defaults_confidence_to_one(self):
        body = coco_yolo_keypoints_to_body(make_keypoints(dims=2))

        self.assertEqual(body["left"]["shoulder_conf"], 1.0)
        self.assertEqual(body["left"]["elbow_conf"], 1.0)
        self.assertEqual(body["left"]["wrist_conf"], 1.0)
        self.assertEqual(body["right"]["shoulder_conf"], 1.0)
        self.assertEqual(body["right"]["elbow_conf"], 1.0)
        self.assertEqual(body["right"]["wrist_conf"], 1.0)

    def test_low_confidence_shoulder_width_is_none(self):
        keypoints = make_keypoints()
        keypoints[5][2] = 0.49

        body = coco_yolo_keypoints_to_body(keypoints)

        self.assertIsNone(body["shoulder_width_px"])

    def test_invalid_input_shape_raises_value_error(self):
        with self.assertRaises(ValueError):
            coco_yolo_keypoints_to_body([[0.0, 0.0, 1.0]] * 16)
        with self.assertRaises(ValueError):
            coco_yolo_keypoints_to_body([[0.0, 0.0, 1.0, 2.0]] * 17)
        with self.assertRaises(ValueError):
            coco_yolo_keypoints_to_body([0.0] * 17)


if __name__ == "__main__":
    unittest.main()
