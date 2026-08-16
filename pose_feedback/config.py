from dataclasses import dataclass
from typing import Literal, Optional

HandDetectionMode = Literal["fullframe", "crop"]


@dataclass(frozen=True)
class WristExerciseConfig:
    name: str
    use_bend: bool = True
    use_rotation: bool = True
    use_symmetry: bool = False
    use_rep_phase: bool = False
    hand_detection_mode: HandDetectionMode = "crop"
    max_hand_match_ratio: float = 0.35
    max_hand_match_px_fallback: float = 100.0
    bend_good_max_risk: float = 20.0
    bend_warning_max_risk: float = 40.0
    rotation_warning_deg: float = 25.0
    rotation_bad_deg: float = 45.0
    min_forearm_ratio: float = 0.15
    min_horizontal_ratio: Optional[float] = None
    min_vertical_ratio: Optional[float] = None
    max_hold_seconds: float = 0.3
    feedback_min_interval_seconds: float = 1.0
    crop_smoothing_alpha: float = 0.4
    symmetry_good_max_norm: float = 0.05
    symmetry_warning_max_norm: float = 0.10


PUSHUP_SIDE_CONFIG = WristExerciseConfig(
    name="pushup_side",
    use_bend=True,
    use_rotation=False,
    use_symmetry=False,
    use_rep_phase=False,
    hand_detection_mode="crop",
    bend_good_max_risk=25.0,
    bend_warning_max_risk=45.0,
    min_forearm_ratio=0.15,
    max_hold_seconds=0.25,
    feedback_min_interval_seconds=1.0,
    crop_smoothing_alpha=0.45,
)
