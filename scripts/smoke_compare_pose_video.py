import argparse
import json
import os
from pathlib import Path
import sys


os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mpl_cache")

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
    legacy_openmmlab_checkpoint_load,
)
from pose_feedback.body.rtmpose_runner import (
    RTMPoseNoPersonDetectedError,
    RTMPoseRunner,
)
from pose_feedback.body.yolo26_runner import (
    NoPersonDetectedError,
    UltralyticsYOLO26PoseRunner,
)


FOCUS_KEYPOINTS = [
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
        description="Video smoke comparison for YOLO26n-pose and RTMPose-s.",
    )
    parser.add_argument("--video", default="assets/smoke/vedio_1.mp4")
    parser.add_argument("--yolo-model", default="models/yolo26n-pose.pt")
    parser.add_argument(
        "--rtmpose-config",
        default="models/rtmpose/rtmpose-s_8xb256-420e_coco-256x192.py",
    )
    parser.add_argument(
        "--rtmpose-checkpoint",
        default="models/rtmpose/rtmpose-s_coco.pth",
    )
    parser.add_argument(
        "--output-yolo-video",
        default="assets/smoke/vedio_1_yolo26n_overlay.mp4",
    )
    parser.add_argument(
        "--output-rtmpose-video",
        default="assets/smoke/vedio_1_rtmpose_s_overlay.mp4",
    )
    parser.add_argument(
        "--output-jsonl",
        default="assets/smoke/vedio_1_pose_compare_log.jsonl",
    )
    parser.add_argument("--max-frames", type=int, default=300)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--marker-scale", type=float, default=0.6)
    parser.add_argument("--conf-threshold", type=float, default=0.3)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.stride < 1:
        raise ValueError("--stride must be >= 1")
    if args.max_frames < 1:
        raise ValueError("--max-frames must be >= 1")

    import cv2

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        print({"video_opened": False, "video": args.video})
        return 0

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 1e-6:
        fps = 30.0
    image_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    image_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output_fps = max(1.0, fps / args.stride)
    sizes = drawing_sizes(image_w, image_h, args.marker_scale)

    yolo_runner, yolo_init_error = init_yolo(args.yolo_model)
    rtmpose_runner, rtmpose_init_error = init_rtmpose(
        args.rtmpose_config,
        args.rtmpose_checkpoint,
        args.device,
    )
    if yolo_init_error:
        print(f"YOLO26n-pose unavailable: {yolo_init_error}")
    if rtmpose_init_error:
        print(f"RTMPose-s unavailable: {rtmpose_init_error}")

    yolo_writer = make_writer(args.output_yolo_video, output_fps, image_w, image_h)
    rtmpose_writer = make_writer(args.output_rtmpose_video, output_fps, image_w, image_h)
    jsonl_path = Path(args.output_jsonl)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)

    accum = SummaryAccumulator()
    processed_frames = 0
    yolo_detected_count = 0
    rtmpose_detected_count = 0
    frame_idx = 0

    with jsonl_path.open("w", encoding="utf-8") as log_file:
        while processed_frames < args.max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % args.stride != 0:
                frame_idx += 1
                continue

            timestamp_sec = frame_idx / fps
            yolo_keypoints, yolo_error = predict_yolo(yolo_runner, frame)
            rtmpose_keypoints, rtmpose_error = predict_rtmpose(rtmpose_runner, frame)
            if yolo_keypoints is not None:
                yolo_detected_count += 1
            elif yolo_init_error and yolo_error is None:
                yolo_error = yolo_init_error
            if rtmpose_keypoints is not None:
                rtmpose_detected_count += 1
            elif rtmpose_init_error and rtmpose_error is None:
                rtmpose_error = rtmpose_init_error

            comparison, distance_summary = compare_keypoints(
                yolo_keypoints,
                rtmpose_keypoints,
                args.conf_threshold,
            )
            accum.update(comparison)
            write_frame(
                yolo_writer,
                frame,
                yolo_keypoints,
                yolo_error,
                "YOLO26n-pose",
                "Y",
                YOLO_COLOR,
                args.conf_threshold,
                sizes,
            )
            write_frame(
                rtmpose_writer,
                frame,
                rtmpose_keypoints,
                rtmpose_error,
                "RTMPose-s",
                "R",
                RTMPOSE_COLOR,
                args.conf_threshold,
                sizes,
            )
            log_file.write(
                json.dumps(
                    {
                        "frame_idx": frame_idx,
                        "timestamp_sec": timestamp_sec,
                        "yolo_body_detected": yolo_keypoints is not None,
                        "rtmpose_body_detected": rtmpose_keypoints is not None,
                        "yolo_error": yolo_error,
                        "rtmpose_error": rtmpose_error,
                        "yolo_keypoints": keypoints_to_records(yolo_keypoints),
                        "rtmpose_keypoints": keypoints_to_records(rtmpose_keypoints),
                        "disagreement": frame_disagreement_payload(
                            comparison,
                            distance_summary,
                        ),
                    },
                    sort_keys=True,
                )
                + "\n",
            )

            processed_frames += 1
            frame_idx += 1

    cap.release()
    yolo_writer.release()
    rtmpose_writer.release()

    summary = {
        "video_opened": True,
        "video": args.video,
        "processed_frames": processed_frames,
        "yolo_detected_count": yolo_detected_count,
        "rtmpose_detected_count": rtmpose_detected_count,
        "output_yolo_video": args.output_yolo_video,
        "output_rtmpose_video": args.output_rtmpose_video,
        "output_jsonl": str(jsonl_path),
        "mean_yolo_vs_rtmpose_keypoint_distance": accum.mean_all(),
        "focus_mean_distances": accum.focus_means(),
    }
    print(summary)
    return 0


