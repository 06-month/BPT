"""MotionAGFormer 2D input adapters.

MotionAGFormer is trained on Human3.6M-style 17-joint inputs. RTMPose emits
COCO17. The COCO->H36M mapping below is ported from
external/2DEstimatorEval/data/prepare_2d_estimation.py::coco2h36m.

The mapping is still approximate for arbitrary in-the-wild COCO detections:
torso/head joints are synthesized from COCO joints, and that mismatch can
degrade depth estimation.
"""

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None


MOTIONAGFORMER_H36M17_NAMES = [
    "pelvis",
    "r_hip",
    "r_knee",
    "r_ankle",
    "l_hip",
    "l_knee",
    "l_ankle",
    "spine",
    "thorax",
    "neck",
    "head",
    "l_shoulder",
    "l_elbow",
    "l_wrist",
    "r_shoulder",
    "r_elbow",
    "r_wrist",
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


def coco17_to_motionagformer_h36m17(coco17):
    """Convert COCO17 keypoints to MotionAGFormer H36M17 2D joints.

    Args:
        coco17: Array with shape (..., 17, 2) or (..., 17, 3).

    Returns:
        If input contains x/y only, returns converted joints with shape
        (..., 17, 2). If input contains confidence, returns
        (converted_2d, converted_confidence).
    """
    arr = _as_array(coco17)
    if arr.shape[-2] != 17 or arr.shape[-1] not in (2, 3):
        raise ValueError("coco17 must have shape (..., 17, 2) or (..., 17, 3)")
    converted = _coco2h36m_xy(arr[..., :2])
    if arr.shape[-1] == 2:
        return converted.astype("float32")
    confidence = _coco2h36m_conf(arr[..., 2])
    return converted.astype("float32"), confidence.astype("float32")


def normalize_motionagformer_2d(joints_2d, image_width, image_height):
    """Normalize image coordinates as MotionAGFormer/VideoPose3D expects.

    Source convention:
    common.camera.normalize_screen_coordinates(X, w, h):
        X / w * 2 - [1, h / w]
    """
    points = _as_2d_array(joints_2d)
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image_width and image_height must be positive")
    offset = np.asarray([1.0, float(image_height) / float(image_width)], dtype="float32")
    return (points / float(image_width) * 2.0 - offset).astype("float32")


def denormalize_motionagformer_2d(normalized_2d, image_width, image_height):
    points = _as_2d_array(normalized_2d)
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image_width and image_height must be positive")
    offset = np.asarray([1.0, float(image_height) / float(image_width)], dtype="float32")
    return ((points + offset) * float(image_width) / 2.0).astype("float32")


def motionagformer_angles(joints_3d):
    """Return elbow/knee angles for MotionAGFormer's H36M17 order."""
    from pose_feedback.geometry.angles_3d import angle_3d

    joints = _as_array(joints_3d)
    if joints.shape[-2:] != (17, 3):
        raise ValueError("joints_3d must have shape (..., 17, 3)")
    return {
        "left_elbow": angle_3d(joints[11], joints[12], joints[13]),
        "right_elbow": angle_3d(joints[14], joints[15], joints[16]),
        "left_knee": angle_3d(joints[4], joints[5], joints[6]),
        "right_knee": angle_3d(joints[1], joints[2], joints[3]),
    }


def _coco2h36m_xy(keypoints):
    new_keypoints = np.zeros_like(keypoints)
    new_keypoints[..., 0, :] = (keypoints[..., 11, :] + keypoints[..., 12, :]) * 0.5
    new_keypoints[..., 1, :] = keypoints[..., 12, :]
    new_keypoints[..., 2, :] = keypoints[..., 14, :]
    new_keypoints[..., 3, :] = keypoints[..., 16, :]
    new_keypoints[..., 4, :] = keypoints[..., 11, :]
    new_keypoints[..., 5, :] = keypoints[..., 13, :]
    new_keypoints[..., 6, :] = keypoints[..., 15, :]
    new_keypoints[..., 8, :] = (keypoints[..., 5, :] + keypoints[..., 6, :]) * 0.5
    new_keypoints[..., 7, :] = (new_keypoints[..., 0, :] + new_keypoints[..., 8, :]) * 0.5
    new_keypoints[..., 9, :] = (keypoints[..., 0, :] + new_keypoints[..., 8, :]) * 0.5
    new_keypoints[..., 10, :] = (keypoints[..., 1, :] + keypoints[..., 2, :]) * 0.5
    new_keypoints[..., 11, :] = keypoints[..., 5, :]
    new_keypoints[..., 12, :] = keypoints[..., 7, :]
    new_keypoints[..., 13, :] = keypoints[..., 9, :]
    new_keypoints[..., 14, :] = keypoints[..., 6, :]
    new_keypoints[..., 15, :] = keypoints[..., 8, :]
    new_keypoints[..., 16, :] = keypoints[..., 10, :]
    return new_keypoints


def _coco2h36m_conf(confidence):
    conf = np.asarray(confidence, dtype="float32")
    new_conf = np.zeros(conf.shape[:-1] + (17,), dtype="float32")
    new_conf[..., 0] = (conf[..., 11] + conf[..., 12]) * 0.5
    new_conf[..., 1] = conf[..., 12]
    new_conf[..., 2] = conf[..., 14]
    new_conf[..., 3] = conf[..., 16]
    new_conf[..., 4] = conf[..., 11]
    new_conf[..., 5] = conf[..., 13]
    new_conf[..., 6] = conf[..., 15]
    new_conf[..., 8] = (conf[..., 5] + conf[..., 6]) * 0.5
    new_conf[..., 7] = (new_conf[..., 0] + new_conf[..., 8]) * 0.5
    new_conf[..., 9] = (conf[..., 0] + new_conf[..., 8]) * 0.5
    new_conf[..., 10] = (conf[..., 1] + conf[..., 2]) * 0.5
    new_conf[..., 11] = conf[..., 5]
    new_conf[..., 12] = conf[..., 7]
    new_conf[..., 13] = conf[..., 9]
    new_conf[..., 14] = conf[..., 6]
    new_conf[..., 15] = conf[..., 8]
    new_conf[..., 16] = conf[..., 10]
    return new_conf


def _as_array(values):
    if np is None:  # pragma: no cover
        raise ImportError("numpy is required for MotionAGFormer adapters")
    return np.asarray(values, dtype="float32")


def _as_2d_array(values):
    arr = _as_array(values)
    if arr.shape[-1] != 2:
        raise ValueError("joints_2d must have last dimension 2")
    return arr
