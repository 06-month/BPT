from pose_feedback.wrist.crop import make_forward_hand_crop_box


class HandCropSelector:
    def __init__(
        self,
        margin_ratio: float = 0.25,
        fallback_scale: float = 2.2,
        fallback_shift: float = 0.45,
    ):
        self.margin_ratio = margin_ratio
        self.fallback_scale = fallback_scale
        self.fallback_shift = fallback_shift

    def select_crop(
        self,
        image_w,
        image_h,
        elbow_px,
        wrist_px,
        hand_bbox=None,
    ):
        if hand_bbox is None:
            return make_forward_hand_crop_box(
                elbow=elbow_px,
                wrist=wrist_px,
                image_w=image_w,
                image_h=image_h,
                scale=self.fallback_scale,
                shift=self.fallback_shift,
            )
        x1, y1, x2, y2 = _validate_bbox(hand_bbox)
        width = x2 - x1
        height = y2 - y1
        margin = max(width, height) * self.margin_ratio
        return (
            int(max(0, x1 - margin)),
            int(max(0, y1 - margin)),
            int(min(image_w, x2 + margin)),
            int(min(image_h, y2 + margin)),
        )


def _validate_bbox(hand_bbox):
    if len(hand_bbox) != 4:
        raise ValueError("hand_bbox must be (x1, y1, x2, y2)")
    x1, y1, x2, y2 = (float(value) for value in hand_bbox)
    if x2 < x1 or y2 < y1:
        raise ValueError("hand_bbox coordinates must satisfy x1 <= x2 and y1 <= y2")
    if x2 == x1 or y2 == y1:
        raise ValueError("hand_bbox must have non-zero area")
    return x1, y1, x2, y2