def init_yolo(model_path):
    try:
        return UltralyticsYOLO26PoseRunner(model_path=model_path), None
    except ImportError as exc:
        return None, f"runtime_import_error: {exc}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def init_rtmpose(config_path, checkpoint_path, device):
    try:
        with legacy_openmmlab_checkpoint_load():
            return (
                RTMPoseRunner(
                    pose_config=config_path,
                    pose_checkpoint=checkpoint_path,
                    device=device,
                ),
                None,
            )
    except ImportError as exc:
        return None, f"runtime_import_error: {exc}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def predict_yolo(runner, frame):
    if runner is None:
        return None, None
    try:
        return runner.predict_keypoints(frame), None
    except NoPersonDetectedError as exc:
        return None, f"no_person_detected: {exc}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def predict_rtmpose(runner, frame):
    if runner is None:
        return None, None
    try:
        return runner.predict_keypoints(frame), None
    except RTMPoseNoPersonDetectedError as exc:
        return None, f"no_person_detected: {exc}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def make_writer(path, fps, image_w, image_h):
    import cv2

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output), fourcc, fps, (image_w, image_h))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {output}")
    return writer


def write_frame(
    writer,
    frame,
    keypoints,
    error,
    title,
    prefix,
    color,
    conf_threshold,
    sizes,
):
    panel = frame.copy()
    if keypoints is None:
        draw_status(panel, f"{title} failed", error or "no result", sizes)
    else:
        draw_pose(panel, keypoints, prefix, color, conf_threshold, sizes)
    draw_panel_title(panel, title, color, sizes)
    writer.write(panel)


def keypoints_to_records(keypoints):
    if keypoints is None:
        return None
    records = []
    for index, name in enumerate(KEYPOINT_NAMES):
        records.append(
            {
                "index": index,
                "name": name,
                "x": float(keypoints[index][0]),
                "y": float(keypoints[index][1]),
                "confidence": float(keypoints[index][2]),
            },
        )
    return records


def frame_disagreement_payload(comparison, summary):
    return {
        "mean_distance_px": summary["mean_distance_px"],
        "max_distance_px": summary["max_distance_px"],
        "distances_by_keypoint": {
            name: item["distance_px"]
            for name, item in comparison.items()
        },
        "focus_disagreements": {
            name: summary["focus_disagreements"].get(name)
            for name in FOCUS_KEYPOINTS
        },
    }


class SummaryAccumulator:
    def __init__(self):
        self.all_distances = []
        self.focus_distances = {name: [] for name in FOCUS_KEYPOINTS}

    def update(self, comparison):
        for name, item in comparison.items():
            distance = item["distance_px"]
            if distance is None:
                continue
            self.all_distances.append(float(distance))
            if name in self.focus_distances:
                self.focus_distances[name].append(float(distance))

    def mean_all(self):
        if not self.all_distances:
            return None
        return float(sum(self.all_distances) / len(self.all_distances))

    def focus_means(self):
        means = {}
        for name, values in self.focus_distances.items():
            means[name] = None if not values else float(sum(values) / len(values))
        return means


if __name__ == "__main__":
    raise SystemExit(main())
