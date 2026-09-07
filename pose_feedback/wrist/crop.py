from math import sqrt
from typing import Optional, Tuple

from pose_feedback.wrist.geometry import Point2D

CropBox = Tuple[int, int, int, int]


def make_forward_hand_crop_box(
    elbow: Point2D,
    wrist: Point2D,
    image_w: int,
    image_h: int,
    scale: float = 2.2,
    shift: float = 0.45,
) -> CropBox:
    vx = wrist[0] - elbow[0]
    vy = wrist[1] - elbow[1]
    forearm_len = sqrt(vx * vx + vy * vy) + 1e-8
    direction = vx / forearm_len, vy / forearm_len
    center = (
        wrist[0] + direction[0] * forearm_len * shift,
        wrist[1] + direction[1] * forearm_len * shift,
    )
    size = max(96.0, forearm_len * scale)
    x1 = int(round(max(0, center[0] - size / 2)))
    y1 = int(round(max(0, center[1] - size / 2)))
    x2 = int(round(min(image_w, center[0] + size / 2)))
    y2 = int(round(min(image_h, center[1] + size / 2)))
    return x1, y1, x2, y2


class CropBoxSmoother:
    def __init__(self, alpha: float = 0.4):
        self.alpha = alpha
        self.box: Optional[Tuple[float, float, float, float]] = None

    def update(self, box: CropBox) -> CropBox:
        new = tuple(float(v) for v in box)
        if self.box is None:
            self.box = new
        else:
            self.box = tuple(
                self.alpha * new_value + (1.0 - self.alpha) * old_value
                for new_value, old_value in zip(new, self.box)
            )
        return tuple(int(v) for v in self.box)

    def reset(self) -> None:
        self.box = None
