import unittest

from pose_feedback.body.yolo26_runner import YOLO26PoseRunner


def make_keypoints():
    keypoints = [[0.0, 0.0, 0.0] for _ in range(17)]
    keypoints[5] = [100.0, 200.0, 0.95]
    keypoints[6] = [400.0, 200.0, 0.96]
    keypoints[7] = [120.0, 260.0, 0.85]
    keypoints[8] = [380.0, 260.0, 0.86]
    keypoints[9] = [140.0, 320.0, 0.25]
    keypoints[10] = [360.0, 320.0, 0.88]
    return keypoints


class FakeYOLO26PoseRunner(YOLO26PoseRunner):
    def __init__(self, keypoints):
        super().__init__()
        self.keypoints = keypoints

    def predict_keypoints(self, image):
        return self.keypoints


class YOLO26PoseRunnerTest(unittest.TestCase):
    def test_predict_body_returns_named_body_dict(self):
        runner = FakeYOLO26PoseRunner(make_keypoints())

        body = runner.predict_body(image=object())

        self.assertEqual(tuple(body["left"]["shoulder_px"]), (100.0, 200.0))
        self.assertEqual(tuple(body["left"]["elbow_px"]), (120.0, 260.0))
        self.assertEqual(tuple(body["left"]["wrist_px"]), (140.0, 320.0))
        self.assertEqual(tuple(body["right"]["shoulder_px"]), (400.0, 200.0))
        self.assertEqual(tuple(body["right"]["elbow_px"]), (380.0, 260.0))
        self.assertEqual(tuple(body["right"]["wrist_px"]), (360.0, 320.0))

    def test_predict_body_computes_shoulder_width(self):
        runner = FakeYOLO26PoseRunner(make_keypoints())

        body = runner.predict_body(image=object())

        self.assertEqual(body["shoulder_width_px"], 300.0)

    def test_predict_body_propagates_low_confidence_wrist(self):
        runner = FakeYOLO26PoseRunner(make_keypoints())

        body = runner.predict_body(image=object())

        self.assertEqual(body["left"]["wrist_conf"], 0.25)

    def test_invalid_keypoint_shape_raises_value_error(self):
        runner = FakeYOLO26PoseRunner([[0.0, 0.0, 1.0]] * 16)

        with self.assertRaises(ValueError):
            runner.predict_body(image=object())


if __name__ == "__main__":
    unittest.main()
