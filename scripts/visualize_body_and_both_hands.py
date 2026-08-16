import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.body_adapter import coco_yolo_keypoints_to_body
from pose_feedback.body.yolo26_runner import (
    NoPersonDetectedError,
    UltralyticsYOLO26PoseRunner,
)
from pose_feedback.config import PUSHUP_SIDE_CONFIG
from pose_feedback.hand.hand_crop_selector import HandCropSelector
from pose_feedback.hand.mediapipe_hand_runner import (
    MediaPipeHandsRuntimeError,
    MediaPipeHandsRunner,
)
from pose_feedback.wrist.crop import CropBoxSmoother
from pose_feedback.wrist.estimator import WristEstimator
from pose_feedback.wrist.geometry import crop_to_image_coords, palm_normal_from_world


KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]
BODY_SKELETON = [
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12), (11, 13), (13, 15),
    (12, 14), (14, 16), (0, 1), (0, 2), (1, 3), (2, 4),
]
LEFT_BODY = {1, 3, 5, 7, 9, 11, 13, 15}
RIGHT_BODY = {2, 4, 6, 8, 10, 12, 14, 16}

HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
)
FINGER_CHAINS = {
    "thumb": ((0, 1), (1, 2), (2, 3), (3, 4)),
    "index": ((0, 5), (5, 6), (6, 7), (7, 8)),
    "middle": ((0, 9), (9, 10), (10, 11), (11, 12)),
    "ring": ((0, 13), (13, 14), (14, 15), (15, 16)),
    "pinky": ((0, 17), (17, 18), (18, 19), (19, 20)),
    "palm": ((5, 9), (9, 13), (13, 17)),
}


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize body and both hand crops.")
    parser.add_argument("--model", required=True, help="Path to YOLO26 pose model.")
    parser.add_argument("--image", required=True, help="Path to input image.")
    parser.add_argument("--output-2d", required=True, help="Path for 2D overlay.")
    parser.add_argument("--output-left-3d", required=True, help="Path for left hand 3D plot.")
    parser.add_argument("--output-right-3d", required=True, help="Path for right hand 3D plot.")
    parser.add_argument("--conf-threshold", type=float, default=0.3)
    parser.add_argument("--marker-scale", type=float, default=1.0)
    return parser.parse_args()


def read_image(path):
    import cv2

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def main():
    args = parse_args()
    image = read_image(Path(args.image))
    image_h, image_w = image.shape[:2]
    config = PUSHUP_SIDE_CONFIG

    try:
        runner = UltralyticsYOLO26PoseRunner(model_path=args.model)
        keypoints = runner.predict_keypoints(image)
    except ImportError as exc:
        print({"body_detected": False, "yolo_runtime": "unavailable", "reason": str(exc)})
        return 0
    except NoPersonDetectedError as exc:
        print({"body_detected": False, "reason": str(exc)})
        return 0

    body = coco_yolo_keypoints_to_body(keypoints)
    crop_selector = HandCropSelector()
    smoothers = {
        "left": CropBoxSmoother(alpha=config.crop_smoothing_alpha),
        "right": CropBoxSmoother(alpha=config.crop_smoothing_alpha),
    }
    estimators = {"left": WristEstimator(config), "right": WristEstimator(config)}
    hand_runner = create_hand_runner()

    side_results = {}
    for side in ("left", "right"):
        side_results[side] = process_side(
            side=side,
            image=image,
            image_w=image_w,
            image_h=image_h,
            body=body,
            crop_selector=crop_selector,
            smoother=smoothers[side],
            estimator=estimators[side],
            hand_runner=hand_runner,
        )

    if hand_runner is not None:
        hand_runner.close()

    output_2d = Path(args.output_2d)
    output_2d.parent.mkdir(parents=True, exist_ok=True)
    sizes = drawing_sizes(image_w, image_h, args.marker_scale)
    save_2d_overlay(
        image=image,
        keypoints=keypoints,
        body=body,
        side_results=side_results,
        output_path=output_2d,
        conf_threshold=args.conf_threshold,
        sizes=sizes,
    )

    left_3d = save_side_3d_if_available(
        side_results["left"],
        Path(args.output_left_3d),
        is_right_hand=False,
    )
    right_3d = save_side_3d_if_available(
        side_results["right"],
        Path(args.output_right_3d),
        is_right_hand=True,
    )

    print(
        {
            "body_detected": True,
            "output_2d": str(output_2d),
            "output_left_3d": left_3d,
            "output_right_3d": right_3d,
            "left": compact_side_result(side_results["left"]),
            "right": compact_side_result(side_results["right"]),
        },
    )
    return 0


