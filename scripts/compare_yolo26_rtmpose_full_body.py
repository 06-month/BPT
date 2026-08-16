import argparse
from contextlib import contextmanager
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.rtmpose_runner import (
    RTMPoseNoPersonDetectedError,
    RTMPoseRunner,
)
from pose_feedback.body.yolo26_runner import (
    NoPersonDetectedError,
    UltralyticsYOLO26PoseRunner,
)


KEYPOINT_NAMES = [
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

SKELETON = [
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (0, 1),
    (0, 2),
    (1, 3),
    (2, 4),
]

FOCUS_KEYPOINTS = [
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

YOLO_COLOR = (255, 80, 40)
RTMPOSE_COLOR = (40, 40, 255)
LOW_CONF_COLOR = (150, 150, 150)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare YOLO26n-pose and RTMPose-m COCO full-body keypoints.",
    )
    parser.add_argument("--image", default="assets/smoke/pushup.jpg")
    parser.add_argument("--yolo-model", default="models/yolo26n-pose.pt")
    parser.add_argument(
        "--rtmpose-config",
        default="models/rtmpose/rtmpose-m_8xb256-420e_coco-256x192.py",
    )
    parser.add_argument(
        "--rtmpose-checkpoint",
        default="models/rtmpose/rtmpose-m_coco.pth",
    )
    parser.add_argument(
        "--output-overlay",
        default="assets/smoke/compare_yolo26n_rtmpose_overlay.jpg",
    )
    parser.add_argument(
        "--output-side-by-side",
        default="assets/smoke/compare_yolo26n_rtmpose_side_by_side.jpg",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--conf-threshold", type=float, default=0.3)
    parser.add_argument("--marker-scale", type=float, default=0.6)
    return parser.parse_args()


def main():
    args = parse_args()
    image_path = Path(args.image)
    image = read_image(image_path)
    sizes = drawing_sizes(image.shape[1], image.shape[0], args.marker_scale)

    yolo_keypoints, yolo_error = run_yolo(args.yolo_model, image)
    rtmpose_keypoints, rtmpose_error = run_rtmpose(
        args.rtmpose_config,
        args.rtmpose_checkpoint,
        args.device,
        image,
    )

    if yolo_error:
        print(f"YOLO26n-pose unavailable: {yolo_error}")
    if rtmpose_error:
        print(f"RTMPose unavailable: {rtmpose_error}")
    if yolo_keypoints is None and rtmpose_keypoints is None:
        print(
            {
                "image": str(image_path),
                "yolo_body_detected": False,
                "rtmpose_body_detected": False,
                "reason": "both_models_failed",
                "yolo_error": yolo_error,
                "rtmpose_error": rtmpose_error,
            },
        )
        return 0

    overlay_path = Path(args.output_overlay)
    side_by_side_path = Path(args.output_side_by_side)
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    side_by_side_path.parent.mkdir(parents=True, exist_ok=True)

    save_same_image_overlay(
        image=image,
        yolo_keypoints=yolo_keypoints,
        rtmpose_keypoints=rtmpose_keypoints,
        output=overlay_path,
        conf_threshold=args.conf_threshold,
        sizes=sizes,
    )
    save_side_by_side(
        image=image,
        yolo_keypoints=yolo_keypoints,
        rtmpose_keypoints=rtmpose_keypoints,
        output=side_by_side_path,
        conf_threshold=args.conf_threshold,
        sizes=sizes,
        yolo_error=yolo_error,
        rtmpose_error=rtmpose_error,
    )

    comparison, summary = compare_keypoints(
        yolo_keypoints,
        rtmpose_keypoints,
        args.conf_threshold,
    )
    result = {
        "image": str(image_path),
        "yolo_body_detected": yolo_keypoints is not None,
        "rtmpose_body_detected": rtmpose_keypoints is not None,
        "output_overlay": str(overlay_path),
        "output_side_by_side": str(side_by_side_path),
        "mean_distance_px": summary["mean_distance_px"],
        "max_distance_px": summary["max_distance_px"],
        "largest_disagreement_keypoints": summary["largest_disagreement_keypoints"],
        "focus_disagreements": summary["focus_disagreements"],
        "keypoint_comparison": comparison,
    }
    print(result)
    return 0


def read_image(path):
    import cv2

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def run_yolo(model_path, image):
    try:
        runner = UltralyticsYOLO26PoseRunner(model_path=model_path)
        return runner.predict_keypoints(image), None
    except ImportError as exc:
        return None, f"runtime_import_error: {exc}"
    except NoPersonDetectedError as exc:
        return None, f"no_person_detected: {exc}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def run_rtmpose(config_path, checkpoint_path, device, image):
    try:
        with legacy_openmmlab_checkpoint_load():
            runner = RTMPoseRunner(
                pose_config=config_path,
                pose_checkpoint=checkpoint_path,
                device=device,
            )
            return runner.predict_keypoints(image), None
    except ImportError as exc:
        return None, f"runtime_import_error: {exc}"
    except RTMPoseNoPersonDetectedError as exc:
        return None, f"no_person_detected: {exc}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


@contextmanager
def legacy_openmmlab_checkpoint_load():
    try:
        import torch
    except Exception:
        yield
        return

    original_load = torch.load

    def load_with_legacy_default(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)

    torch.load = load_with_legacy_default
    try:
        yield
    finally:
        torch.load = original_load


def drawing_sizes(image_w, image_h, marker_scale):
    base = max(1.0, min(image_w, image_h) / 300.0)
    return {
        "radius": max(2, int(3 * base * marker_scale)),
        "line": max(1, int(2 * base * marker_scale)),
        "font": max(0.35, 0.42 * base * marker_scale),
        "title_font": max(0.45, 0.55 * base * marker_scale),
        "text": max(1, int(1 * base * marker_scale)),
    }


def save_same_image_overlay(
    image,
    yolo_keypoints,
    rtmpose_keypoints,
    output,
    conf_threshold,
    sizes,
):
    import cv2

    overlay = image.copy()
    if yolo_keypoints is not None:
        draw_pose(
            overlay,
            yolo_keypoints,
            label_prefix="Y",
            color=YOLO_COLOR,
            conf_threshold=conf_threshold,
            sizes=sizes,
            label_offset=(4, -4),
        )
    if rtmpose_keypoints is not None:
        draw_pose(
            overlay,
            rtmpose_keypoints,
            label_prefix="R",
            color=RTMPOSE_COLOR,
            conf_threshold=conf_threshold,
            sizes=sizes,
            label_offset=(4, 12),
        )
    draw_legend(overlay, sizes)
    cv2.imwrite(str(output), overlay)


def save_side_by_side(
    image,
    yolo_keypoints,
    rtmpose_keypoints,
    output,
    conf_threshold,
    sizes,
    yolo_error,
    rtmpose_error,
):
    import cv2

    left = image.copy()
    right = image.copy()
    if yolo_keypoints is not None:
        draw_pose(left, yolo_keypoints, "Y", YOLO_COLOR, conf_threshold, sizes)
    else:
        draw_status(left, "YOLO failed", yolo_error or "no result", sizes)
    if rtmpose_keypoints is not None:
        draw_pose(right, rtmpose_keypoints, "R", RTMPOSE_COLOR, conf_threshold, sizes)
    else:
        draw_status(right, "RTMPose failed", rtmpose_error or "no result", sizes)
    draw_panel_title(left, "YOLO26n-pose", YOLO_COLOR, sizes)
    draw_panel_title(right, "RTMPose-m", RTMPOSE_COLOR, sizes)
    combined = cv2.hconcat([left, right])
    cv2.imwrite(str(output), combined)


def draw_pose(
    image,
    keypoints,
    label_prefix,
    color,
    conf_threshold,
    sizes,
    label_offset=(4, -4),
):
    import cv2

    for a, b in SKELETON:
        if confidence(keypoints, a) < conf_threshold or confidence(keypoints, b) < conf_threshold:
            continue
        cv2.line(
            image,
            point_to_int(keypoints[a]),
            point_to_int(keypoints[b]),
            color,
            sizes["line"],
            cv2.LINE_AA,
        )
    for index, name in enumerate(KEYPOINT_NAMES):
        conf = confidence(keypoints, index)
        if conf < conf_threshold:
            continue
        point = point_to_int(keypoints[index])
        cv2.circle(image, point, sizes["radius"], color, -1)
        cv2.circle(image, point, sizes["radius"] + 1, WHITE, 1)
        label = f"{label_prefix}{index} {short_name(name)}"
        cv2.putText(
            image,
            label,
            (point[0] + label_offset[0], point[1] + label_offset[1]),
            cv2.FONT_HERSHEY_SIMPLEX,
            sizes["font"],
            color,
            sizes["text"],
            cv2.LINE_AA,
        )


def draw_legend(image, sizes):
    import cv2

    lines = ["blue = YOLO26n-pose", "red = RTMPose"]
    x, y = 8, 8
    line_h = max(16, int(24 * sizes["font"]))
    width = max(190, int(260 * sizes["font"]))
    height = line_h * len(lines) + 12
    draw_translucent_box(image, (x, y, x + width, y + height), alpha=0.58)
    for row, text in enumerate(lines):
        color = YOLO_COLOR if row == 0 else RTMPOSE_COLOR
        cv2.putText(
            image,
            text,
            (x + 8, y + 16 + row * line_h),
            cv2.FONT_HERSHEY_SIMPLEX,
            sizes["font"],
            color,
            sizes["text"],
            cv2.LINE_AA,
        )


def draw_panel_title(image, title, color, sizes):
    import cv2

    x, y = 8, 8
    width = max(170, int(len(title) * 16 * sizes["title_font"]))
    height = max(26, int(36 * sizes["title_font"]))
    draw_translucent_box(image, (x, y, x + width, y + height), alpha=0.58)
    cv2.putText(
        image,
        title,
        (x + 8, y + height - 8),
        cv2.FONT_HERSHEY_SIMPLEX,
        sizes["title_font"],
        color,
        sizes["text"],
        cv2.LINE_AA,
    )


def draw_status(image, title, message, sizes):
    import cv2

    h, w = image.shape[:2]
    x1, y1 = 8, max(40, h // 2 - 35)
    x2, y2 = min(w - 8, x1 + 360), min(h - 8, y1 + 80)
    draw_translucent_box(image, (x1, y1, x2, y2), alpha=0.65)
    cv2.putText(
        image,
        title,
        (x1 + 8, y1 + 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        sizes["title_font"],
        (80, 80, 255),
        sizes["text"],
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        str(message)[:70],
        (x1 + 8, y1 + 52),
        cv2.FONT_HERSHEY_SIMPLEX,
        sizes["font"],
        WHITE,
        sizes["text"],
        cv2.LINE_AA,
    )


def draw_translucent_box(image, box, alpha=0.5):
    import cv2

    x1, y1, x2, y2 = [int(v) for v in box]
    patch = image.copy()
    cv2.rectangle(patch, (x1, y1), (x2, y2), BLACK, -1)
    cv2.addWeighted(patch, alpha, image, 1.0 - alpha, 0, image)


def compare_keypoints(yolo_keypoints, rtmpose_keypoints, conf_threshold):
    comparison = {}
    distances = []
    focus = {}
    if yolo_keypoints is None or rtmpose_keypoints is None:
        for name in KEYPOINT_NAMES:
            comparison[name] = {
                "yolo": keypoint_tuple(yolo_keypoints, name),
                "rtmpose": keypoint_tuple(rtmpose_keypoints, name),
                "distance_px": None,
            }
        return comparison, {
            "mean_distance_px": None,
            "max_distance_px": None,
            "largest_disagreement_keypoints": [],
            "focus_disagreements": {name: None for name in FOCUS_KEYPOINTS},
        }

    for index, name in enumerate(KEYPOINT_NAMES):
        yolo = keypoint_tuple(yolo_keypoints, name)
        rtmpose = keypoint_tuple(rtmpose_keypoints, name)
        distance = None
        if yolo[2] >= conf_threshold and rtmpose[2] >= conf_threshold:
            distance = point_distance(yolo, rtmpose)
            distances.append((name, distance))
        comparison[name] = {
            "yolo": yolo,
            "rtmpose": rtmpose,
            "distance_px": distance,
        }
        if name in FOCUS_KEYPOINTS:
            focus[name] = distance

    distance_values = [item[1] for item in distances]
    largest = sorted(distances, key=lambda item: item[1], reverse=True)[:5]
    return comparison, {
        "mean_distance_px": (
            float(sum(distance_values) / len(distance_values))
            if distance_values else None
        ),
        "max_distance_px": float(max(distance_values)) if distance_values else None,
        "largest_disagreement_keypoints": [
            {"name": name, "distance_px": float(distance)}
            for name, distance in largest
        ],
        "focus_disagreements": {
            name: (None if focus.get(name) is None else float(focus[name]))
            for name in FOCUS_KEYPOINTS
        },
    }


def keypoint_tuple(keypoints, name):
    if keypoints is None:
        return None
    index = KEYPOINT_NAMES.index(name)
    return (
        float(keypoints[index][0]),
        float(keypoints[index][1]),
        float(keypoints[index][2]),
    )


def point_distance(a, b):
    return float(math.hypot(a[0] - b[0], a[1] - b[1]))


def confidence(keypoints, index):
    return float(keypoints[index][2])


def point_to_int(row):
    return int(round(float(row[0]))), int(round(float(row[1])))


def short_name(name):
    return (
        name.replace("left_", "L_")
        .replace("right_", "R_")
        .replace("shoulder", "sho")
        .replace("elbow", "elb")
        .replace("wrist", "wri")
        .replace("ankle", "ank")
        .replace("knee", "kne")
    )


if __name__ == "__main__":
    raise SystemExit(main())
