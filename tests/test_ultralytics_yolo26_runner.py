import unittest

from pose_feedback.body.yolo26_runner import (
    NoPersonDetectedError,
    UltralyticsYOLO26PoseRunner,
)


def person(base_x, confidence):
    rows = []
    for index in range(17):
        rows.append([base_x + index, 100.0 + index, confidence])
    rows[5] = [base_x + 50.0, 200.0, confidence]
    rows[6] = [base_x + 350.0, 200.0, confidence]
    rows[9] = [base_x + 90.0, 300.0, confidence]
    return rows


class FakeKeypoints:
    def __init__(self, data=None, xy=None, conf=None):
        self.data = data
        self.xy = xy
        self.conf = conf


class FakeResult:
    def __init__(self, keypoints):
        self.keypoints = keypoints


class FakeModel:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def predict(self, image, conf, verbose):
        self.calls.append({"image": image, "conf": conf, "verbose": verbose})
        return [self.result]


class UltralyticsYOLO26PoseRunnerTest(unittest.TestCase):
    def test_predict_keypoints_returns_coco_shape(self):
        model = FakeModel(FakeResult(FakeKeypoints(data=[person(0.0, 0.9)])))
        runner = UltralyticsYOLO26PoseRunner(
            model_path="fake.pt",
            confidence=0.33,
            model=model,
        )

        keypoints = runner.predict_keypoints(image="frame")

        self.assertEqual(keypoints.shape, (17, 3))
        self.assertEqual(tuple(keypoints[5][:2]), (50.0, 200.0))
        self.assertAlmostEqual(float(keypoints[5][2]), 0.9)
        self.assertEqual(model.calls, [{"image": "frame", "conf": 0.33, "verbose": False}])

    def test_predict_keypoints_selects_best_person_by_confidence(self):
        model = FakeModel(
            FakeResult(
                FakeKeypoints(
                    data=[
                        person(0.0, 0.2),
                        person(1000.0, 0.9),
                    ],
                ),
            ),
        )
        runner = UltralyticsYOLO26PoseRunner(model_path="fake.pt", model=model)

        keypoints = runner.predict_keypoints(image="frame")

        self.assertEqual(tuple(keypoints[5][:2]), (1050.0, 200.0))
        self.assertAlmostEqual(float(keypoints[5][2]), 0.9)

    def test_predict_body_uses_adapter_path(self):
        model = FakeModel(FakeResult(FakeKeypoints(data=[person(0.0, 0.9)])))
        runner = UltralyticsYOLO26PoseRunner(model_path="fake.pt", model=model)

        body = runner.predict_body(image="frame")

        self.assertEqual(tuple(body["left"]["shoulder_px"]), (50.0, 200.0))
        self.assertEqual(tuple(body["left"]["wrist_px"]), (90.0, 300.0))
        self.assertEqual(body["shoulder_width_px"], 300.0)

    def test_no_person_detected_raises_custom_error(self):
        model = FakeModel(FakeResult(FakeKeypoints(data=[])))
        runner = UltralyticsYOLO26PoseRunner(model_path="fake.pt", model=model)

        with self.assertRaises(NoPersonDetectedError):
            runner.predict_keypoints(image="frame")

    def test_invalid_detected_keypoint_count_raises_value_error(self):
        model = FakeModel(FakeResult(FakeKeypoints(data=[person(0.0, 0.9)[:16]])))
        runner = UltralyticsYOLO26PoseRunner(model_path="fake.pt", model=model)

        with self.assertRaises(ValueError):
            runner.predict_keypoints(image="frame")


if __name__ == "__main__":
    unittest.main()