def create_hand_runner():
    try:
        return MediaPipeHandsRunner(
            static_image_mode=True,
            max_num_hands=1,
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3,
            cpu_only=True,
            input_color_format="BGR",
        )
    except (ImportError, MediaPipeHandsRuntimeError) as exc:
        print({"mediapipe_runtime": "unavailable", "reason": str(exc)})
        return None
    except Exception as exc:
        print({"mediapipe_runtime": "failed", "reason": str(exc)})
        return None


def process_side(
    side,
    image,
    image_w,
    image_h,
    body,
    crop_selector,
    smoother,
    estimator,
    hand_runner,
):
    side_body = body[side]
    crop_box = crop_selector.select_crop(
        image_w=image_w,
        image_h=image_h,
        elbow_px=side_body["elbow_px"],
        wrist_px=side_body["wrist_px"],
        hand_bbox=None,
    )
    crop_box = smoother.update(crop_box)
    hand_results = []
    if hand_runner is not None:
        try:
            hand_results = hand_runner.run_crop(image, crop_box)
        except Exception as exc:
            print({"side": side, "hand_runtime": "failed", "reason": str(exc)})
    hand_result = hand_results[0] if hand_results else None
    estimate = estimator.estimate(
        elbow_px=side_body["elbow_px"],
        wrist_px=side_body["wrist_px"],
        elbow_conf=side_body["elbow_conf"],
        wrist_conf=side_body["wrist_conf"],
        shoulder_width_px=body["shoulder_width_px"],
        hand_landmarks=None if hand_result is None else hand_result["hand_landmarks"],
        hand_world_landmarks=None if hand_result is None else hand_result["hand_world_landmarks"],
        crop_box=crop_box,
        is_right_hand=side == "right",
        current_time_sec=0.0,
    )
    return {"side": side, "crop_box": crop_box, "hand_result": hand_result, "estimate": estimate}


def drawing_sizes(image_w, image_h, marker_scale):
    base = max(1.0, min(image_w, image_h) / 300.0)
    return {
        "body_radius": max(2, int(3 * base * marker_scale)),
        "hand_radius": max(1, int(2 * base * marker_scale)),
        "highlight_radius": max(3, int(4 * base * marker_scale)),
        "line_thickness": max(1, int(2 * base * marker_scale)),
        "font_scale": max(0.35, 0.45 * base * marker_scale),
        "text_thickness": max(1, int(1 * base * marker_scale)),
    }


def save_2d_overlay(image, keypoints, body, side_results, output_path, conf_threshold, sizes):
    import cv2

    overlay = image.copy()
    draw_body(overlay, keypoints, conf_threshold, sizes)
    for side, color in (("left", (255, 255, 0)), ("right", (255, 0, 255))):
        draw_side_hand(overlay, body[side], side_results[side], color, sizes)
    draw_text_summary(overlay, side_results, sizes)
    cv2.imwrite(str(output_path), overlay)


