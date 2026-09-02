"""BlazePose 33-joint to H36M17 mapping.

MediaPipe emits BlazePose GHUM's 33 joints. H36M17's pelvis, spine, thorax,
neck and head have no direct BlazePose counterpart, so they are synthesized
with exactly the rule ``pose_feedback/body/motionagformer_adapter.py`` uses for
COCO17. Keeping the synthesis identical is what makes the RTMPose arm and the
MediaPipe arm comparable: both are scored on the same constructed joints, and
any error the synthesis introduces is charged to both.
"""

from __future__ import annotations

import numpy as np

from bpt.benchmarks.pose.adapters.joint_mapping import H36M17_NAMES

BLAZEPOSE = {
    "nose": 0,
    "left_eye": 2,
    "right_eye": 5,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}

# H36M17 index -> the BlazePose joints averaged to produce it.
H36M_FROM_BLAZEPOSE = {
    0: ("left_hip", "right_hip"),        # pelvis
    1: ("right_hip",),
    2: ("right_knee",),
    3: ("right_ankle",),
    4: ("left_hip",),
    5: ("left_knee",),
    6: ("left_ankle",),
    8: ("left_shoulder", "right_shoulder"),  # thorax
    10: ("left_eye", "right_eye"),           # head
    11: ("left_shoulder",),
    12: ("left_elbow",),
    13: ("left_wrist",),
    14: ("right_shoulder",),
    15: ("right_elbow",),
    16: ("right_wrist",),
}


def blazepose33_to_h36m17(landmarks: np.ndarray) -> np.ndarray:
    """Map ``[33,C]`` BlazePose joints to ``[17,C]`` H36M17 joints.

    The last channel is treated as a score and averaged like the coordinates,
    matching the COCO17 adapter's confidence aggregation.
    """

    landmarks = np.asarray(landmarks, dtype=np.float64)
    if landmarks.ndim != 2 or landmarks.shape[0] != 33:
        raise ValueError(f"expected BlazePose [33,C], got {landmarks.shape}")
    output = np.zeros((17, landmarks.shape[1]), dtype=np.float64)
    for index, sources in H36M_FROM_BLAZEPOSE.items():
        rows = [landmarks[BLAZEPOSE[name]] for name in sources]
        output[index] = np.mean(rows, axis=0)
    pelvis, thorax = output[0], output[8]
    output[7] = (pelvis + thorax) / 2.0                                  # spine
    output[9] = (landmarks[BLAZEPOSE["nose"]] + thorax) / 2.0            # neck
    return output


def mapping_table() -> list[dict[str, object]]:
    return [
        {
            "h36m_index": index,
            "h36m_joint": H36M17_NAMES[index],
            "blazepose_sources": list(H36M_FROM_BLAZEPOSE.get(index, ())) or "synthesized",
        }
        for index in range(17)
    ]
