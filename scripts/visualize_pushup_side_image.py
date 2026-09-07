import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    parser = argparse.ArgumentParser(description="Visualize one pushup_side image.")
    parser.add_argument("--model", required=True, help="Path to YOLO26 pose model.")
    parser.add_argument("--image", required=True, help="Path to input image.")
    parser.add_argument(
        "--side",
        default="left",
        choices=("left", "right"),
        help="Visible side to evaluate.",
    )
    parser.add_argument(
        "--output-2d",
        default="assets/smoke/pushup_side_overlay_2d.jpg",
        help="Path for the 2D overlay image.",
    )
    parser.add_argument(
        "--output-3d",
        default="assets/smoke/pushup_side_hand_world_3d.png",
        help="Path for the 3D hand world plot.",
    )
    parser.add_argument(
        "--save-debug-crop",
        help="Optional path for the exact crop image passed to MediaPipeHandsRunner.",
    )
    return parser.parse_args()


def read_image(path):
    import cv2

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Could not read image: {path}")
    return image


def point_to_tuple(point):
    if point is None:
        return None
    return tuple(float(value) for value in point)


def point_to_int(point):
    return int(round(float(point[0]))), int(round(float(point[1])))


def main():
    args = parse_args()
    image = read_image(Path(args.image))
    image_h, image_w = image.shape[:2]
    config = PUSHUP_SIDE_CONFIG

    try:
        body_runner = UltralyticsYOLO26PoseRunner(model_path=args.model)
        body = body_runner.predict_body(image)
    except ImportError as exc:
        print({"body_detected": False, "yolo_runtime": "unavailable", "reason": str(exc)})
        return 0
    except NoPersonDetectedError as exc:
        print({"body_detected": False, "reason": str(exc)})
        return 0

    side_body = body[args.side]
    crop_selector = HandCropSelector()
    crop_smoother = CropBoxSmoother(alpha=config.crop_smoothing_alpha)
    crop_box = crop_selector.select_crop(
        image_w=image_w,
        image_h=image_h,
        elbow_px=side_body["elbow_px"],
        wrist_px=side_body["wrist_px"],
        hand_bbox=None,
    )
    crop_box = crop_smoother.update(crop_box)
    debug_crop_path = None
    if args.save_debug_crop:
        debug_crop_path = Path(args.save_debug_crop)
        debug_crop_path.parent.mkdir(parents=True, exist_ok=True)
        save_crop_image(image, crop_box, debug_crop_path)

    hand_results = []
    mediapipe_runtime = "available"
    try:
        hand_runner = MediaPipeHandsRunner(
            static_image_mode=True,
            max_num_hands=1,
            min_detection_confidence=0.3,
            min_tracking_confidence=0.3,
            cpu_only=True,
            input_color_format="BGR",
        )
        try:
            hand_results = hand_runner.run_crop(image, crop_box)
        finally:
            hand_runner.close()
    except (ImportError, MediaPipeHandsRuntimeError) as exc:
        mediapipe_runtime = "unavailable"
        print({"mediapipe_runtime": mediapipe_runtime, "reason": str(exc)})
    except Exception as exc:
        mediapipe_runtime = "failed"
        print({"mediapipe_runtime": mediapipe_runtime, "reason": str(exc)})

    hand_result = hand_results[0] if hand_results else None
    estimator = WristEstimator(config)
    result = estimator.estimate(
        elbow_px=side_body["elbow_px"],
        wrist_px=side_body["wrist_px"],
        elbow_conf=side_body["elbow_conf"],
        wrist_conf=side_body["wrist_conf"],
        shoulder_width_px=body["shoulder_width_px"],
        hand_landmarks=None if hand_result is None else hand_result["hand_landmarks"],
        hand_world_landmarks=(
            None if hand_result is None else hand_result["hand_world_landmarks"]
        ),
        crop_box=crop_box,
        is_right_hand=args.side == "right",
        current_time_sec=0.0,
    )

    output_2d = Path(args.output_2d)
    output_2d.parent.mkdir(parents=True, exist_ok=True)
    save_2d_overlay(
        image=image,
        output_path=output_2d,
        side=args.side,
        side_body=side_body,
        crop_box=crop_box,
        hand_result=hand_result,
        estimator_result=result,
    )

    output_3d = None
    if hand_result is not None and hand_result["hand_world_landmarks"] is not None:
        output_3d_path = Path(args.output_3d)
        output_3d_path.parent.mkdir(parents=True, exist_ok=True)
        save_3d_hand_world_plot(
            hand_world_landmarks=hand_result["hand_world_landmarks"],
            output_path=output_3d_path,
            is_right_hand=args.side == "right",
        )
        output_3d = str(output_3d_path)
    else:
        print({"hand_world_3d": "unavailable", "reason": "no_hand_world_landmarks"})

    print(
        {
            "body_detected": True,
            "side": args.side,
            "shoulder_width_px": body["shoulder_width_px"],
            "crop_box": crop_box,
            "hand_detected": hand_result is not None,
            "handedness": None if hand_result is None else hand_result["handedness"],
            "mediapipe_wrist_px": (
                None if hand_result is None else point_to_tuple(hand_result["wrist_px"])
            ),
            "bend_angle_2d": result["bend_angle_2d"],
            "bend_risk": result["bend_risk"],
            "bend_state": result["bend_state"],
            "valid": result["valid"],
            "global_invalid_reason": result["global_invalid_reason"],
            "output_2d": str(output_2d),
            "output_3d": output_3d,
            "debug_crop": None if debug_crop_path is None else str(debug_crop_path),
            "mediapipe_runtime": mediapipe_runtime,
        },
    )
    return 0