def draw_body(image, keypoints, conf_threshold, sizes):
    import cv2

    for a, b in BODY_SKELETON:
        if conf(keypoints, a) < conf_threshold or conf(keypoints, b) < conf_threshold:
            continue
        cv2.line(
            image,
            point_to_int(keypoints[a]),
            point_to_int(keypoints[b]),
            body_color(a, b),
            sizes["line_thickness"],
            cv2.LINE_AA,
        )
    for idx, name in enumerate(KEYPOINT_NAMES):
        point = point_to_int(keypoints[idx])
        if conf(keypoints, idx) < conf_threshold:
            cv2.circle(image, point, sizes["body_radius"], (150, 150, 150), 1)
            continue
        color = body_keypoint_color(idx)
        cv2.circle(image, point, sizes["body_radius"], color, -1)


def draw_side_hand(image, side_body, side_result, crop_color, sizes):
    import cv2

    crop_box = side_result["crop_box"]
    x1, y1, x2, y2 = crop_box
    cv2.rectangle(image, (x1, y1), (x2, y2), crop_color, sizes["line_thickness"])
    cv2.putText(
        image,
        f"{side_result['side']} crop",
        (x1 + 3, max(12, y1 - 4)),
        cv2.FONT_HERSHEY_SIMPLEX,
        sizes["font_scale"],
        crop_color,
        sizes["text_thickness"],
        cv2.LINE_AA,
    )

    hand_result = side_result["hand_result"]
    if hand_result is None or hand_result["hand_landmarks"] is None:
        return

    points = hand_landmarks_to_image_points(hand_result["hand_landmarks"], crop_box)
    for a, b in HAND_CONNECTIONS:
        cv2.line(
            image,
            point_to_int(points[a]),
            point_to_int(points[b]),
            (0, 180, 0),
            sizes["line_thickness"],
            cv2.LINE_AA,
        )
    for idx, point in enumerate(points):
        color = (0, 180, 0)
        radius = sizes["hand_radius"]
        if idx in (0, 5, 9, 17):
            color = (0, 90, 255)
            radius = sizes["highlight_radius"]
        cv2.circle(image, point_to_int(point), radius, color, -1)

    elbow = point_to_int(side_body["elbow_px"])
    wrist = point_to_int(side_body["wrist_px"])
    middle_mcp = point_to_int(points[9])
    cv2.arrowedLine(image, elbow, wrist, (255, 255, 0), sizes["line_thickness"] + 1, tipLength=0.08)
    cv2.arrowedLine(image, wrist, middle_mcp, (255, 0, 255), sizes["line_thickness"] + 1, tipLength=0.08)


