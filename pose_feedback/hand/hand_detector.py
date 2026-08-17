from math import sqrt


class HandDetector:
    def detect(self, image) -> list[dict]:
        raise NotImplementedError("Real hand detector runtime is not connected yet.")


def select_best_hand_bbox_for_wrist(
    detections,
    wrist_px,
    shoulder_width_px=None,
    max_distance_ratio: float = 0.75,
    min_confidence: float = 0.5,
):
    best_bbox = None
    best_distance = None
    for detection in detections:
        confidence = float(detection.get("confidence", 0.0))
        if confidence < min_confidence:
            continue
        bbox = detection.get("bbox")
        if not _valid_bbox(bbox):
            continue
        distance = _bbox_center_distance(bbox, wrist_px)
        if (
            shoulder_width_px is not None
            and shoulder_width_px > 1e-8
            and distance / shoulder_width_px > max_distance_ratio
        ):
            continue
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_bbox = bbox
    return best_bbox


def _valid_bbox(bbox):
    if bbox is None:
        return False
    try:
        if len(bbox) != 4:
            return False
        x1, y1, x2, y2 = (float(value) for value in bbox)
    except (TypeError, ValueError):
        return False
    return x2 > x1 and y2 > y1


def _bbox_center_distance(bbox, wrist_px):
    x1, y1, x2, y2 = (float(value) for value in bbox)
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    dx = cx - float(wrist_px[0])
    dy = cy - float(wrist_px[1])
    return sqrt(dx * dx + dy * dy)
