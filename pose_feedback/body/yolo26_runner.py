from pose_feedback.body.body_adapter import coco_yolo_keypoints_to_body

try:
    import numpy as np
except ModuleNotFoundError:
    np = None


class YOLO26PoseRunner:
    def __init__(self, model_path=None, model=None, min_confidence: float = 0.5):
        self.model_path = model_path
        self.model = model
        self.min_confidence = min_confidence

    def predict_keypoints(self, image):
        if self.model is None:
            raise NotImplementedError(
                "YOLO runtime is not connected yet; override predict_keypoints.",
            )
        raise NotImplementedError(
            "Real YOLO26 inference is intentionally not wired in this stub.",
        )

    def predict_body(self, image):
        keypoints = self.predict_keypoints(image)
        return coco_yolo_keypoints_to_body(
            keypoints,
            min_confidence=self.min_confidence,
        )


class NoPersonDetectedError(RuntimeError):
    pass


class UltralyticsYOLO26PoseRunner(YOLO26PoseRunner):
    def __init__(
        self,
        model_path,
        confidence: float = 0.25,
        min_confidence: float = 0.5,
        model=None,
    ):
        if model is None:
            try:
                from ultralytics import YOLO
            except ModuleNotFoundError as exc:
                raise ImportError(
                    "ultralytics is required to construct "
                    "UltralyticsYOLO26PoseRunner without an injected model.",
                ) from exc
            model = YOLO(model_path)
        super().__init__(
            model_path=model_path,
            model=model,
            min_confidence=min_confidence,
        )
        self.confidence = confidence

    def predict_keypoints(self, image):
        results = self._predict_one(image)
        result = results[0] if isinstance(results, (list, tuple)) else results
        keypoints = getattr(result, "keypoints", None)
        if keypoints is None:
            raise NoPersonDetectedError("No pose keypoints were detected.")

        data = getattr(keypoints, "data", None)
        if data is None:
            data = self._xy_conf_to_data(keypoints)
        people = _to_python(data)
        if not people:
            raise NoPersonDetectedError("No person was detected.")

        best_person = _best_person(people)
        if len(best_person) < 17:
            raise ValueError("Detected pose must contain at least 17 keypoints.")
        return _keypoint_array([row[:3] for row in best_person[:17]])

    def _predict_one(self, image):
        predict = getattr(self.model, "predict", None)
        if predict is not None:
            return predict(image, conf=self.confidence, verbose=False)
        return self.model(image)

    def _xy_conf_to_data(self, keypoints):
        xy = _to_python(getattr(keypoints, "xy", None))
        conf = _to_python(getattr(keypoints, "conf", None))
        if not xy:
            raise NoPersonDetectedError("No pose keypoints were detected.")
        people = []
        for person_index, person_xy in enumerate(xy):
            person_conf = conf[person_index] if conf else [1.0] * len(person_xy)
            people.append(
                [
                    [point[0], point[1], person_conf[keypoint_index]]
                    for keypoint_index, point in enumerate(person_xy)
                ],
            )
        return people


def _to_python(value):
    if value is None:
        return None
    cpu = getattr(value, "cpu", None)
    if cpu is not None:
        value = cpu()
    numpy_value = getattr(value, "numpy", None)
    if numpy_value is not None:
        value = numpy_value()
    tolist = getattr(value, "tolist", None)
    if tolist is not None:
        return tolist()
    return value


def _best_person(people):
    if _is_keypoint_row(people):
        return people
    if not people:
        raise NoPersonDetectedError("No person was detected.")
    return max(people, key=_mean_confidence)


def _is_keypoint_row(value):
    return (
        isinstance(value, (list, tuple))
        and len(value) >= 17
        and isinstance(value[0], (list, tuple))
        and len(value[0]) >= 3
        and isinstance(value[0][0], (int, float))
    )


def _mean_confidence(person):
    scores = [float(row[2]) for row in person[:17] if len(row) >= 3]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def _keypoint_array(rows):
    numeric_rows = [
        [float(row[0]), float(row[1]), float(row[2])]
        for row in rows
    ]
    if np is not None:
        return np.array(numeric_rows, dtype="float32")
    return _KeypointArray(numeric_rows)


class _KeypointArray:
    def __init__(self, rows):
        self._rows = rows
        self.shape = (len(rows), len(rows[0]) if rows else 0)

    def __iter__(self):
        return iter(self._rows)

    def __getitem__(self, index):
        return self._rows[index]