def draw_text_summary(image, side_results, sizes):
    import cv2

    lines = [
        "body_detected: True",
        f"left hand_detected: {side_results['left']['hand_result'] is not None}",
        f"left bend_angle_2d: {fmt(side_results['left']['estimate']['bend_angle_2d'])}",
        f"left bend_state: {side_results['left']['estimate']['bend_state']}",
        f"right hand_detected: {side_results['right']['hand_result'] is not None}",
        f"right bend_angle_2d: {fmt(side_results['right']['estimate']['bend_angle_2d'])}",
        f"right bend_state: {side_results['right']['estimate']['bend_state']}",
    ]
    line_height = max(14, int(18 * sizes["font_scale"] / 0.45))
    width = min(image.shape[1] - 8, 380)
    height = line_height * len(lines) + 10
    avoid = [side_results["left"]["crop_box"], side_results["right"]["crop_box"]]
    x0, y0 = choose_text_origin(image, width, height, avoid)
    roi = image[y0:y0 + height, x0:x0 + width]
    black = roi.copy()
    black[:] = (0, 0, 0)
    cv2.addWeighted(black, 0.68, roi, 0.32, 0, dst=roi)
    y = y0 + line_height
    for line in lines:
        cv2.putText(
            image,
            line,
            (x0 + 6, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            sizes["font_scale"],
            (255, 255, 255),
            sizes["text_thickness"],
            cv2.LINE_AA,
        )
        y += line_height


def save_side_3d_if_available(side_result, output_path, is_right_hand):
    hand_result = side_result["hand_result"]
    if hand_result is None or hand_result["hand_world_landmarks"] is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_3d_hand_world_plot(hand_result["hand_world_landmarks"], output_path, is_right_hand)
    return str(output_path)


def save_3d_hand_world_plot(hand_world_landmarks, output_path, is_right_hand):
    os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mplconfig")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    points = np.array([[lm.x, lm.y, lm.z] for lm in hand_world_landmarks.landmark], dtype=float)
    fig = plt.figure(figsize=(8, 7), dpi=180)
    ax = fig.add_subplot(111, projection="3d")
    chain_colors = {
        "thumb": "tab:orange", "index": "tab:blue", "middle": "tab:green",
        "ring": "tab:purple", "pinky": "tab:brown", "palm": "gray",
    }
    for chain, connections in FINGER_CHAINS.items():
        for a, b in connections:
            segment = points[[a, b]]
            ax.plot(segment[:, 0], segment[:, 1], segment[:, 2], color=chain_colors[chain], linewidth=2.6)
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], c="tab:blue", s=20)
    for idx, label in {0: "wrist", 5: "index_mcp", 9: "middle_mcp", 17: "pinky_mcp"}.items():
        ax.scatter(points[idx, 0], points[idx, 1], points[idx, 2], c="red", s=85)
        ax.text(points[idx, 0], points[idx, 1], points[idx, 2], label)
    normal = palm_normal_from_world(hand_world_landmarks, is_right_hand=is_right_hand)
    palm_center = points[[0, 5, 17]].mean(axis=0)
    ax.quiver(palm_center[0], palm_center[1], palm_center[2], normal[0], normal[1], normal[2], length=0.08, color="green")
    set_equalish_axes(ax, points)
    ax.view_init(elev=22, azim=-62)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def set_equalish_axes(ax, points):
    import numpy as np

    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    centers = (mins + maxs) / 2.0
    radius = float(np.max(maxs - mins) / 2.0)
    if radius <= 1e-8:
        radius = 0.1
    ax.set_xlim(centers[0] - radius, centers[0] + radius)
    ax.set_ylim(centers[1] - radius, centers[1] + radius)
    ax.set_zlim(centers[2] - radius, centers[2] + radius)


def hand_landmarks_to_image_points(hand_landmarks, crop_box):
    x1, y1, x2, y2 = crop_box
    return [crop_to_image_coords(lm, x1, y1, x2, y2) for lm in hand_landmarks.landmark]


def compact_side_result(side_result):
    estimate = side_result["estimate"]
    return {
        "hand_detected": side_result["hand_result"] is not None,
        "crop_box": side_result["crop_box"],
        "bend_angle_2d": estimate["bend_angle_2d"],
        "bend_state": estimate["bend_state"],
    }


def body_keypoint_color(index):
    if index in LEFT_BODY:
        return (255, 0, 0)
    if index in RIGHT_BODY:
        return (0, 165, 255)
    return (0, 200, 0)


def body_color(a, b):
    if a in LEFT_BODY and b in LEFT_BODY:
        return (255, 0, 0)
    if a in RIGHT_BODY and b in RIGHT_BODY:
        return (0, 165, 255)
    return (0, 200, 0)


def conf(keypoints, index):
    return float(keypoints[index][2])


def point_to_int(point):
    return int(round(float(point[0]))), int(round(float(point[1])))


def choose_text_origin(image, width, height, avoid_boxes):
    image_h, image_w = image.shape[:2]
    candidates = [
        (4, 4),
        (max(4, image_w - width - 4), 4),
        (4, max(4, image_h - height - 4)),
        (max(4, image_w - width - 4), max(4, image_h - height - 4)),
    ]
    for candidate in candidates:
        box = (candidate[0], candidate[1], candidate[0] + width, candidate[1] + height)
        if all(not boxes_overlap(box, avoid) for avoid in avoid_boxes):
            return candidate
    return candidates[0]


def boxes_overlap(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def fmt(value):
    if value is None:
        return "None"
    return f"{float(value):.1f}"


if __name__ == "__main__":
    raise SystemExit(main())
