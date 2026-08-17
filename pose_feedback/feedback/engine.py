from typing import Optional

from pose_feedback.feedback.invalid_reason import INVALID_MESSAGE, resolve_invalid_reason
from pose_feedback.feedback.throttle import FeedbackThrottle


class FeedbackEngine:
    def __init__(self, config):
        self.config = config
        self.throttle = FeedbackThrottle(
            min_interval_seconds=config.feedback_min_interval_seconds,
        )

    def generate(
        self,
        left_result: Optional[dict] = None,
        right_result: Optional[dict] = None,
        symmetry_result: Optional[dict] = None,
        rep_phase: str = "unknown",
        current_time_sec: float = 0.0,
    ) -> list[dict]:
        left_held = bool(left_result and left_result.get("is_held"))
        right_held = bool(right_result and right_result.get("is_held"))
        return self._generate_basic_feedback(
            left_result=left_result,
            right_result=right_result,
            symmetry_result=symmetry_result,
            current_time_sec=current_time_sec,
            allow_left_feedback=left_result is not None and not left_held,
            allow_right_feedback=right_result is not None and not right_held,
            allow_symmetry_feedback=(
                symmetry_result is not None and not left_held and not right_held
            ),
        )

    def _generate_basic_feedback(
        self,
        left_result: Optional[dict],
        right_result: Optional[dict],
        symmetry_result: Optional[dict],
        current_time_sec: float,
        allow_left_feedback: bool,
        allow_right_feedback: bool,
        allow_symmetry_feedback: bool,
    ) -> list[dict]:
        feedbacks = []
        for side, result, allowed in (
            ("left", left_result, allow_left_feedback),
            ("right", right_result, allow_right_feedback),
        ):
            if not allowed or result is None:
                continue
            if not result.get("valid"):
                reason = resolve_invalid_reason(result)
                if reason is not None:
                    feedback_type = f"{side}:invalid:{reason}"
                    if self.throttle.should_fire(feedback_type, current_time_sec):
                        feedbacks.append(
                            {
                                "type": feedback_type,
                                "severity": "info",
                                "message": INVALID_MESSAGE.get(
                                    reason,
                                    "손목 상태를 인식할 수 없습니다.",
                                ),
                            },
                        )
                continue
            if result.get("bend_state") == "bad":
                feedback_type = f"{side}:bend_bad"
                if self.throttle.should_fire(feedback_type, current_time_sec):
                    feedbacks.append(
                        {
                            "type": feedback_type,
                            "severity": "warning",
                            "message": f"{side} 손목이 많이 꺾였습니다.",
                        },
                    )
            if result.get("rotation_state") == "rotated_bad":
                feedback_type = f"{side}:rotation_bad"
                if self.throttle.should_fire(feedback_type, current_time_sec):
                    feedbacks.append(
                        {
                            "type": feedback_type,
                            "severity": "warning",
                            "message": f"{side} 손목 회전이 기준 자세에서 많이 벗어났습니다.",
                        },
                    )
        if allow_symmetry_feedback and symmetry_result is not None:
            if symmetry_result.get("symmetry_state") == "bad":
                feedback_type = "symmetry_bad"
                if self.throttle.should_fire(feedback_type, current_time_sec):
                    feedbacks.append(
                        {
                            "type": feedback_type,
                            "severity": "warning",
                            "message": "좌우 손목 높이가 크게 다릅니다.",
                        },
                    )
        return feedbacks

    def reset(self) -> None:
        self.throttle.reset()
