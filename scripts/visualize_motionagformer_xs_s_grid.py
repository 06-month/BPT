import argparse
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from visualize_2d_video_with_uplift_3d_side_by_side import draw_coco17, drawing_sizes, make_writer, read_frame
from visualize_motionagformer_2d_3d_side_by_side import render_3d_stack
from pose_feedback.body.motionagformer_adapter import motionagformer_angles


def parse_args():
    parser = argparse.ArgumentParser(description="Visualize XS vs S MotionAGFormer 3D outputs with RTMPose 2D.")
    parser.add_argument("--video", default="assets/smoke/pushup_1.mp4")
    parser.add_argument("--rtmpose-jsonl", default="assets/smoke/pushup_1_rtmpose_s_2d_keypoints.jsonl")
    parser.add_argument("--xs-npz", required=True)
    parser.add_argument("--s-npz", required=True)
    parser.add_argument("--output-video", required=True)
    parser.add_argument("--max-frames", type=int, default=170)
    parser.add_argument("--marker-scale", type=float, default=0.6)
    parser.add_argument("--axis-preset", choices=("raw", "user"), default="user")
    return parser.parse_args()


def main():
    args = parse_args()
    import cv2

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print({"video_created": False, "reason": "video_open_failed", "video": args.video})
        return 0
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0
    image_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    image_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    sizes = drawing_sizes(image_w, image_h, args.marker_scale)
    rtmpose = load_rtmpose_jsonl(Path(args.rtmpose_jsonl))
    xs = load_output(args.xs_npz)
    small = load_output(args.s_npz)
    frame_to_xs = {int(frame): idx for idx, frame in enumerate(xs["frames"])}
    frame_to_s = {int(frame): idx for idx, frame in enumerate(small["frames"])}
    frames = sorted(set(frame_to_xs) & set(frame_to_s))[: args.max_frames]
    writer = make_writer(Path(args.output_video), fps, image_w * 3, image_h)
    rendered = 0
    for frame in frames:
        ok, image = read_frame(cap, frame)
        if not ok:
            continue
        left = image.copy()
        row = rtmpose.get(frame)
        if row and row.get("keypoints_coco17") is not None:
            draw_coco17(left, np.asarray(row["keypoints_coco17"], dtype="float32"), sizes)
        label(left, f"RTMPose-s 2D | frame {frame}", sizes)
        xs_panel = render_3d_stack(
            xs["joints"][frame_to_xs[frame]],
            motionagformer_angles(xs["joints"][frame_to_xs[frame]]),
            frame_to_xs[frame],
            frame,
            image_w,
            image_h,
            args.axis_preset,
            "XS lookahead5",
            int(xs["latency_frames"]),
            float(xs["latency_sec"]),
        )
        s_panel = render_3d_stack(
            small["joints"][frame_to_s[frame]],
            motionagformer_angles(small["joints"][frame_to_s[frame]]),
            frame_to_s[frame],
            frame,
            image_w,
            image_h,
            args.axis_preset,
            "S lookahead5",
            int(small["latency_frames"]),
            float(small["latency_sec"]),
        )
        writer.write(np.concatenate([left, xs_panel, s_panel], axis=1))
        rendered += 1
    cap.release()
    writer.release()
    print({"video_created": True, "rendered_frames": rendered, "output_video": args.output_video})
    return 0


def load_output(path):
    data = np.load(path, allow_pickle=True)
    pred = np.asarray(data["pred_3d"], dtype="float32")
    frame_indices = np.asarray(data["frame_indices"])
    latency_frames = int(np.asarray(data["latency_frames"])[0])
    latency_sec = float(np.asarray(data["latency_sec"])[0])
    output_idx = int(np.clip(pred.shape[1] - latency_frames - 1, 0, pred.shape[1] - 1))
    frames = frame_indices[:, output_idx] if frame_indices.ndim == 2 else frame_indices
    joints = pred[:, output_idx] if pred.ndim == 4 else pred
    return {
        "frames": np.asarray(frames, dtype=int),
        "joints": joints,
        "latency_frames": latency_frames,
        "latency_sec": latency_sec,
    }


def load_rtmpose_jsonl(path):
    rows = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                row = json.loads(line)
                rows[int(row["frame_idx"])] = row
    return rows


def label(image, text, sizes):
    import cv2

    cv2.putText(image, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, sizes["font_scale"], (255, 255, 255), sizes["text_thickness"], cv2.LINE_AA)


if __name__ == "__main__":
    raise SystemExit(main())
