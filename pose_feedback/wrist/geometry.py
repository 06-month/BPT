from math import acos, degrees, sqrt
from typing import Optional, Protocol, Sequence, Tuple

Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]


class ImageLandmark(Protocol):
    x: float
    y: float


class WorldLandmark(Protocol):
    x: float
    y: float
    z: float


class LandmarkList(Protocol):
    landmark: Sequence[WorldLandmark]


def _sub2(a: Point2D, b: Point2D) -> Point2D:
    return a[0] - b[0], a[1] - b[1]


def _norm2(v: Point2D) -> float:
    return sqrt(v[0] * v[0] + v[1] * v[1])


def _norm3(v: Point3D) -> float:
    return sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def normalize3(v: Point3D) -> Point3D:
    length = _norm3(v) + 1e-8
    return v[0] / length, v[1] / length, v[2] / length


def compute_shoulder_width(
    left_shoulder_px: Optional[Point2D],
    right_shoulder_px: Optional[Point2D],
) -> Optional[float]:
    if left_shoulder_px is None or right_shoulder_px is None:
        return None
    return _norm2(_sub2(left_shoulder_px, right_shoulder_px))


def crop_to_image_coords(
    landmark: ImageLandmark,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> Point2D:
    return landmark.x * (x2 - x1) + x1, landmark.y * (y2 - y1) + y1


def angle_between(v1: Point2D, v2: Point2D) -> float:
    n1 = _norm2(v1) + 1e-8
    n2 = _norm2(v2) + 1e-8
    dot = (v1[0] / n1) * (v2[0] / n2) + (v1[1] / n1) * (v2[1] / n2)
    clamped = max(-1.0, min(1.0, dot))
    return degrees(acos(clamped))


def wrist_bend_angle_2d(
    elbow_px: Point2D,
    wrist_px: Point2D,
    middle_mcp_px: Point2D,
) -> float:
    forearm_vec = _sub2(elbow_px, wrist_px)
    hand_vec = _sub2(middle_mcp_px, wrist_px)
    return angle_between(forearm_vec, hand_vec)


def bend_angle_to_risk(angle: float) -> float:
    return max(0.0, 180.0 - angle)


def valid_forearm_projection(
    elbow_px: Point2D,
    wrist_px: Point2D,
    shoulder_width_px: Optional[float],
    min_forearm_ratio: float = 0.15,
    min_horizontal_ratio: Optional[float] = None,
    min_vertical_ratio: Optional[float] = None,
) -> bool:
    if shoulder_width_px is None or shoulder_width_px <= 1e-8:
        return False
    vec = _sub2(wrist_px, elbow_px)
    forearm_len = _norm2(vec) + 1e-8
    if forearm_len / shoulder_width_px < min_forearm_ratio:
        return False
    horizontal_ratio = abs(vec[0]) / forearm_len
    vertical_ratio = abs(vec[1]) / forearm_len
    if min_horizontal_ratio is not None and horizontal_ratio < min_horizontal_ratio:
        return False
    if min_vertical_ratio is not None and vertical_ratio < min_vertical_ratio:
        return False
    return True


def classify_bend_risk(risk: float, config) -> str:
    if risk <= config.bend_good_max_risk:
        return "good"
    if risk <= config.bend_warning_max_risk:
        return "warning"
    return "bad"


def palm_normal_from_world(
    hand_world_landmarks: LandmarkList,
    is_right_hand: bool = True,
) -> Point3D:
    wrist = hand_world_landmarks.landmark[0]
    index_mcp = hand_world_landmarks.landmark[5]
    pinky_mcp = hand_world_landmarks.landmark[17]
    v_index = (
        index_mcp.x - wrist.x,
        index_mcp.y - wrist.y,
        index_mcp.z - wrist.z,
    )
    v_pinky = (
        pinky_mcp.x - wrist.x,
        pinky_mcp.y - wrist.y,
        pinky_mcp.z - wrist.z,
    )
    normal = (
        v_index[1] * v_pinky[2] - v_index[2] * v_pinky[1],
        v_index[2] * v_pinky[0] - v_index[0] * v_pinky[2],
        v_index[0] * v_pinky[1] - v_index[1] * v_pinky[0],
    )
    if not is_right_hand:
        normal = -normal[0], -normal[1], -normal[2]
    return normalize3(normal)


def angle_between_normals(n0: Point3D, n1: Point3D) -> float:
    a = normalize3(n0)
    b = normalize3(n1)
    dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
    return degrees(acos(max(-1.0, min(1.0, dot))))


def classify_rotation(delta: float, config) -> str:
    if delta < config.rotation_warning_deg:
        return "stable"
    if delta < config.rotation_bad_deg:
        return "rotated_warning"
    return "rotated_bad"
