from math import sqrt

try:
    import numpy as np
except ModuleNotFoundError:
    class _NumpyCompat:
        @staticmethod
        def array(values, dtype=None):
            return tuple(float(value) for value in values)

    np = _NumpyCompat()


LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10


def coco_yolo_keypoints_to_body(keypoints, min_confidence=0.5):
    rows, dims = _validate_keypoints(keypoints)

    left = {
        "shoulder_px": _point(rows[LEFT_SHOULDER]),
        "elbow_px": _point(rows[LEFT_ELBOW]),
        "wrist_px": _point(rows[LEFT_WRIST]),
        "shoulder_conf": _confidence(rows[LEFT_SHOULDER], dims),
        "elbow_conf": _confidence(rows[LEFT_ELBOW], dims),
        "wrist_conf": _confidence(rows[LEFT_WRIST], dims),
    }
    right = {
        "shoulder_px": _point(rows[RIGHT_SHOULDER]),
        "elbow_px": _point(rows[RIGHT_ELBOW]),
        "wrist_px": _point(rows[RIGHT_WRIST]),
        "shoulder_conf": _confidence(rows[RIGHT_SHOULDER], dims),
        "elbow_conf": _confidence(rows[RIGHT_ELBOW], dims),
        "wrist_conf": _confidence(rows[RIGHT_WRIST], dims),
    }
    shoulder_width_px = None
    if (
        left["shoulder_conf"] >= min_confidence
        and right["shoulder_conf"] >= min_confidence
    ):
        shoulder_width_px = _distance(left["shoulder_px"], right["shoulder_px"])

    return {
        "left": left,
        "right": right,
        "shoulder_width_px": shoulder_width_px,
    }


def _validate_keypoints(keypoints):
    shape = getattr(keypoints, "shape", None)
    if shape is not None and len(shape) == 2:
        rows_count, dims = int(shape[0]), int(shape[1])
        if rows_count == 17 and dims in (2, 3):
            return keypoints, dims
        raise ValueError("keypoints must have shape (17, 2) or (17, 3)")

    try:
        rows = list(keypoints)
    except TypeError as exc:
        raise ValueError("keypoints must be a 2D sequence") from exc

    if len(rows) != 17:
        raise ValueError("keypoints must contain 17 rows")
    dims = None
    for row in rows:
        try:
            row_len = len(row)
        except TypeError as exc:
            raise ValueError("each keypoint row must be a sequence") from exc
        if row_len not in (2, 3):
            raise ValueError("keypoints must have shape (17, 2) or (17, 3)")
        if dims is None:
            dims = row_len
        elif row_len != dims:
            raise ValueError("all keypoint rows must have the same length")
    return rows, dims


def _point(row):
    return np.array([float(row[0]), float(row[1])], dtype="float32")


def _confidence(row, dims):
    if dims == 2:
        return 1.0
    return float(row[2])


def _distance(a, b):
    dx = float(a[0]) - float(b[0])
    dy = float(a[1]) - float(b[1])
    return float(sqrt(dx * dx + dy * dy))
