from pose_feedback.hand.hand_crop_selector import HandCropSelector
from pose_feedback.hand.hand_detector import select_best_hand_bbox_for_wrist
from pose_feedback.wrist.crop import CropBoxSmoother


class PushupSidePipeline:
    def __init__(
        self,
        config,
        body_runner,
        hand_runner,
        wrist_estimator,
        feedback_engine,
        hand_detector=None,
        hand_crop_selector=None,
    ):
        self.config = config
        self.body_runner = body_runner
        self.hand_runner = hand_runner
        self.wrist_estimator = wrist_estimator
        self.feedback_engine = feedback_engine
        self.hand_detector = hand_detector
        self.hand_crop_selector = hand_crop_selector or HandCropSelector()
        self.crop_smoother = CropBoxSmoother(alpha=config.crop_smoothing_alpha)

    def run_frame(self, image, timestamp_sec: float, side: str = "left") -> dict:
        if side not in ("left", "right"):
            raise ValueError('side must be "left" or "right"')

        body = self.body_runner.predict_body(image)
        side_body = body[side]
        image_w, image_h = _image_size(image)
        hand_bbox = None
        if self.hand_detector is not None:
            hand_bbox = select_best_hand_bbox_for_wrist(
                self.hand_detector.detect(image),
                wrist_px=side_body["wrist_px"],
                shoulder_width_px=body["shoulder_width_px"],
            )
        crop_box = self.hand_crop_selector.select_crop(
            image_w=image_w,
            image_h=image_h,
            elbow_px=side_body["elbow_px"],
            wrist_px=side_body["wrist_px"],
            hand_bbox=hand_bbox,
        )
        crop_box = self.crop_smoother.update(crop_box)
        hand_results = self.hand_runner.run_crop(image, crop_box)
        hand_result = hand_results[0] if hand_results else None
        result = self.wrist_estimator.estimate(
            elbow_px=side_body["elbow_px"],
            wrist_px=side_body["wrist_px"],
            elbow_conf=side_body["elbow_conf"],
            wrist_conf=side_body["wrist_conf"],
            shoulder_width_px=body["shoulder_width_px"],
            hand_landmarks=(
                None if hand_result is None else hand_result.get("hand_landmarks")
            ),
            hand_world_landmarks=(
                None
                if hand_result is None
                else hand_result.get("hand_world_landmarks")
            ),
            crop_box=crop_box,
            is_right_hand=side == "right",
            current_time_sec=timestamp_sec,
        )
        feedbacks = self.feedback_engine.generate(
            left_result=result if side == "left" else None,
            right_result=result if side == "right" else None,
            current_time_sec=timestamp_sec,
        )
        return {
            "timestamp_sec": timestamp_sec,
            "side": side,
            "crop_box": crop_box,
            "hand_detected": hand_result is not None,
            "bend_valid": result["bend_valid"],
            "bend_angle_2d": result["bend_angle_2d"],
            "bend_risk": result["bend_risk"],
            "bend_state": result["bend_state"],
            "valid": result["valid"],
            "is_held": result["is_held"],
            "hold_duration_sec": result["hold_duration_sec"],
            "global_invalid_reason": result["global_invalid_reason"],
            "feedbacks": feedbacks,
        }

    def reset(self) -> None:
        self.crop_smoother.reset()
        self.wrist_estimator.reset()
        self.feedback_engine.reset()


def _image_size(image):
    if isinstance(image, dict):
        if "image_w" in image and "image_h" in image:
            return int(image["image_w"]), int(image["image_h"])
        if "width" in image and "height" in image:
            return int(image["width"]), int(image["height"])
    shape = getattr(image, "shape", None)
    if shape is not None and len(shape) >= 2:
        return int(shape[1]), int(shape[0])
    raise ValueError("image must provide image_w/image_h, width/height, or shape")