def save_2d_overlay(
    image,
    output_path,
    side,
    side_body,
    crop_box,
    hand_result,
    estimator_result,
):
    import cv2

    overlay = image.copy()
    x1, y1, x2, y2 = crop_box
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 255, 255), 4)
    cv2.putText(
        overlay,
        "selected crop_box",
        (x1 + 4, max(15, y1 - 6)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 255),
        1,
        cv2.LINE_AA,
    )

    shoulder = point_to_int(side_body["shoulder_px"])
    elbow = point_to_int(side_body["elbow_px"])
    wrist = point_to_int(side_body["wrist_px"])
    yolo_color = (255, 0, 0)
    cv2.line(overlay, shoulder, elbow, yolo_color, 4)
    cv2.line(overlay, elbow, wrist, yolo_color, 4)
    draw_point(overlay, shoulder, yolo_color, "Y shoulder", radius=9, thickness=2)
    draw_point(overlay, elbow, yolo_color, "Y elbow", radius=9, thickness=2)
    draw_point(overlay, wrist, yolo_color, "Y wrist", radius=9, thickness=2)

    mp_wrist_text = "None"
    middle_mcp_text = "None"
    if hand_result is not None and hand_result["hand_landmarks"] is not None:
        points = hand_landmarks_to_image_points(
            hand_result["hand_landmarks"],
            crop_box,
        )
        for a, b in HAND_CONNECTIONS:
            cv2.line(overlay, point_to_int(points[a]), point_to_int(points[b]), (0, 190, 0), 3)
        for idx, point in enumerate(points):
            color = (0, 180, 0)
            radius = 4
            if idx in (0, 5, 9, 17):
                color = (0, 80, 255)
                radius = 8
            cv2.circle(overlay, point_to_int(point), radius, color, -1)
        mp_wrist = point_to_int(hand_result["wrist_px"])
        middle_mcp = point_to_int(points[9])
        cv2.arrowedLine(overlay, elbow, wrist, (255, 255, 0), 5, tipLength=0.08)
        cv2.arrowedLine(overlay, wrist, middle_mcp, (255, 0, 255), 5, tipLength=0.08)
        draw_point(overlay, mp_wrist, (0, 80, 255), "MP wrist", radius=9, thickness=2)
        draw_point(overlay, point_to_int(points[5]), (0, 140, 255), "MP index_mcp", radius=9, thickness=2)
        draw_point(overlay, middle_mcp, (0, 80, 255), "MP middle_mcp", radius=9, thickness=2)
        draw_point(overlay, point_to_int(points[17]), (0, 140, 255), "MP pinky_mcp", radius=9, thickness=2)
        mp_wrist_text = format_point(hand_result["wrist_px"])
        middle_mcp_text = format_point(points[9])

    text_lines = [
        f"side: {side}",
        "body_detected: True",
        f"hand_detected: {hand_result is not None}",
        f"handedness: {None if hand_result is None else hand_result['handedness']}",
        f"YOLO wrist: {format_point(side_body['wrist_px'])}",
        f"MP wrist: {mp_wrist_text}",
        f"MP middle_mcp: {middle_mcp_text}",
        f"bend_angle_2d: {format_value(estimator_result['bend_angle_2d'])}",
        f"bend_risk: {format_value(estimator_result['bend_risk'])}",
        f"bend_state: {estimator_result['bend_state']}",
        f"valid: {estimator_result['valid']}",
        f"global_invalid_reason: {estimator_result['global_invalid_reason']}",
    ]
    draw_text_block(overlay, text_lines, avoid_box=crop_box)
    cv2.imwrite(str(output_path), overlay)


