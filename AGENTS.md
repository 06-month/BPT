# AGENTS.md
# Project: On-device Real-time Wrist / Body Pose Feedback System
This repository implements a smartphone on-device real-time pose feedback system.
Primary goal:
- Estimate body pose with YOLO26-pose or an equivalent body pose estimator.
- Estimate hand orientation only when needed.
- Compute wrist-related fitness feedback.
- Prioritize mobile runtime stability, low latency, robust feedback timing, and implementation clarity over research-only accuracy.
This project is not a generic hand pose estimation project.
It is a wrist-orientation and exercise-feedback system.
The system must support:
- Single-side wrist bend feedback, starting with `pushup_side`.
- Later extension to bimanual exercises such as `latpulldown_back`.
- A modular interface so MediaPipe Hands can later be replaced by a better hand orientation model without rewriting the whole pipeline.
---
# 1. High-level architecture
Implement the system using the following module boundaries.
```text
ExercisePoseFeedbackSystem
├─ YOLO26PoseRunner
├─ HandRunner
│  ├─ fullframe mode
│  └─ crop mode
├─ HandWristMatcher
├─ CropBoxSmoother
├─ WristEstimatorLeft
├─ WristEstimatorRight
├─ BimanualBaselineCalibrator
├─ BimanualWristAnalyzer
├─ RepPhaseDetector
└─ FeedbackEngine
   ├─ invalid reason resolver
   ├─ held result gate
   ├─ phase-aware feedback
   └─ feedback throttle

Responsibilities:

YOLO26PoseRunner:
- Runs body pose estimation.
- Provides shoulder, elbow, wrist 2D image coordinates and keypoint confidences.
- Defines left/right side ownership.
HandRunner:
- Runs hand landmark estimation.
- Supports full-frame and crop mode.
- Always returns hand wrist coordinates restored to original image coordinates.
- Must hide fullframe/crop coordinate differences from downstream modules.
HandWristMatcher:
- Matches YOLO left/right wrist keypoints to detected hand landmark results.
- Uses YOLO side as the source of truth for left/right assignment.
- Does not blindly trust MediaPipe handedness.
CropBoxSmoother:
- Smooths wrist crop boxes to reduce crop-induced landmark jitter.
WristEstimator:
- Estimates one side only.
- Computes feature-level wrist information:
  - bend risk from 2D image landmarks
  - palm rotation delta from hand world landmarks
- Does not perform bimanual symmetry logic.
- Does not perform feedback timing logic.
BimanualBaselineCalibrator:
- Collects left/right palm baseline normals simultaneously.
- Used for bimanual exercises where rotation delta comparison matters.
BimanualWristAnalyzer:
- Computes left/right symmetry features.
- Example:
  - wrist height difference
  - elbow height difference
  - rotation delta difference
  - timing difference
RepPhaseDetector:
- Estimates exercise phase.
- Example:
  - down_phase
  - up_phase
  - hold
  - hold_bottom
  - hold_top
  - unknown
FeedbackEngine:
- Decides when and what to tell the user.
- Applies held-result gating.
- Applies feedback throttling.
- Applies invalid reason prioritization.
- Applies phase-aware feedback rules.

Do not collapse these responsibilities into one monolithic class.

⸻

2. Core design principles

2.1 YOLO side owns left/right identity

YOLO body pose keypoints determine left and right.

MediaPipe handedness may be wrong in practical conditions:

* selfie camera mirror preview
* crop-based input
* hands crossing
* palm/back-of-hand transition
* occlusion by exercise equipment

Therefore:

YOLO left_wrist  → system left wrist
YOLO right_wrist → system right wrist

MediaPipe handedness is only a secondary signal for palm normal direction correction.

Recommended policy:

def resolve_is_right_hand(yolo_side, mp_handedness=None, selfie_mirror=False):
    """
    YOLO side is the primary source of truth.
    Use MediaPipe handedness only as auxiliary metadata.
    Recommendation:
    - Run inference on the original camera frame.
    - Apply selfie mirroring only at the UI preview layer.
    """
    if selfie_mirror:
        return yolo_side == "left"
    return yolo_side == "right"

2.2 Coordinate systems must never be mixed

YOLO26-pose body keypoints are 2D image pixel coordinates.

MediaPipe hand image landmarks are normalized coordinates relative to the input image or crop.

MediaPipe hand world landmarks are local 3D hand coordinates, not directly compatible with YOLO 2D image coordinates.

Never do this:

angle_between(
    yolo_elbow_pixel,
    yolo_wrist_pixel,
    mediapipe_middle_mcp_world
)

This is invalid because the coordinates are from different spaces.

Correct policy:

For 2D bend:
- Use YOLO elbow/wrist in original image pixel coordinates.
- Convert MediaPipe crop-normalized MCP landmarks back to original image pixel coordinates.
- Compute 2D projected angle in original image coordinates.
For palm rotation:
- Use MediaPipe hand_world_landmarks only.
- Compute palm normal in hand-world coordinate space.
- Compare current palm normal against baseline palm normal.
- Prefer baseline-relative rotation delta over absolute pronation/supination angle.

2.3 Wrist angle is not a single value

Separate wrist-related features:

1. Wrist bend / flexion-extension proxy
   - 2D projected elbow-wrist-middle_mcp angle.
   - Useful mainly for side-view exercises.
   - Example: pushup_side, plank_side.
2. Radial / ulnar deviation proxy
   - 2D image-space deviation.
   - More meaningful in front-view.
   - Not part of the first MVP unless required.
3. Pronation / supination proxy
   - Palm normal rotation using hand_world_landmarks.
   - Must be baseline-relative.
   - Do not claim exact anatomical 3D rotation from monocular RGB.
4. Bimanual symmetry
   - Left/right wrist height.
   - Left/right elbow height.
   - Left/right palm rotation delta difference.
   - Useful for latpulldown_back and similar bimanual exercises.

⸻

3. Initial MVP scope

Start with pushup_side.

Do not start with latpulldown_back.

Reason:

* latpulldown_back is difficult due to rear-view projection artifact, bar occlusion, two-hand matching, and grip occlusion.
* pushup_side validates the core pipeline with fewer failure modes.

MVP target:

Exercise:
- pushup_side
Models:
- YOLO26-pose for body
- MediaPipe Hands in crop mode for hand orientation proxy
Features:
- use_bend=True
- use_rotation=False
- use_symmetry=False
- use_rep_phase=False
Pipeline:
YOLO26-pose
→ visible-side elbow/wrist
→ shoulder_width calculation
→ wrist crop generation
→ crop smoothing
→ MediaPipe Hands crop mode
→ crop_to_image_coords
→ bend_angle_2d
→ bend_risk
→ asymmetric smoothing
→ time-based hold
→ time-based feedback throttle

Do not implement the entire latpulldown system before the pushup_side MVP works.

⸻

4. Exercise config

Use a config-driven design.

Do not hardcode thresholds inside estimator logic.

Use seconds instead of frame counts.
Use normalized body-scale ratios instead of absolute pixel thresholds where possible.

from dataclasses import dataclass
from typing import Optional, Literal
HandDetectionMode = Literal["fullframe", "crop"]
@dataclass
class WristExerciseConfig:
    name: str
    # feature usage
    use_bend: bool = True
    use_rotation: bool = True
    use_symmetry: bool = False
    use_rep_phase: bool = False
    # hand detection policy
    hand_detection_mode: HandDetectionMode = "crop"
    # hand matching
    max_hand_match_ratio: float = 0.35
    max_hand_match_px_fallback: float = 100.0
    # bend risk thresholds
    # bend_risk = 180 - bend_angle
    bend_good_max_risk: float = 20.0
    bend_warning_max_risk: float = 40.0
    # palm rotation delta thresholds
    rotation_warning_deg: float = 25.0
    rotation_bad_deg: float = 45.0
    # projection validity
    # Use shoulder-width-normalized forearm length.
    min_forearm_ratio: float = 0.15
    min_horizontal_ratio: Optional[float] = None
    min_vertical_ratio: Optional[float] = None
    # temporal behavior
    max_hold_seconds: float = 0.3
    feedback_min_interval_seconds: float = 1.0
    # crop smoothing
    crop_smoothing_alpha: float = 0.4
    # bimanual symmetry, normalized by shoulder width
    symmetry_good_max_norm: float = 0.05
    symmetry_warning_max_norm: float = 0.10

Recommended configs:

PUSHUP_SIDE_CONFIG = WristExerciseConfig(
    name="pushup_side",
    use_bend=True,
    use_rotation=False,
    use_symmetry=False,
    use_rep_phase=False,
    hand_detection_mode="crop",
    bend_good_max_risk=25.0,      # angle >= 155
    bend_warning_max_risk=45.0,   # angle >= 135
    min_forearm_ratio=0.15,
    max_hold_seconds=0.25,
    feedback_min_interval_seconds=1.0,
    crop_smoothing_alpha=0.45,
)
LATPULLDOWN_BACK_CONFIG = WristExerciseConfig(
    name="latpulldown_back",
    use_bend=False,
    use_rotation=True,
    use_symmetry=True,
    use_rep_phase=True,
    hand_detection_mode="fullframe",
    max_hand_match_ratio=0.45,
    max_hand_match_px_fallback=130.0,
    rotation_warning_deg=35.0,
    rotation_bad_deg=60.0,
    min_forearm_ratio=0.12,
    min_horizontal_ratio=0.3,
    max_hold_seconds=0.35,
    feedback_min_interval_seconds=1.5,
    crop_smoothing_alpha=0.35,
    symmetry_good_max_norm=0.05,
    symmetry_warning_max_norm=0.10,
)

⸻

5. Body pose assumptions

YOLO26-pose or equivalent COCO-style body pose model is expected to provide:

left_shoulder
right_shoulder
left_elbow
right_elbow
left_wrist
right_wrist

COCO index convention, if used:

left_elbow  = keypoint 7
right_elbow = keypoint 8
left_wrist  = keypoint 9
right_wrist = keypoint 10

The code must not assume that keypoint ordering is always COCO unless the model adapter explicitly documents it.

Create a body adapter layer that returns named keypoints:

{
    "left": {
        "shoulder_px": np.array([x, y]),
        "elbow_px": np.array([x, y]),
        "wrist_px": np.array([x, y]),
        "shoulder_conf": float,
        "elbow_conf": float,
        "wrist_conf": float,
    },
    "right": {
        "shoulder_px": np.array([x, y]),
        "elbow_px": np.array([x, y]),
        "wrist_px": np.array([x, y]),
        "shoulder_conf": float,
        "elbow_conf": float,
        "wrist_conf": float,
    },
    "shoulder_width_px": float | None,
}

⸻

6. Shoulder width normalization

Avoid absolute pixel thresholds wherever possible.

Compute shoulder width:

import numpy as np
def compute_shoulder_width(left_shoulder_px, right_shoulder_px):
    if left_shoulder_px is None or right_shoulder_px is None:
        return None
    return float(np.linalg.norm(left_shoulder_px - right_shoulder_px))

Use shoulder width to normalize:

* forearm length validity
* bimanual symmetry
* hand matching distance where possible

Forearm projection validity:

def valid_forearm_projection(
    elbow_px,
    wrist_px,
    shoulder_width_px,
    min_forearm_ratio=0.15,
    min_horizontal_ratio=None,
    min_vertical_ratio=None,
):
    vec = wrist_px - elbow_px
    forearm_len = np.linalg.norm(vec) + 1e-8
    if shoulder_width_px is None or shoulder_width_px <= 1e-8:
        return False
    forearm_ratio = forearm_len / shoulder_width_px
    if forearm_ratio < min_forearm_ratio:
        return False
    horizontal_ratio = abs(vec[0]) / forearm_len
    vertical_ratio = abs(vec[1]) / forearm_len
    if min_horizontal_ratio is not None and horizontal_ratio < min_horizontal_ratio:
        return False
    if min_vertical_ratio is not None and vertical_ratio < min_vertical_ratio:
        return False
    return True

Notes:

* min_forearm_ratio replaces min_forearm_len_px.
* min_horizontal_ratio is useful for rear/front-view movements where the projected forearm direction may collapse.
* For latpulldown_back, 2D bend is unreliable; use use_bend=False.

⸻

7. HandRunner

HandRunner must hide whether MediaPipe or the hand model is running in full-frame or crop mode.

Downstream modules should receive hand results in a unified format.

class HandRunner:
    def __init__(self, mode="crop"):
        assert mode in ("fullframe", "crop")
        self.mode = mode
    def run_fullframe(self, image):
        """
        Return list of hand results.
        Each hand result must have:
        {
            "hand_landmarks": ...,
            "hand_world_landmarks": ...,
            "handedness": "Left" or "Right" or None,
            "wrist_px": np.array([x, y]),  # original image coordinate
            "crop_box": None,
        }
        """
        raise NotImplementedError
    def run_crop(self, image, crop_box):
        """
        crop_box: (x1, y1, x2, y2) in original image coordinates.
        Return list of hand results.
        Each result must have:
        {
            "hand_landmarks": ...,
            "hand_world_landmarks": ...,
            "handedness": "Left" or "Right" or None,
            "wrist_px": np.array([x, y]),  # restored to original image coordinate
            "crop_box": crop_box,
        }
        """
        raise NotImplementedError

Full-frame wrist coordinate:

def mp_wrist_to_image_coords(hand_landmarks, image_w, image_h):
    lm = hand_landmarks.landmark[0]
    return np.array([
        lm.x * image_w,
        lm.y * image_h,
    ], dtype=np.float32)

Crop-mode wrist coordinate:

def mp_wrist_crop_to_image_coords(hand_landmarks, crop_box):
    x1, y1, x2, y2 = crop_box
    lm = hand_landmarks.landmark[0]
    return np.array([
        lm.x * (x2 - x1) + x1,
        lm.y * (y2 - y1) + y1,
    ], dtype=np.float32)

Crop-to-image coordinate conversion for any landmark:

def crop_to_image_coords(landmark, x1, y1, x2, y2):
    crop_w = x2 - x1
    crop_h = y2 - y1
    return np.array([
        landmark.x * crop_w + x1,
        landmark.y * crop_h + y1,
    ], dtype=np.float32)

⸻

8. Crop generation and smoothing

Generate a hand crop from elbow/wrist.

Initial crop may be centered at the wrist.
Improved crop should shift from wrist toward the hand direction.

def make_forward_hand_crop_box(
    elbow,
    wrist,
    image_w,
    image_h,
    scale=2.2,
    shift=0.45,
):
    forearm_vec = wrist - elbow
    forearm_len = np.linalg.norm(forearm_vec) + 1e-8
    direction = forearm_vec / forearm_len
    center = wrist + direction * forearm_len * shift
    size = max(96.0, forearm_len * scale)
    cx, cy = center
    x1 = int(max(0, cx - size / 2))
    y1 = int(max(0, cy - size / 2))
    x2 = int(min(image_w, cx + size / 2))
    y2 = int(min(image_h, cy + size / 2))
    return x1, y1, x2, y2

Smooth crop box per side:

class CropBoxSmoother:
    def __init__(self, alpha=0.4):
        self.alpha = alpha
        self.box = None
    def update(self, box):
        new = np.array(box, dtype=np.float32)
        if self.box is None:
            self.box = new
        else:
            self.box = self.alpha * new + (1 - self.alpha) * self.box
        return tuple(self.box.astype(np.int32))
    def reset(self):
        self.box = None

Use separate smoothers:

left_crop_smoother = CropBoxSmoother(alpha=config.crop_smoothing_alpha)
right_crop_smoother = CropBoxSmoother(alpha=config.crop_smoothing_alpha)

Notes:

* Crop smoothing reduces jitter.
* Too much crop smoothing can cause the crop to lag behind fast hand movement.
* Tune crop_smoothing_alpha per exercise.

⸻

9. HandWristMatcher

Match YOLO wrists to hand results using distance in original image coordinates.

Use YOLO side as the final side identity.

def valid_hand_match(
    dist_px,
    shoulder_width_px,
    max_match_ratio=0.35,
    max_match_px_fallback=100.0,
):
    if shoulder_width_px is not None and shoulder_width_px > 1e-8:
        return (dist_px / shoulder_width_px) <= max_match_ratio
    return dist_px <= max_match_px_fallback
def match_hands_to_yolo_wrists(
    yolo_wrists,
    hand_results,
    shoulder_width_px,
    max_match_ratio,
    max_match_px_fallback,
):
    """
    yolo_wrists:
    {
        "left":  {"wrist_px": np.array([x, y]), "conf": float},
        "right": {"wrist_px": np.array([x, y]), "conf": float},
    }
    hand_results:
    [
        {
            "hand_landmarks": ...,
            "hand_world_landmarks": ...,
            "handedness": ...,
            "wrist_px": np.array([x, y]),
            "crop_box": ...,
        },
        ...
    ]
    return:
    {
        "left": hand_result_or_None,
        "right": hand_result_or_None,
    }
    """
    matched = {"left": None, "right": None}
    candidates = []
    for side, yolo_data in yolo_wrists.items():
        wrist_px = yolo_data["wrist_px"]
        conf = yolo_data["conf"]
        if wrist_px is None or conf < 0.5:
            continue
        for hand_idx, hand in enumerate(hand_results):
            if hand.get("wrist_px") is None:
                continue
            dist = float(np.linalg.norm(wrist_px - hand["wrist_px"]))
            candidates.append({
                "side": side,
                "hand_idx": hand_idx,
                "dist": dist,
            })
    candidates.sort(key=lambda x: x["dist"])
    used_sides = set()
    used_hands = set()
    for c in candidates:
        side = c["side"]
        hand_idx = c["hand_idx"]
        dist = c["dist"]
        if side in used_sides:
            continue
        if hand_idx in used_hands:
            continue
        if not valid_hand_match(
            dist_px=dist,
            shoulder_width_px=shoulder_width_px,
            max_match_ratio=max_match_ratio,
            max_match_px_fallback=max_match_px_fallback,
        ):
            continue
        matched[side] = hand_results[hand_idx]
        used_sides.add(side)
        used_hands.add(hand_idx)
    return matched

Notes:

* Fullframe mode requires matching.
* Crop mode has a side prior, but distance validation is still useful.
* For latpulldown_back, allow larger match tolerance than pushup_side.

⸻

10. Palm normal and rotation delta

Use MediaPipe hand_world_landmarks for palm normal.

Do not mix this with YOLO 2D vectors.

def normalize(v):
    return v / (np.linalg.norm(v) + 1e-8)
def palm_normal_from_world(hand_world_landmarks, is_right_hand=True):
    """
    Uses:
    0  wrist
    5  index_mcp
    17 pinky_mcp
    Correct normal direction using left/right hand.
    """
    wrist = np.array([
        hand_world_landmarks.landmark[0].x,
        hand_world_landmarks.landmark[0].y,
        hand_world_landmarks.landmark[0].z,
    ], dtype=np.float32)
    index_mcp = np.array([
        hand_world_landmarks.landmark[5].x,
        hand_world_landmarks.landmark[5].y,
        hand_world_landmarks.landmark[5].z,
    ], dtype=np.float32)
    pinky_mcp = np.array([
        hand_world_landmarks.landmark[17].x,
        hand_world_landmarks.landmark[17].y,
        hand_world_landmarks.landmark[17].z,
    ], dtype=np.float32)
    v_index = index_mcp - wrist
    v_pinky = pinky_mcp - wrist
    palm_normal = np.cross(v_index, v_pinky)
    if not is_right_hand:
        palm_normal = -palm_normal
    return normalize(palm_normal)
def angle_between_normals(n0, n1):
    n0 = normalize(n0)
    n1 = normalize(n1)
    cos = np.clip(np.dot(n0, n1), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos)))

Policy:

* Use baseline-relative palm rotation delta.
* Do not treat it as exact anatomical pronation/supination.
* Use it as a robust relative orientation feature.

⸻

11. Baseline calibration

11.1 Single-hand calibrator

class BaselineCalibrator:
    def __init__(self, required_frames=15, min_frames=5, max_attempts=90):
        self.required_frames = required_frames
        self.min_frames = min_frames
        self.max_attempts = max_attempts
        self.normals = []
        self.attempts = 0
    def update(self, hand_world_landmarks, is_right_hand=True):
        self.attempts += 1
        if hand_world_landmarks is not None:
            normal = palm_normal_from_world(
                hand_world_landmarks,
                is_right_hand=is_right_hand
            )
            self.normals.append(normal)
        if len(self.normals) >= self.required_frames:
            mean_normal = normalize(np.mean(self.normals, axis=0))
            return "done", mean_normal
        if self.attempts >= self.max_attempts:
            if len(self.normals) >= self.min_frames:
                mean_normal = normalize(np.mean(self.normals, axis=0))
                return "done_partial", mean_normal
            return "failed", None
        return "collecting", None
    def reset(self):
        self.normals = []
        self.attempts = 0

UI states:

collecting:
- "기준 자세를 유지하세요."
done:
- "기준값 설정 완료."
done_partial:
- "기준값이 불안정할 수 있습니다. 그래도 시작합니다."
failed:
- "손목 기준값을 잡지 못했습니다. 손이 보이게 다시 잡아주세요."

11.2 Bimanual baseline calibrator

For bimanual exercises, collect both hands in the same frames.

class BimanualBaselineCalibrator:
    def __init__(self, required_frames=15, min_frames=5, max_attempts=90):
        self.required_frames = required_frames
        self.min_frames = min_frames
        self.max_attempts = max_attempts
        self.left_normals = []
        self.right_normals = []
        self.attempts = 0
    def update(
        self,
        left_world_lm,
        right_world_lm,
        left_is_right_hand=False,
        right_is_right_hand=True,
    ):
        self.attempts += 1
        # Use only frames where both hands are available.
        if left_world_lm is not None and right_world_lm is not None:
            left_normal = palm_normal_from_world(
                left_world_lm,
                is_right_hand=left_is_right_hand,
            )
            right_normal = palm_normal_from_world(
                right_world_lm,
                is_right_hand=right_is_right_hand,
            )
            self.left_normals.append(left_normal)
            self.right_normals.append(right_normal)
        if len(self.left_normals) >= self.required_frames:
            left_mean = normalize(np.mean(self.left_normals, axis=0))
            right_mean = normalize(np.mean(self.right_normals, axis=0))
            return "done", left_mean, right_mean
        if self.attempts >= self.max_attempts:
            if len(self.left_normals) >= self.min_frames:
                left_mean = normalize(np.mean(self.left_normals, axis=0))
                right_mean = normalize(np.mean(self.right_normals, axis=0))
                return "done_partial", left_mean, right_mean
            return "failed", None, None
        return "collecting", None, None
    def reset(self):
        self.left_normals = []
        self.right_normals = []
        self.attempts = 0

⸻

12. Bend angle and bend risk

For 2D bend, use original image pixel coordinates only.

def angle_between(v1, v2):
    v1 = v1 / (np.linalg.norm(v1) + 1e-8)
    v2 = v2 / (np.linalg.norm(v2) + 1e-8)
    cos = np.clip(np.dot(v1, v2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos)))
def wrist_bend_angle_2d(elbow_px, wrist_px, middle_mcp_px):
    """
    2D projected wrist bend angle.
    Most meaningful for side-view flexion/extension proxy.
    """
    forearm_vec = elbow_px - wrist_px
    hand_vec = middle_mcp_px - wrist_px
    return angle_between(forearm_vec, hand_vec)

Use bend risk, not raw angle, for smoothing:

def bend_angle_to_risk(angle):
    """
    180 degrees is straight.
    Smaller angle means more wrist bend.
    risk = 180 - angle
    """
    return max(0.0, 180.0 - angle)

Classification:

def classify_bend_risk(risk, config):
    if risk <= config.bend_good_max_risk:
        return "good"
    elif risk <= config.bend_warning_max_risk:
        return "warning"
    else:
        return "bad"

Reason:

* Bend angle decreases when posture worsens.
* Rotation delta increases when posture worsens.
* By converting bend angle to risk, both bend and rotation can use the same smoothing convention:
    * risk/delta increase = bad
    * risk/delta decrease = recovery

⸻

13. Asymmetric EMA

Use asymmetric smoothing for fast bad detection and slower recovery.

class AsymmetricEMA:
    def __init__(self, alpha_increase=0.5, alpha_decrease=0.2):
        """
        x increase = higher risk / worse state.
        x decrease = recovery.
        """
        self.alpha_increase = alpha_increase
        self.alpha_decrease = alpha_decrease
        self.value = None
    def update(self, x):
        if self.value is None:
            self.value = x
            return self.value
        alpha = self.alpha_increase if x > self.value else self.alpha_decrease
        self.value = alpha * x + (1.0 - alpha) * self.value
        return self.value
    def reset(self):
        self.value = None

Recommended usage:

bend_risk_filter = AsymmetricEMA(
    alpha_increase=0.55,
    alpha_decrease=0.20,
)
rotation_delta_filter = AsymmetricEMA(
    alpha_increase=0.45,
    alpha_decrease=0.25,
)

These values are initial guesses.
Tune using real video.
Do not assume they are final.

⸻

14. Time-based ResultHolder

Do not use frame-count based hold thresholds.

Use seconds because FPS may vary across devices.

class ResultHolder:
    def __init__(self, max_hold_seconds=0.3):
        self.max_hold_seconds = max_hold_seconds
        self.last_valid_result = None
        self.last_valid_time_sec = None
    def update(self, result, current_time_sec):
        if result.get("valid"):
            result["is_held"] = False
            result["hold_duration_sec"] = 0.0
            self.last_valid_result = dict(result)
            self.last_valid_time_sec = current_time_sec
            return result
        if self.last_valid_result is not None and self.last_valid_time_sec is not None:
            hold_duration = current_time_sec - self.last_valid_time_sec
            if hold_duration <= self.max_hold_seconds:
                held = dict(self.last_valid_result)
                held["is_held"] = True
                held["hold_duration_sec"] = hold_duration
                held["global_invalid_reason"] = result.get("global_invalid_reason")
                return held
        return result
    def reset(self):
        self.last_valid_result = None
        self.last_valid_time_sec = None

Policy:

* Held result may keep UI stable.
* Held result must not generate new warning feedback.
* Held result may show a subtle “tracking unstable” indicator.
* Held result should be side-specific, not global.

⸻

15. WristEstimator

WristEstimator estimates one side only.

It must process bend and rotation independently.

One feature failing must not kill the other feature.

Result schema:

{
    "valid": bool,
    "global_invalid_reason": str | None,
    "bend_valid": bool,
    "bend_angle_2d": float | None,
    "bend_risk": float | None,
    "bend_state": "good" | "warning" | "bad" | None,
    "bend_invalid_reason": str | None,
    "rotation_valid": bool,
    "palm_rotation_delta": float | None,
    "rotation_state": "stable" | "rotated_warning" | "rotated_bad" | None,
    "rotation_invalid_reason": str | None,
    "is_held": bool,
    "hold_duration_sec": float,
}

Implementation skeleton:

class WristEstimator:
    def __init__(self, config):
        self.config = config
        self.bend_risk_filter = AsymmetricEMA(
            alpha_increase=0.55,
            alpha_decrease=0.20,
        )
        self.rotation_delta_filter = AsymmetricEMA(
            alpha_increase=0.45,
            alpha_decrease=0.25,
        )
        self.baseline_palm_normal = None
        self.holder = ResultHolder(
            max_hold_seconds=config.max_hold_seconds
        )
    def set_baseline_normal(self, normal):
        self.baseline_palm_normal = normalize(normal)
    def reset(self, reset_baseline=True):
        self.bend_risk_filter.reset()
        self.rotation_delta_filter.reset()
        self.holder.reset()
        if reset_baseline:
            self.baseline_palm_normal = None
    def estimate(
        self,
        elbow_px,
        wrist_px,
        elbow_conf,
        wrist_conf,
        shoulder_width_px,
        hand_landmarks,
        hand_world_landmarks,
        crop_box,
        is_right_hand=True,
        current_time_sec=0.0,
    ):
        raw_result = self._estimate_once(
            elbow_px=elbow_px,
            wrist_px=wrist_px,
            elbow_conf=elbow_conf,
            wrist_conf=wrist_conf,
            shoulder_width_px=shoulder_width_px,
            hand_landmarks=hand_landmarks,
            hand_world_landmarks=hand_world_landmarks,
            crop_box=crop_box,
            is_right_hand=is_right_hand,
        )
        return self.holder.update(raw_result, current_time_sec)
    def _estimate_once(
        self,
        elbow_px,
        wrist_px,
        elbow_conf,
        wrist_conf,
        shoulder_width_px,
        hand_landmarks,
        hand_world_landmarks,
        crop_box,
        is_right_hand=True,
    ):
        result = {
            "valid": False,
            "global_invalid_reason": None,
            "bend_valid": False,
            "bend_angle_2d": None,
            "bend_risk": None,
            "bend_state": None,
            "bend_invalid_reason": None,
            "rotation_valid": False,
            "palm_rotation_delta": None,
            "rotation_state": None,
            "rotation_invalid_reason": None,
            "is_held": False,
            "hold_duration_sec": 0.0,
        }
        if elbow_conf < 0.5 or wrist_conf < 0.5:
            result["global_invalid_reason"] = "low_body_confidence"
            return result
        projection_valid = valid_forearm_projection(
            elbow_px=elbow_px,
            wrist_px=wrist_px,
            shoulder_width_px=shoulder_width_px,
            min_forearm_ratio=self.config.min_forearm_ratio,
            min_horizontal_ratio=self.config.min_horizontal_ratio,
            min_vertical_ratio=self.config.min_vertical_ratio,
        )
        if not projection_valid:
            result["global_invalid_reason"] = "poor_forearm_projection"
            return result
        x1, y1, x2, y2 = crop_box
        # Feature 1: 2D bend
        if self.config.use_bend:
            if hand_landmarks is None:
                result["bend_invalid_reason"] = "no_hand_landmarks"
            else:
                middle_mcp_px = crop_to_image_coords(
                    hand_landmarks.landmark[9],
                    x1, y1, x2, y2
                )
                raw_bend_angle = wrist_bend_angle_2d(
                    elbow_px,
                    wrist_px,
                    middle_mcp_px
                )
                raw_bend_risk = bend_angle_to_risk(raw_bend_angle)
                smooth_bend_risk = self.bend_risk_filter.update(raw_bend_risk)
                smooth_bend_angle = 180.0 - smooth_bend_risk
                result["bend_valid"] = True
                result["bend_angle_2d"] = float(smooth_bend_angle)
                result["bend_risk"] = float(smooth_bend_risk)
                result["bend_state"] = classify_bend_risk(
                    smooth_bend_risk,
                    self.config
                )
        # Feature 2: palm rotation
        if self.config.use_rotation:
            if hand_world_landmarks is None:
                result["rotation_invalid_reason"] = "no_hand_world_landmarks"
            elif self.baseline_palm_normal is None:
                result["rotation_invalid_reason"] = "no_baseline_palm_normal"
            else:
                current_normal = palm_normal_from_world(
                    hand_world_landmarks,
                    is_right_hand=is_right_hand
                )
                raw_delta = angle_between_normals(
                    self.baseline_palm_normal,
                    current_normal
                )
                smooth_delta = self.rotation_delta_filter.update(raw_delta)
                result["rotation_valid"] = True
                result["palm_rotation_delta"] = float(smooth_delta)
                result["rotation_state"] = classify_rotation(
                    smooth_delta,
                    self.config
                )
        result["valid"] = result["bend_valid"] or result["rotation_valid"]
        if not result["valid"]:
            result["global_invalid_reason"] = resolve_invalid_reason(result) or "no_valid_feature"
        return result

Rotation classification:

def classify_rotation(delta, config):
    if delta < config.rotation_warning_deg:
        return "stable"
    elif delta < config.rotation_bad_deg:
        return "rotated_warning"
    else:
        return "rotated_bad"

⸻

16. BimanualWristAnalyzer

This module is not part of the pushup_side MVP.
Use it for latpulldown_back and other bimanual exercises.

Use normalized values, not raw pixels.

def analyze_bimanual_symmetry(
    left_result,
    right_result,
    left_body,
    right_body,
    shoulder_width_px,
    config,
):
    result = {
        "valid": False,
        "wrist_height_diff_norm": None,
        "elbow_height_diff_norm": None,
        "rotation_delta_diff": None,
        "symmetry_state": None,
        "invalid_reason": None,
    }
    if shoulder_width_px is None or shoulder_width_px <= 1e-8:
        result["invalid_reason"] = "missing_shoulder_width"
        return result
    left_wrist = left_body.get("wrist_px")
    right_wrist = right_body.get("wrist_px")
    left_elbow = left_body.get("elbow_px")
    right_elbow = right_body.get("elbow_px")
    if left_wrist is None or right_wrist is None:
        result["invalid_reason"] = "missing_wrist"
        return result
    wrist_height_diff_norm = abs(left_wrist[1] - right_wrist[1]) / shoulder_width_px
    result["wrist_height_diff_norm"] = float(wrist_height_diff_norm)
    if left_elbow is not None and right_elbow is not None:
        result["elbow_height_diff_norm"] = float(
            abs(left_elbow[1] - right_elbow[1]) / shoulder_width_px
        )
    if (
        left_result is not None
        and right_result is not None
        and left_result.get("rotation_valid")
        and right_result.get("rotation_valid")
    ):
        left_delta = left_result["palm_rotation_delta"]
        right_delta = right_result["palm_rotation_delta"]
        result["rotation_delta_diff"] = float(abs(left_delta - right_delta))
    if wrist_height_diff_norm < config.symmetry_good_max_norm:
        state = "good"
    elif wrist_height_diff_norm < config.symmetry_warning_max_norm:
        state = "warning"
    else:
        state = "bad"
    result["symmetry_state"] = state
    result["valid"] = True
    return result

Policy:

* Symmetry feedback requires both sides to be real-time, not held.
* If one side is held, suppress symmetry feedback.
* Per-side feedback for the non-held side may still fire.

⸻

17. RepPhaseDetector

Use this for exercises where feedback depends on phase.

For initial latpulldown_back implementation, a wrist-y velocity detector is acceptable.

class RepPhaseDetector:
    def __init__(
        self,
        window=5,
        move_threshold_px=3.0,
    ):
        self.window = window
        self.move_threshold_px = move_threshold_px
        self.y_history = []
    def update(self, left_wrist_y=None, right_wrist_y=None):
        ys = []
        if left_wrist_y is not None:
            ys.append(left_wrist_y)
        if right_wrist_y is not None:
            ys.append(right_wrist_y)
        if not ys:
            return "unknown"
        mean_y = float(np.mean(ys))
        self.y_history.append(mean_y)
        if len(self.y_history) > self.window:
            self.y_history.pop(0)
        if len(self.y_history) < 2:
            return "unknown"
        dy = self.y_history[-1] - self.y_history[0]
        # image coordinate: y increase = moving down
        if dy > self.move_threshold_px:
            return "down_phase"
        elif dy < -self.move_threshold_px:
            return "up_phase"
        else:
            return "hold"
    def reset(self):
        self.y_history = []

Future expansion:

* Replace velocity-only phase detection with a state machine:
    * unknown
    * top_hold
    * down_phase
    * bottom_hold
    * up_phase
    * top_hold

For latpulldown_back:

* Strong wrist/grip/symmetry warnings should usually fire in down_phase or hold_bottom.
* Suppress strong warnings during up_phase unless clearly necessary.

⸻

18. Invalid reason resolver

Feature-level invalid reasons can coexist.

Use deterministic priority.

INVALID_PRIORITY = [
    "low_body_confidence",
    "poor_forearm_projection",
    "no_baseline_palm_normal",
    "no_hand_world_landmarks",
    "no_hand_landmarks",
    "missing_shoulder_width",
    "missing_wrist",
    "no_valid_feature",
]
def resolve_invalid_reason(result):
    reasons = []
    for key in [
        "global_invalid_reason",
        "rotation_invalid_reason",
        "bend_invalid_reason",
        "invalid_reason",
    ]:
        reason = result.get(key)
        if reason is not None:
            reasons.append(reason)
    if not reasons:
        return None
    for priority_reason in INVALID_PRIORITY:
        if priority_reason in reasons:
            return priority_reason
    return reasons[0]

UI messages:

INVALID_MESSAGE = {
    "low_body_confidence": "팔이 화면에 잘 보이게 해주세요.",
    "poor_forearm_projection": "현재 각도에서는 손목 판정이 어렵습니다. 팔이 더 잘 보이게 자세를 조정하세요.",
    "no_baseline_palm_normal": "손목 기준값을 먼저 잡아야 합니다.",
    "no_hand_world_landmarks": "손바닥 방향을 추정하지 못했습니다.",
    "no_hand_landmarks": "손이 가려졌습니다. 손목이 보이게 해주세요.",
    "missing_shoulder_width": "상체가 화면에 충분히 보이게 해주세요.",
    "missing_wrist": "양쪽 손목이 화면에 보이게 해주세요.",
    "no_valid_feature": "손목 상태를 판정할 수 없습니다.",
}

⸻

19. FeedbackEngine

FeedbackEngine decides:

* whether to fire feedback
* which feedback to fire
* how often to fire
* whether the current result is reliable enough

Use time-based throttling.

class FeedbackThrottle:
    def __init__(self, min_interval_seconds=1.0):
        self.min_interval_seconds = min_interval_seconds
        self.last_feedback_time = {}
    def should_fire(self, feedback_type, current_time_sec):
        last = self.last_feedback_time.get(feedback_type, -1e9)
        if current_time_sec - last >= self.min_interval_seconds:
            self.last_feedback_time[feedback_type] = current_time_sec
            return True
        return False
    def reset(self):
        self.last_feedback_time = {}

Held gate must be side-specific.

Never do this:

if left_result and left_result.get("is_held"):
    return feedbacks
if right_result and right_result.get("is_held"):
    return feedbacks

Correct policy:

left feedback:
- Allowed only if left_result is not held.
right feedback:
- Allowed only if right_result is not held.
symmetry feedback:
- Allowed only if neither left_result nor right_result is held.

Implementation skeleton:

class FeedbackEngine:
    def __init__(self, config):
        self.config = config
        self.throttle = FeedbackThrottle(
            min_interval_seconds=config.feedback_min_interval_seconds
        )
    def generate(
        self,
        left_result=None,
        right_result=None,
        symmetry_result=None,
        rep_phase="unknown",
        current_time_sec=0.0,
    ):
        left_held = bool(left_result and left_result.get("is_held"))
        right_held = bool(right_result and right_result.get("is_held"))
        allow_left_feedback = left_result is not None and not left_held
        allow_right_feedback = right_result is not None and not right_held
        allow_symmetry_feedback = (
            symmetry_result is not None
            and not left_held
            and not right_held
        )
        if self.config.use_rep_phase:
            return self._generate_phase_aware_feedback(
                left_result=left_result,
                right_result=right_result,
                symmetry_result=symmetry_result,
                rep_phase=rep_phase,
                current_time_sec=current_time_sec,
                allow_left_feedback=allow_left_feedback,
                allow_right_feedback=allow_right_feedback,
                allow_symmetry_feedback=allow_symmetry_feedback,
            )
        return self._generate_basic_feedback(
            left_result=left_result,
            right_result=right_result,
            symmetry_result=symmetry_result,
            current_time_sec=current_time_sec,
            allow_left_feedback=allow_left_feedback,
            allow_right_feedback=allow_right_feedback,
            allow_symmetry_feedback=allow_symmetry_feedback,
        )
    def _generate_basic_feedback(
        self,
        left_result,
        right_result,
        symmetry_result,
        current_time_sec,
        allow_left_feedback,
        allow_right_feedback,
        allow_symmetry_feedback,
    ):
        feedbacks = []
        for side, result, allowed in [
            ("left", left_result, allow_left_feedback),
            ("right", right_result, allow_right_feedback),
        ]:
            if not allowed:
                continue
            if result is None:
                continue
            if not result.get("valid"):
                reason = resolve_invalid_reason(result)
                if reason:
                    feedback_type = f"{side}:invalid:{reason}"
                    if self.throttle.should_fire(feedback_type, current_time_sec):
                        feedbacks.append({
                            "type": feedback_type,
                            "severity": "info",
                            "message": INVALID_MESSAGE.get(
                                reason,
                                "손목 상태를 인식할 수 없습니다."
                            ),
                        })
                continue
            if result.get("bend_state") == "bad":
                feedback_type = f"{side}:bend_bad"
                if self.throttle.should_fire(feedback_type, current_time_sec):
                    feedbacks.append({
                        "type": feedback_type,
                        "severity": "warning",
                        "message": f"{side} 손목이 많이 꺾였습니다.",
                    })
            if result.get("rotation_state") == "rotated_bad":
                feedback_type = f"{side}:rotation_bad"
                if self.throttle.should_fire(feedback_type, current_time_sec):
                    feedbacks.append({
                        "type": feedback_type,
                        "severity": "warning",
                        "message": f"{side} 손목 회전이 기준 자세에서 많이 벗어났습니다.",
                    })
        if allow_symmetry_feedback:
            if symmetry_result.get("symmetry_state") == "bad":
                feedback_type = "symmetry_bad"
                if self.throttle.should_fire(feedback_type, current_time_sec):
                    feedbacks.append({
                        "type": feedback_type,
                        "severity": "warning",
                        "message": "좌우 손목 높이가 크게 다릅니다.",
                    })
        return feedbacks
    def _generate_phase_aware_feedback(
        self,
        left_result,
        right_result,
        symmetry_result,
        rep_phase,
        current_time_sec,
        allow_left_feedback,
        allow_right_feedback,
        allow_symmetry_feedback,
    ):
        # Example policy for latpulldown:
        # Strong feedback only during pulling or bottom hold.
        if rep_phase not in ("down_phase", "hold_bottom", "hold"):
            return []
        return self._generate_basic_feedback(
            left_result=left_result,
            right_result=right_result,
            symmetry_result=symmetry_result,
            current_time_sec=current_time_sec,
            allow_left_feedback=allow_left_feedback,
            allow_right_feedback=allow_right_feedback,
            allow_symmetry_feedback=allow_symmetry_feedback,
        )
    def reset(self):
        self.throttle.reset()

⸻

20. Latpulldown back policy

For latpulldown_back, do not rely on 2D wrist bend.

Use:

use_bend=False
use_rotation=True
use_symmetry=True
use_rep_phase=True
hand_detection_mode=fullframe

Rationale:

* Rear-view 2D wrist bend is unreliable due to projection artifact.
* Forearm may point into camera depth.
* Bar occlusion can break crop-mode hand detection.
* Useful wrist-related cues are:
    * left/right wrist height symmetry
    * left/right elbow height symmetry
    * palm/grip orientation change
    * left/right rotation delta difference
    * phase-aware timing

Avoid strong wrist bend warnings in rear-view latpulldown.

⸻

21. Pushup side policy

For pushup_side, use:

use_bend=True
use_rotation=False
use_symmetry=False
use_rep_phase=False
hand_detection_mode=crop

Rationale:

* Side-view 2D bend is meaningful enough as a practical wrist extension proxy.
* Hand crop is likely stable.
* Rotation is not necessary for the first MVP.
* Symmetry and rep phase are not required for first validation.

⸻

22. Reset lifecycle

Every stateful module must expose reset().

Reset when:

* exercise type changes
* camera direction changes
* user requests recalibration
* camera switches
* new set starts, if the UX requires independent sets

Do not reset on:

* one-frame tracking failure
* short MediaPipe hand miss
* short occlusion

Modules requiring reset:

* WristEstimator
* AsymmetricEMA
* ResultHolder
* CropBoxSmoother
* BaselineCalibrator
* BimanualBaselineCalibrator
* RepPhaseDetector
* FeedbackThrottle
* FeedbackEngine

⸻

23. UI contract

The UI must distinguish:

feature disabled:
- config.use_* is False.
- Hide the feature row entirely.
feature unavailable:
- config.use_* is True, but *_valid is False.
- Show a mild tracking or setup message.
held result:
- valid=True, is_held=True.
- Show previous value in a subdued style.
- Do not fire new warning feedback.
real-time valid result:
- valid=True, is_held=False.
- Show value normally.
- Allow feedback generation.
invalid result:
- valid=False.
- Show invalid reason message.

Do not treat None as always an error.
None can mean:

* disabled by config
* unavailable due to missing input
* invalid due to projection/body issue

Always inspect:

* config.use_bend
* bend_valid
* bend_invalid_reason
* config.use_rotation
* rotation_valid
* rotation_invalid_reason
* is_held

⸻

24. Implementation order

Implement in this order.

Phase 1: Pushup side MVP

Required modules:

* YOLO26PoseRunner
* CropBoxSmoother
* HandRunner crop mode
* WristEstimator single-side
* FeedbackEngine basic throttle

Required validation:

* YOLO wrist stability
* crop box stability
* MediaPipe Hands crop success rate
* crop_to_image_coords correctness
* bend_angle_2d / bend_risk behavior
* asymmetric smoothing behavior
* time-based hold behavior
* time-based feedback throttle behavior

Do not implement:

* BimanualBaselineCalibrator
* BimanualWristAnalyzer
* RepPhaseDetector
* fullframe HandRunner mode
    unless necessary.

Phase 2: Plank side

Mostly same as pushup_side.
Use to tune wrist extension thresholds.

Phase 3: Shoulder press front

Add:

* rotation feature
* baseline calibration
* both hands if needed

Phase 4: Latpulldown back

Add:

* fullframe HandRunner
* HandWristMatcher
* BimanualBaselineCalibrator
* BimanualWristAnalyzer
* RepPhaseDetector
* phase-aware FeedbackEngine

⸻

25. Testing and logging requirements

Log per frame at least:

{
    "timestamp_sec": float,
    "exercise": str,
    "side": "left" | "right",
    "elbow_conf": float,
    "wrist_conf": float,
    "shoulder_width_px": float | None,
    "crop_box": tuple | None,
    "hand_detected": bool,
    "hand_match_dist_norm": float | None,
    "bend_valid": bool,
    "bend_angle_2d": float | None,
    "bend_risk": float | None,
    "bend_state": str | None,
    "rotation_valid": bool,
    "palm_rotation_delta": float | None,
    "rotation_state": str | None,
    "valid": bool,
    "is_held": bool,
    "hold_duration_sec": float,
    "invalid_reason": str | None,
    "rep_phase": str | None,
    "feedbacks": list,
}

This is required because most remaining values require real-video tuning.

Do not tune blindly.

Review actual video overlays and logs.

⸻

26. Known limitations

The system does not estimate exact anatomical wrist angles.

Limitations:

* Monocular RGB cannot reliably recover true 3D wrist biomechanics.
* YOLO body keypoints are 2D image coordinates.
* MediaPipe hand_world_landmarks are hand-local world-like coordinates, not a full calibrated camera-space 3D reconstruction.
* 2D bend angle is a projection proxy.
* Palm rotation delta is baseline-relative, not absolute pronation/supination.

Therefore, app wording should avoid claims like:

* “Your wrist is exactly 37 degrees extended.”
* “Your pronation angle is 52 degrees.”

Prefer:

* “손목이 기준 자세보다 많이 꺾였습니다.”
* “손목 방향이 기준 자세에서 벗어났습니다.”
* “좌우 손목 높이가 다릅니다.”
* “현재 각도에서는 손목 판정이 어렵습니다.”

⸻

27. Do-not rules

Do not:

* Mix YOLO 2D pixels with MediaPipe hand_world_landmarks in one vector calculation.
* Use 2D bend angle as the main metric for rear-view latpulldown.
* Trust MediaPipe handedness as the final side assignment.
* Use frame-count thresholds for hold or feedback throttling.
* Use absolute pixel distances when shoulder-width normalization is available.
* Let one held hand suppress all feedback for the other hand.
* Fire new feedback from held results.
* Generate symmetry feedback if either side is held.
* Hardcode exercise thresholds inside estimator logic.
* Build latpulldown_back before pushup_side MVP is validated.
* Treat None output as always an error.
* Reset estimator state on one-frame tracking failure.
* Claim exact anatomical 3D wrist angle from this system.

⸻

28. Definition of done

For pushup_side MVP, done means:

1. YOLO26-pose body runner returns named elbow/wrist/shoulder keypoints.
2. shoulder_width_px is computed.
3. wrist crop is generated and smoothed.
4. MediaPipe Hands crop mode runs.
5. crop-normalized middle_mcp is restored to original image coordinates.
6. bend_angle_2d is computed only in image coordinate space.
7. bend_risk is computed and smoothed.
8. ResultHolder is time-based.
9. FeedbackThrottle is time-based.
10. FeedbackEngine does not fire from held result.
11. Logs include bend_valid, bend_risk, is_held, invalid_reason, and feedbacks.
12. A real pushup_side video can be processed end-to-end.

For latpulldown_back, done means:

1. fullframe HandRunner works.
2. HandWristMatcher maps both hands to YOLO wrists.
3. BimanualBaselineCalibrator collects same-frame left/right baselines.
4. left/right WristEstimators compute rotation deltas.
5. BimanualWristAnalyzer computes normalized symmetry.
6. RepPhaseDetector returns at least down_phase/up_phase/hold.
7. FeedbackEngine applies phase-aware feedback.
8. One held hand does not suppress the other side's per-side feedback.
9. Symmetry feedback is suppressed if either side is held.
10. Real latpulldown_back video can be processed with logs and overlay.

⸻

29. Preferred implementation style

Use clear typed Python modules first.
Do not prematurely optimize for mobile runtime before correctness is validated.

Recommended file organization:

pose_feedback/
├─ config.py
├─ body/
│  ├─ yolo26_runner.py
│  └─ body_adapter.py
├─ hand/
│  ├─ hand_runner.py
│  └─ hand_wrist_matcher.py
├─ wrist/
│  ├─ geometry.py
│  ├─ smoothing.py
│  ├─ crop.py
│  ├─ baseline.py
│  ├─ estimator.py
│  └─ bimanual.py
├─ feedback/
│  ├─ invalid_reason.py
│  ├─ throttle.py
│  └─ engine.py
├─ phase/
│  └─ rep_phase_detector.py
└─ app/
   └─ pipeline.py

Keep geometry utilities pure and testable.

Avoid putting model runtime code and wrist geometry code in the same file.

⸻

30. First task recommendation for Codex

When starting implementation, do this first:

Implement pushup_side MVP only.
Create:
- WristExerciseConfig
- geometry utilities
- AsymmetricEMA
- ResultHolder
- CropBoxSmoother
- WristEstimator
- FeedbackThrottle
- FeedbackEngine basic mode
Do not implement latpulldown_back yet.
Do not implement bimanual calibration yet.
Do not implement rep phase yet.
Add simple unit tests for:
- crop_to_image_coords
- bend_angle_to_risk
- valid_forearm_projection
- ResultHolder time hold
- FeedbackEngine held side gate

Required unit tests:

1. crop_to_image_coords:
   crop=(100,100,200,200), landmark=(0.5,0.5)
   expected=(150,150)
2. bend_angle_to_risk:
   angle=180 → risk=0
   angle=160 → risk=20
   angle=140 → risk=40
3. valid_forearm_projection:
   forearm too short relative to shoulder width → False
   sufficient forearm ratio → True
4. ResultHolder:
   invalid frame within max_hold_seconds returns held result
   invalid frame after max_hold_seconds returns invalid result
5. FeedbackEngine:
   left held, right bad → right feedback still fires
   right held, left bad → left feedback still fires
   either side held → symmetry feedback suppressed
