import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from compare_yolo26_rtmpose_full_body import (
    KEYPOINT_NAMES,
    RTMPOSE_COLOR,
    YOLO_COLOR,
    compare_keypoints,
    draw_panel_title,
    draw_pose,
    draw_status,
    drawing_sizes,
    read_image,
    run_rtmpose,
    run_yolo,
)


RTMPOSE_S_COLOR = (0, 180, 255)
RTMPOSE_M_COLOR = RTMPOSE_COLOR
FOCUS_NAMES = [
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare YOLO26n-pose, RTMPose-s, and RTMPose-m.",
    )
    parser.add_argument("--image", default="assets/smoke/pushup.jpg")
    parser.add_argument("--yolo-model", default="models/yolo26n-pose.pt")
    parser.add_argument(
        "--rtmpose-s-config",
        default="models/rtmpose/rtmpose-s_8xb256-420e_coco-256x192.py",
    )
    parser.add_argument(
        "--rtmpose-s-checkpoint",
        default="models/rtmpose/rtmpose-s_coco.pth",
    )
    parser.add_argument(
        "--rtmpose-m-config",
        default="models/rtmpose/rtmpose-m_8xb256-420e_coco-256x192.py",
    )
    parser.add_argument(
        "--rtmpose-m-checkpoint",
        default="models/rtmpose/rtmpose-m_coco.pth",
    )
    parser.add_argument(
        "--output-side-by-side",
        default="assets/smoke/compare_yolo26n_rtmpose_s_m_side_by_side.jpg",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--conf-threshold", type=float, default=0.3)
    parser.add_argument("--marker-scale", type=float, default=0.6)
    return parser.parse_args()


def main():
    args = parse_args()
    image = read_image(Path(args.image))
    sizes = drawing_sizes(image.shape[1], image.shape[0], args.marker_scale)

    yolo_keypoints, yolo_error = run_yolo(args.yolo_model, image)
    rtmpose_s_keypoints, rtmpose_s_error = run_rtmpose(
        args.rtmpose_s_config,
        args.rtmpose_s_checkpoint,
        args.device,
        image,
    )
    rtmpose_m_keypoints, rtmpose_m_error = run_rtmpose(
        args.rtmpose_m_config,
        args.rtmpose_m_checkpoint,
        args.device,
        image,
    )

    output = Path(args.output_side_by_side)
    output.parent.mkdir(parents=True, exist_ok=True)
    save_three_panel(
        image=image,
        output=output,
        conf_threshold=args.conf_threshold,
        sizes=sizes,
        yolo_keypoints=yolo_keypoints,
        rtmpose_s_keypoints=rtmpose_s_keypoints,
        rtmpose_m_keypoints=rtmpose_m_keypoints,
        yolo_error=yolo_error,
        rtmpose_s_error=rtmpose_s_error,
        rtmpose_m_error=rtmpose_m_error,
    )

    summary = {
        "image": args.image,
        "output_side_by_side": str(output),
        "body_detected": {
            "yolo26n": yolo_keypoints is not None,
            "rtmpose_s": rtmpose_s_keypoints is not None,
            "rtmpose_m": rtmpose_m_keypoints is not None,
        },
        "errors": {
            "yolo26n": yolo_error,
            "rtmpose_s": rtmpose_s_error,
            "rtmpose_m": rtmpose_m_error,
        },
        "comparisons": {
            "yolo26n_vs_rtmpose_s": pair_summary(
                yolo_keypoints,
                rtmpose_s_keypoints,
                args.conf_threshold,
            ),
            "yolo26n_vs_rtmpose_m": pair_summary(
                yolo_keypoints,
                rtmpose_m_keypoints,
                args.conf_threshold,
            ),
            "rtmpose_s_vs_rtmpose_m": pair_summary(
                rtmpose_s_keypoints,
                rtmpose_m_keypoints,
                args.conf_threshold,
            ),
        },
    }
    print(summary)
    return 0


def save_three_panel(
    image,
    output,
    conf_threshold,
    sizes,
    yolo_keypoints,
    rtmpose_s_keypoints,
    rtmpose_m_keypoints,
    yolo_error,
    rtmpose_s_error,
    rtmpose_m_error,
):
    import cv2

    panels = [
        render_panel(
            image,
            yolo_keypoints,
            yolo_error,
            "YOLO26n-pose",
            "Y",
            YOLO_COLOR,
            conf_threshold,
            sizes,
        ),
        render_panel(
            image,
            rtmpose_s_keypoints,
            rtmpose_s_error,
            "RTMPose-s",
            "S",
            RTMPOSE_S_COLOR,
            conf_threshold,
            sizes,
        ),
        render_panel(
            image,
            rtmpose_m_keypoints,
            rtmpose_m_error,
            "RTMPose-m",
            "M",
            RTMPOSE_M_COLOR,
            conf_threshold,
            sizes,
        ),
    ]
    cv2.imwrite(str(output), cv2.hconcat(panels))


def render_panel(
    image,
    keypoints,
    error,
    title,
    prefix,
    color,
    conf_threshold,
    sizes,
):
    panel = image.copy()
    if keypoints is None:
        draw_status(panel, f"{title} failed", error or "no result", sizes)
    else:
        draw_pose(panel, keypoints, prefix, color, conf_threshold, sizes)
    draw_panel_title(panel, title, color, sizes)
    return panel


def pair_summary(a_keypoints, b_keypoints, conf_threshold):
    _, summary = compare_keypoints(a_keypoints, b_keypoints, conf_threshold)
    return {
        "mean_distance_px": summary["mean_distance_px"],
        "max_distance_px": summary["max_distance_px"],
        "largest_disagreement_keypoints": summary["largest_disagreement_keypoints"],
        "focus_disagreements": {
            name: summary["focus_disagreements"].get(name)
            for name in FOCUS_NAMES
            if name in KEYPOINT_NAMES
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