def save_crop_image(image, crop_box, output_path):
    import cv2

    x1, y1, x2, y2 = crop_box
    cv2.imwrite(str(output_path), image[y1:y2, x1:x2])


def draw_point(image, point, color, label, radius=6, thickness=1):
    import cv2

    cv2.circle(image, point, radius, color, -1)
    cv2.circle(image, point, radius + 2, (255, 255, 255), thickness)
    cv2.putText(
        image,
        label,
        (point[0] + radius + 4, point[1] - radius - 3),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2,
        cv2.LINE_AA,
    )


def draw_text_block(image, lines, avoid_box):
    import cv2

    line_height = 22
    width = min(image.shape[1] - 10, 760)
    height = line_height * len(lines) + 12
    x0, y0 = choose_text_origin(image, width, height, avoid_box)
    roi = image[y0 : y0 + height, x0 : x0 + width]
    black = roi.copy()
    black[:] = (0, 0, 0)
    cv2.addWeighted(black, 0.68, roi, 0.32, 0, dst=roi)
    x = x0 + 8
    y = y0 + 22
    for line in lines:
        cv2.putText(
            image,
            line,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        y += line_height


def choose_text_origin(image, width, height, avoid_box):
    image_h, image_w = image.shape[:2]
    candidates = [
        (5, 5),
        (max(5, image_w - width - 5), 5),
        (5, max(5, image_h - height - 5)),
        (max(5, image_w - width - 5), max(5, image_h - height - 5)),
    ]
    for x0, y0 in candidates:
        if not boxes_overlap((x0, y0, x0 + width, y0 + height), avoid_box):
            return x0, y0
    return candidates[0]


def boxes_overlap(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def hand_landmarks_to_image_points(hand_landmarks, crop_box):
    x1, y1, x2, y2 = crop_box
    return [
        crop_to_image_coords(landmark, x1, y1, x2, y2)
        for landmark in hand_landmarks.landmark
    ]


def save_3d_hand_world_plot(hand_world_landmarks, output_path, is_right_hand):
    os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mplconfig")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    points = np.array(
        [
            [landmark.x, landmark.y, landmark.z]
            for landmark in hand_world_landmarks.landmark
        ],
        dtype=float,
    )
    fig = plt.figure(figsize=(8, 7), dpi=180)
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(points[:, 0], points[:, 1], points[:, 2], c="tab:blue", s=20)
    chain_colors = {
        "thumb": "tab:orange",
        "index": "tab:blue",
        "middle": "tab:green",
        "ring": "tab:purple",
        "pinky": "tab:brown",
        "palm": "gray",
    }
    for chain_name, connections in FINGER_CHAINS.items():
        for a, b in connections:
            segment = points[[a, b]]
            ax.plot(
                segment[:, 0],
                segment[:, 1],
                segment[:, 2],
                color=chain_colors[chain_name],
                linewidth=2.6,
            )

    highlights = {0: "wrist", 5: "index_mcp", 9: "middle_mcp", 17: "pinky_mcp"}
    for idx, label in highlights.items():
        ax.scatter(points[idx, 0], points[idx, 1], points[idx, 2], c="red", s=85)
        ax.text(points[idx, 0], points[idx, 1], points[idx, 2], label)

    normal = np.array(
        palm_normal_from_world(hand_world_landmarks, is_right_hand=is_right_hand),
        dtype=float,
    )
    palm_center = points[[0, 5, 17]].mean(axis=0)
    ax.quiver(
        palm_center[0],
        palm_center[1],
        palm_center[2],
        normal[0],
        normal[1],
        normal[2],
        length=0.08,
        color="green",
    )
    set_equalish_axes(ax, points)
    ax.view_init(elev=22, azim=-62)
    ax.set_title("MediaPipe hand_world_landmarks")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
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


def format_value(value):
    if value is None:
        return "None"
    return f"{float(value):.2f}"


def format_point(point):
    if point is None:
        return "None"
    return f"({float(point[0]):.1f}, {float(point[1]):.1f})"


if __name__ == "__main__":
    raise SystemExit(main())
