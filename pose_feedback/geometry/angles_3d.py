try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None


def angle_3d(a, b, c):
    """Return angle ABC in degrees, or None for zero-length vectors."""
    pts = _points(a, b, c)
    v1 = pts[0] - pts[1]
    v2 = pts[2] - pts[1]
    n1 = float(np.linalg.norm(v1))
    n2 = float(np.linalg.norm(v2))
    if n1 <= 1e-8 or n2 <= 1e-8:
        return None
    cos = float(np.dot(v1 / n1, v2 / n2))
    return float(np.degrees(np.arccos(np.clip(cos, -1.0, 1.0))))


def elbow_flexion_3d(shoulder, elbow, wrist):
    return angle_3d(shoulder, elbow, wrist)


def knee_flexion_3d(hip, knee, ankle):
    return angle_3d(hip, knee, ankle)


def torso_alignment_3d(shoulder_mid, hip_mid, ankle_mid_or_knee_mid):
    return angle_3d(shoulder_mid, hip_mid, ankle_mid_or_knee_mid)


# Wrist pronation/supination cannot be recovered from body-only 17-joint 3D.
# It requires hand 3D landmarks or a palm normal feature.


def _points(*values):
    if np is None:  # pragma: no cover
        raise ImportError("numpy is required for 3D angle utilities")
    return np.asarray(values, dtype="float32")
