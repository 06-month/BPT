from typing import Optional

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


def resolve_invalid_reason(result: dict) -> Optional[str]:
    reasons = []
    for key in (
        "global_invalid_reason",
        "rotation_invalid_reason",
        "bend_invalid_reason",
        "invalid_reason",
    ):
        reason = result.get(key)
        if reason is not None:
            reasons.append(reason)
    if not reasons:
        return None
    for priority_reason in INVALID_PRIORITY:
        if priority_reason in reasons:
            return priority_reason
    return reasons[0]
