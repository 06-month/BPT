from pose_feedback.feedback.invalid_reason import resolve_invalid_reason
from pose_feedback.wrist.geometry import (
    angle_between_normals,
    bend_angle_to_risk,
    classify_bend_risk,
    classify_rotation,
    crop_to_image_coords,
    normalize3,
    palm_normal_from_world,
    valid_forearm_projection,
    wrist_bend_angle_2d,
)
from pose_feedback.wrist.smoothing import AsymmetricEMA, ResultHolder


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
        self.holder = ResultHolder(max_hold_seconds=config.max_hold_seconds)

    def set_baseline_normal(self, normal) -> None:
        self.baseline_palm_normal = normalize3(normal)

    def reset(self, reset_baseline: bool = True) -> None:
        self.bend_risk_filter.reset()
        self.rotation_delta_filter.reset()
        self.holder.reset()
        if reset_baseline:
            self.baseline_palm_normal = None

    def estimate(
        self,
        elbow_px,
        wrist_px,
        elbow_conf: float,
        wrist_conf: float,
        shoulder_width_px,
        hand_landmarks,
        hand_world_landmarks,
        crop_box,
        is_right_hand: bool = True,
        current_time_sec: float = 0.0,
    ) -> dict:
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
        elbow_conf: float,
        wrist_conf: float,
        shoulder_width_px,
        hand_landmarks,
        hand_world_landmarks,
        crop_box,
        is_right_hand: bool = True,
    ) -> dict:
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
        if not valid_forearm_projection(
            elbow_px=elbow_px,
            wrist_px=wrist_px,
            shoulder_width_px=shoulder_width_px,
            min_forearm_ratio=self.config.min_forearm_ratio,
            min_horizontal_ratio=self.config.min_horizontal_ratio,
            min_vertical_ratio=self.config.min_vertical_ratio,
        ):
            result["global_invalid_reason"] = "poor_forearm_projection"
            return result

        if self.config.use_bend:
            if hand_landmarks is None:
                result["bend_invalid_reason"] = "no_hand_landmarks"
            elif crop_box is None:
                result["bend_invalid_reason"] = "no_hand_landmarks"
            else:
                x1, y1, x2, y2 = crop_box
                middle_mcp_px = crop_to_image_coords(
                    hand_landmarks.landmark[9],
                    x1,
                    y1,
                    x2,
                    y2,
                )
                raw_angle = wrist_bend_angle_2d(elbow_px, wrist_px, middle_mcp_px)
                raw_risk = bend_angle_to_risk(raw_angle)
                smooth_risk = self.bend_risk_filter.update(raw_risk)
                result["bend_valid"] = True
                result["bend_angle_2d"] = float(180.0 - smooth_risk)
                result["bend_risk"] = float(smooth_risk)
                result["bend_state"] = classify_bend_risk(smooth_risk, self.config)

        if self.config.use_rotation:
            if hand_world_landmarks is None:
                result["rotation_invalid_reason"] = "no_hand_world_landmarks"
            elif self.baseline_palm_normal is None:
                result["rotation_invalid_reason"] = "no_baseline_palm_normal"
            else:
                current_normal = palm_normal_from_world(
                    hand_world_landmarks,
                    is_right_hand=is_right_hand,
                )
                raw_delta = angle_between_normals(
                    self.baseline_palm_normal,
                    current_normal,
                )
                smooth_delta = self.rotation_delta_filter.update(raw_delta)
                result["rotation_valid"] = True
                result["palm_rotation_delta"] = float(smooth_delta)
                result["rotation_state"] = classify_rotation(smooth_delta, self.config)

        result["valid"] = result["bend_valid"] or result["rotation_valid"]
        if not result["valid"]:
            result["global_invalid_reason"] = (
                resolve_invalid_reason(result) or "no_valid_feature"
            )
        return result
