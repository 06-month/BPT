"""Adapters for the Uplift-Upsample 3D lifter.

The lifter uses a Human3.6M-style 17-joint order, while RTMPose emits COCO 17.
This conversion is approximate. COCO does not contain exact H36M torso, neck,
head, or head-top joints, so those joints are proxies and can degrade 3D output.
"""

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None


UPLIFT_H36M17_NAMES = [
    "r_ankle",
    "r_knee",
    "r_hip",
    "l_hip",
    "l_knee",
    "l_ankle",
    "pelvis",
    "neck",
    "torso",
    "head",
    "head_top",
    "r_wrist",
    "r_elbow",
    "r_shoulder",
    "l_shoulder",
    "l_elbow",
    "l_wrist",
]


COCO = {
    "nose": 0,
    "left_eye": 1,
    "right_eye": 2,
    "left_ear": 3,
    "right_ear": 4,
    "left_shoulder": 5,
    "right_shoulder": 6,
    "left_elbow": 7,
    "right_elbow": 8,
    "left_wrist": 9,
    "right_wrist": 10,
    "left_hip": 11,
    "right_hip": 12,
    "left_knee": 13,
    "right_knee": 14,
    "left_ankle": 15,
    "right_ankle": 16,
}


def coco17_to_uplift_h36m17(coco17, min_confidence=0.3):
    """Convert COCO17 [x, y, conf] to Uplift's approximate H36M17 order.

    Low-confidence inputs are still geometrically converted so the sequence can
    remain dense, but output confidences expose the weak joints for masking or
    downstream diagnostics.
    """
    rows = _as_array(coco17)
    if rows.shape != (17, 3):
        raise ValueError("coco17 must have shape (17, 3)")

    joints = []
    confs = []

    def direct(name):
        row = rows[COCO[name]]
        return row[:2], float(row[2])

    def average(names, fallback_names=None):
        source_names = list(names)
        valid = [rows[COCO[name]] for name in source_names if rows[COCO[name], 2] >= min_confidence]
        if not valid and fallback_names:
            source_names = list(fallback_names)
            valid = [rows[COCO[name]] for name in source_names if rows[COCO[name], 2] >= min_confidence]
        if valid:
            arr = np.stack(valid, axis=0)
            return arr[:, :2].mean(axis=0), float(arr[:, 2].mean())
        arr = np.stack([rows[COCO[name]] for name in source_names], axis=0)
        return arr[:, :2].mean(axis=0), float(arr[:, 2].mean())

    def append(point_conf):
        point, conf = point_conf
        joints.append(point)
        confs.append(conf)

    append(direct("right_ankle"))
    append(direct("right_knee"))
    append(direct("right_hip"))
    append(direct("left_hip"))
    append(direct("left_knee"))
    append(direct("left_ankle"))
    append(average(("left_hip", "right_hip")))
    append(average(("left_shoulder", "right_shoulder")))
    pelvis, pelvis_conf = average(("left_hip", "right_hip"))
    neck, neck_conf = average(("left_shoulder", "right_shoulder"))
    append(((pelvis + neck) / 2.0, min(pelvis_conf, neck_conf)))
    append(average(("left_eye", "right_eye", "left_ear", "right_ear"), fallback_names=("nose",)))
    head, head_conf = average(("left_eye", "right_eye", "left_ear", "right_ear"), fallback_names=("nose",))
    head_top = head + (head - neck) * 0.35
    append((head_top, min(head_conf, neck_conf)))
    append(direct("right_wrist"))
    append(direct("right_elbow"))
    append(direct("right_shoulder"))
    append(direct("left_shoulder"))
    append(direct("left_elbow"))
    append(direct("left_wrist"))

    return np.asarray(joints, dtype="float32"), np.asarray(confs, dtype="float32")


def normalize_uplift_2d(joints_2d, image_width, image_height):
    """Apply Uplift/VideoPose3D screen-coordinate normalization.

    Training data uses common.dataset.camera.normalize_screen_coordinates:
    X / w * 2 - [1, h / w]. This preserves aspect ratio and maps x into
    approximately [-1, 1].
    """
    points = _as_2d_array(joints_2d)
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image_width and image_height must be positive")
    offset = np.asarray([1.0, float(image_height) / float(image_width)], dtype="float32")
    return (points / float(image_width) * 2.0 - offset).astype("float32")


def denormalize_uplift_2d(normalized_2d, image_width, image_height):
    points = _as_2d_array(normalized_2d)
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image_width and image_height must be positive")
    offset = np.asarray([1.0, float(image_height) / float(image_width)], dtype="float32")
    return ((points + offset) * float(image_width) / 2.0).astype("float32")


def make_stride_mask(window_size, mask_stride=None, center_index=None):
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    if center_index is None:
        center_index = window_size // 2
    if mask_stride is None:
        return np.ones((window_size,), dtype=bool)
    if isinstance(mask_stride, (list, tuple)):
        mask_stride = int(mask_stride[0])
    mask_stride = int(mask_stride)
    if mask_stride <= 1:
        return np.ones((window_size,), dtype=bool)
    indices = np.arange(window_size, dtype=int) - int(center_index)
    return np.equal(indices % mask_stride, 0)


def _as_array(values):
    if np is None:  # pragma: no cover
        raise ImportError("numpy is required for Uplift-Upsample adapters")
    return np.asarray(values, dtype="float32")


def _as_2d_array(values):
    arr = _as_array(values)
    if arr.shape[-1] != 2:
        raise ValueError("joints_2d must have last dimension 2")
    return arr
