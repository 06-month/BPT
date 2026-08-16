from typing import Optional

import numpy as np


HAND_3D_CONNECTIONS = (
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (0, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (0, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (0, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (5, 9),
    (9, 13),
    (13, 17),
)

H36M_WRIST_INDEX = {
    "left": 13,
    "right": 16,
}


def build_hand_3d_overlay(
    hand_result: Optional[dict],
    body_joints_3d,
    side: str,
    mode: str,
    scale: float,
    axis_map: str = "x,y,z",
    flip_x: bool = False,
    flip_y: bool = False,
    flip_z: bool = False,
) -> dict:
    """Return visualization-only hand 3D data.

    MediaPipe hand world landmarks are hand-local, not body-camera coordinates.
    This helper subtracts MediaPipe landmark 0 and optionally anchors the local
    hand to a MotionAGFormer wrist joint for debugging visualization only.
    """
    if mode not in ("none", "local", "wrist-anchored"):
        raise ValueError('mode must be "none", "local", or "wrist-anchored"')
    result = {
        "available": False,
        "mode": mode,
        "world_landmarks": None,
        "local_landmarks": None,
        "draw_landmarks": None,
        "attached_landmarks": None,
        "body_wrist_index": H36M_WRIST_INDEX.get(side),
        "body_wrist_3d": None,
        "anchor_error": None,
        "anchor_matches_body_wrist": False,
        "skip_reason": None,
    }
    if mode == "none":
        result["skip_reason"] = "disabled"
        return result
    if hand_result is None:
        result["skip_reason"] = "no_hand_result"
        return result
    world_landmarks = landmarks_to_array(hand_result.get("hand_world_landmarks"))
    if world_landmarks is None:
        result["skip_reason"] = "no_hand_world_landmarks"
        return result
    if world_landmarks.shape != (21, 3):
        result["skip_reason"] = f"unexpected_hand_world_shape:{world_landmarks.shape}"
        return result

    local = world_landmarks - world_landmarks[0:1]
    transformed = transform_hand_local_axes(
        local,
        axis_map=axis_map,
        flip_x=flip_x,
        flip_y=flip_y,
        flip_z=flip_z,
    )
    draw_landmarks = transformed * float(scale)
    result.update(
        {
            "available": True,
            "world_landmarks": world_landmarks.tolist(),
            "local_landmarks": transformed.tolist(),
            "draw_landmarks": draw_landmarks.tolist(),
            "skip_reason": None,
        },
    )
    if mode == "local":
        return result

    wrist_index = H36M_WRIST_INDEX.get(side)
    body = None if body_joints_3d is None else np.asarray(body_joints_3d, dtype="float32")
    if body is None or body.shape != (17, 3) or wrist_index is None:
        result["available"] = False
        result["skip_reason"] = "no_body_wrist_3d"
        return result
    body_wrist = body[wrist_index].astype("float32")
    attached = body_wrist[None, :] + draw_landmarks
    anchor_error = float(np.linalg.norm(attached[0] - body_wrist))
    result.update(
        {
            "body_wrist_3d": body_wrist.tolist(),
            "attached_landmarks": attached.tolist(),
            "draw_landmarks": attached.tolist(),
            "anchor_error": anchor_error,
            "anchor_matches_body_wrist": bool(np.allclose(attached[0], body_wrist)),
        },
    )
    return result


def landmarks_to_array(landmarks):
    if landmarks is None:
        return None
    seq = getattr(landmarks, "landmark", landmarks)
    points = [
        [
            float(landmark.x),
            float(landmark.y),
            float(getattr(landmark, "z", 0.0)),
        ]
        for landmark in seq
    ]
    return np.asarray(points, dtype="float32")


def transform_hand_local_axes(
    local_points,
    axis_map: str = "x,y,z",
    flip_x: bool = False,
    flip_y: bool = False,
    flip_z: bool = False,
):
    points = np.asarray(local_points, dtype="float32")
    axes = _parse_axis_map(axis_map)
    transformed = np.stack([points[:, axis] * sign for axis, sign in axes], axis=1)
    if flip_x:
        transformed[:, 0] *= -1.0
    if flip_y:
        transformed[:, 1] *= -1.0
    if flip_z:
        transformed[:, 2] *= -1.0
    return transformed.astype("float32")


def _parse_axis_map(axis_map: str):
    axis_lookup = {"x": 0, "y": 1, "z": 2}
    tokens = [token.strip().lower() for token in axis_map.split(",")]
    if len(tokens) != 3:
        raise ValueError('--hand-3d-axis-map must contain three comma-separated axes, e.g. "x,y,z"')
    parsed = []
    used = set()
    for token in tokens:
        sign = 1.0
        if token.startswith("-"):
            sign = -1.0
            token = token[1:]
        if token not in axis_lookup:
            raise ValueError(f"invalid hand 3D axis token: {token}")
        axis = axis_lookup[token]
        if axis in used:
            raise ValueError("hand 3D axis map must use each source axis once")
        used.add(axis)
        parsed.append((axis, sign))
    return tuple(parsed)
