from pose_feedback.body.body_adapter import coco_yolo_keypoints_to_body

try:
    import numpy as np
except ModuleNotFoundError:
    np = None


class RTMPoseNoPersonDetectedError(RuntimeError):
    pass


class RTMPoseRunner:
    def __init__(
        self,
        pose_config,
        pose_checkpoint,
        detector_config=None,
        detector_checkpoint=None,
        device: str = "cpu",
        pose_model=None,
        inference_fn=None,
        keypoint_indices=None,
        min_confidence: float = 0.5,
    ):
        self.pose_config = pose_config
        self.pose_checkpoint = pose_checkpoint
        self.detector_config = detector_config
        self.detector_checkpoint = detector_checkpoint
        self.device = device
        self.keypoint_indices = tuple(keypoint_indices or range(17))
        self.min_confidence = min_confidence

        if pose_model is None or inference_fn is None:
            try:
                from mmpose.apis import inference_topdown, init_model
            except ModuleNotFoundError as exc:
                raise ImportError(
                    "mmpose is required to construct RTMPoseRunner without "
                    "an injected pose_model and inference_fn."
                ) from exc
            if pose_model is None:
                pose_model = init_model(pose_config, pose_checkpoint, device=device)
            if inference_fn is None:
                inference_fn = inference_topdown

        self.pose_model = pose_model
        self.inference_fn = inference_fn

    def predict_keypoints(self, image):
        samples = self._run_inference(image)
        if not samples:
            raise RTMPoseNoPersonDetectedError("No person was detected by RTMPose.")
        keypoints, scores = _extract_keypoints_and_scores(samples[0])
        if len(keypoints) <= max(self.keypoint_indices):
            raise ValueError("RTMPose output does not contain enough keypoints.")
        rows = []
        for source_index in self.keypoint_indices:
            point = keypoints[source_index]
            score = scores[source_index] if scores is not None else _point_score(point)
            rows.append([float(point[0]), float(point[1]), float(score)])
        return _keypoint_array(rows)

    def predict_body(self, image):
        return coco_yolo_keypoints_to_body(
            self.predict_keypoints(image),
            min_confidence=self.min_confidence,
        )

    def _run_inference(self, image):
        bbox = _full_image_bbox(image)
        try:
            return self.inference_fn(self.pose_model, image, bboxes=bbox)
        except TypeError:
            return self.inference_fn(self.pose_model, image)


def _full_image_bbox(image):
    shape = getattr(image, "shape", None)
    if shape is None or len(shape) < 2:
        return None
    image_h, image_w = int(shape[0]), int(shape[1])
    rows = [[0.0, 0.0, float(image_w), float(image_h)]]
    if np is not None:
        return np.array(rows, dtype="float32")
    return rows


def _extract_keypoints_and_scores(sample):
    pred_instances = getattr(sample, "pred_instances", sample)
    keypoints = _to_python(getattr(pred_instances, "keypoints", None))
    scores = _to_python(getattr(pred_instances, "keypoint_scores", None))
    if keypoints is None:
        raise RTMPoseNoPersonDetectedError("RTMPose result has no keypoints.")
    keypoints = _first_keypoint_instance(keypoints)
    scores = None if scores is None else _first_score_instance(scores)
    return keypoints, scores


def _first_keypoint_instance(value):
    if not value:
        return value
    first = value[0]
    if isinstance(first, (list, tuple)) and first and isinstance(first[0], (list, tuple)):
        return first
    return value


def _first_score_instance(value):
    if not value:
        return value
    first = value[0]
    if isinstance(first, (list, tuple)):
        return first
    return value


def _point_score(point):
    if len(point) >= 3:
        return point[2]
    return 1.0


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


def _keypoint_array(rows):
    if np is not None:
        return np.array(rows, dtype="float32")
    return _KeypointArray(rows)


class _KeypointArray:
    def __init__(self, rows):
        self._rows = rows
        self.shape = (len(rows), len(rows[0]) if rows else 0)

    def __iter__(self):
        return iter(self._rows)

    def __getitem__(self, index):
        return self._rows[index]
