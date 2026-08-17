"""Visualization-only 2D body wrist anchoring helpers."""

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None

from pose_feedback.body.motionagformer_wrist_source import COCO_WRIST_INDEX


def build_visual_body_2d(
    raw_body_2d,
    mediapipe_wrists_px=None,
    body_wrist_anchor="rtmpose",
):
    """Return a body-keypoint copy for 2D drawing plus per-side debug.

    This is intentionally independent from MotionAGFormer input selection. It
    only affects the rendered body skeleton overlay and never mutates raw
    RTMPose keypoints.
    """
    if np is None:  # pragma: no cover
        raise ImportError("numpy is required for visual body wrist anchoring")
    if body_wrist_anchor not in ("rtmpose", "mediapipe"):
        raise ValueError('body_wrist_anchor must be "rtmpose" or "mediapipe"')

    raw = np.asarray(raw_body_2d, dtype="float32")
    if raw.shape != (17, 2) and raw.shape != (17, 3):
        raise ValueError(f"raw_body_2d must have shape [17, 2] or [17, 3], got {raw.shape}")

    visual_body = raw.copy()
    mediapipe_wrists_px = mediapipe_wrists_px or {}
    debug = {
        "body_wrist_2d_anchor": body_wrist_anchor,
        "raw_keypoints_mutated": False,
        "left": _side_debug(raw, visual_body, "left", None, "rtmpose"),
        "right": _side_debug(raw, visual_body, "right", None, "rtmpose"),
    }

    if body_wrist_anchor == "rtmpose":
        return visual_body, debug

    for side, wrist_index in COCO_WRIST_INDEX.items():
        mp_wrist = _as_wrist_xy(mediapipe_wrists_px.get(side))
        if mp_wrist is None:
            debug[side] = _side_debug(raw, visual_body, side, None, "fallback")
            continue
        visual_body[wrist_index, :2] = mp_wrist
        debug[side] = _side_debug(raw, visual_body, side, mp_wrist, "mediapipe")

    return visual_body, debug


def _side_debug(raw, visual_body, side, mediapipe_wrist, source_used):
    wrist_index = COCO_WRIST_INDEX[side]
    return {
        "source_used": source_used,
        "rtmpose_wrist_px": _xy_list(raw[wrist_index, :2]),
        "mediapipe_wrist_px": None if mediapipe_wrist is None else _xy_list(mediapipe_wrist),
        "visual_body_wrist_px": _xy_list(visual_body[wrist_index, :2]),
        "wrist_index": wrist_index,
    }


def _as_wrist_xy(value):
    if value is None:
        return None
    arr = np.asarray(value, dtype="float32")
    if arr.shape[0] < 2:
        return None
    return arr[:2].astype("float32")


def _xy_list(value):
    return [float(value[0]), float(value[1])]
