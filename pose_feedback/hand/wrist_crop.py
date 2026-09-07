from dataclasses import asdict, dataclass
from math import isfinite
from typing import Optional, Sequence, Tuple


CropBox = Tuple[int, int, int, int]


@dataclass(frozen=True)
class WristHandCrop:
    side: str
    x1: int
    y1: int
    x2: int
    y2: int
    image_width: int
    image_height: int
    wrist_confidence: Optional[float] = None

    @property
    def crop_box(self) -> CropBox:
        return self.x1, self.y1, self.x2, self.y2

    @property
    def crop_width(self) -> int:
        return self.x2 - self.x1

    @property
    def crop_height(self) -> int:
        return self.y2 - self.y1

    def to_dict(self) -> dict:
        data = asdict(self)
        data["crop_width"] = self.crop_width
        data["crop_height"] = self.crop_height
        return data


def build_wrist_hand_crop(
    frame_shape,
    wrist_xy,
    crop_size: int,
    side: str,
    confidence: Optional[float] = None,
    confidence_threshold: float = 0.3,
) -> Optional[WristHandCrop]:
    """Build a clamped square-ish hand crop centered on an RTMPose wrist."""
    image_h, image_w = _frame_hw(frame_shape)
    if crop_size <= 0:
        raise ValueError("crop_size must be positive")
    if side not in ("left", "right"):
        raise ValueError('side must be "left" or "right"')
    if confidence is not None and float(confidence) < confidence_threshold:
        return None

    cx, cy = _point_xy(wrist_xy)
    if not all(isfinite(value) for value in (cx, cy)):
        return None

    half = float(crop_size) * 0.5
    x1 = int(round(cx - half))
    y1 = int(round(cy - half))
    x2 = int(round(cx + half))
    y2 = int(round(cy + half))

    x1 = max(0, min(image_w, x1))
    y1 = max(0, min(image_h, y1))
    x2 = max(0, min(image_w, x2))
    y2 = max(0, min(image_h, y2))
    if x2 <= x1 or y2 <= y1:
        return None

    return WristHandCrop(
        side=side,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        image_width=image_w,
        image_height=image_h,
        wrist_confidence=None if confidence is None else float(confidence),
    )


def crop_frame(frame, crop: WristHandCrop):
    x1, y1, x2, y2 = crop.crop_box
    try:
        return frame[y1:y2, x1:x2]
    except TypeError:
        return [row[x1:x2] for row in frame[y1:y2]]


def map_crop_landmarks_to_frame(landmarks, crop: WristHandCrop):
    """Map normalized crop-local MediaPipe landmarks to frame pixel coordinates."""
    mapped = []
    for landmark in _landmark_sequence(landmarks):
        mapped.append(
            [
                float(crop.x1 + landmark.x * crop.crop_width),
                float(crop.y1 + landmark.y * crop.crop_height),
                float(getattr(landmark, "z", 0.0)),
            ],
        )
    return mapped


def crop_metadata_from_box(
    crop_box: CropBox,
    frame_shape,
    side: str,
    confidence: Optional[float] = None,
) -> WristHandCrop:
    image_h, image_w = _frame_hw(frame_shape)
    x1, y1, x2, y2 = (int(value) for value in crop_box)
    return WristHandCrop(
        side=side,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        image_width=image_w,
        image_height=image_h,
        wrist_confidence=None if confidence is None else float(confidence),
    )


def _frame_hw(frame_shape) -> Tuple[int, int]:
    if len(frame_shape) < 2:
        raise ValueError("frame_shape must include height and width")
    image_h = int(frame_shape[0])
    image_w = int(frame_shape[1])
    if image_w <= 0 or image_h <= 0:
        raise ValueError("frame shape must have positive width and height")
    return image_h, image_w


def _point_xy(point: Sequence[float]) -> Tuple[float, float]:
    if point is None or len(point) < 2:
        raise ValueError("wrist_xy must contain x and y")
    return float(point[0]), float(point[1])


def _landmark_sequence(landmarks):
    return getattr(landmarks, "landmark", landmarks)
