import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from compare_yolo26_rtmpose_full_body import legacy_openmmlab_checkpoint_load
from pose_feedback.body.rtmpose_runner import RTMPoseNoPersonDetectedError, RTMPoseRunner


def parse_args():
    parser = argparse.ArgumentParser(description="Export RTMPose COCO17 2D keypoints to JSONL.")
    parser.add_argument("--video", default="assets/smoke/vedio_1.mp4")
    parser.add_argument("--rtmpose-config", default="models/rtmpose/rtmpose-s_8xb256-420e_coco-256x192.py")
    parser.add_argument("--rtmpose-checkpoint", default="models/rtmpose/rtmpose-s_coco.pth")
    parser.add_argument("--output-jsonl", default="assets/smoke/vedio_1_rtmpose_2d_keypoints.jsonl")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--stride", type=int, default=1)
    return parser.parse_args()


def main():
    args = parse_args()
    import cv2

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        print({"video_opened": False, "video": args.video})
        return 0
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0
    image_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    image_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    try:
        with legacy_openmmlab_checkpoint_load():
            runner = RTMPoseRunner(args.rtmpose_config, args.rtmpose_checkpoint, device=args.device)
    except Exception as exc:
        print({"rtmpose_runtime": "unavailable", "reason": f"{type(exc).__name__}: {exc}"})
        return 0

    output = Path(args.output_jsonl)
    output.parent.mkdir(parents=True, exist_ok=True)
    processed = 0
    detected = 0
    frame_idx = 0
    with output.open("w", encoding="utf-8") as fh:
        while args.max_frames <= 0 or processed < args.max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % args.stride != 0:
                frame_idx += 1
                continue
            record = {
                "frame_idx": frame_idx,
                "timestamp_sec": frame_idx / fps,
                "image_width": image_w,
                "image_height": image_h,
                "keypoints_coco17": None,
                "body_detected": False,
            }
            try:
                keypoints = runner.predict_keypoints(frame)
                record["keypoints_coco17"] = keypoints.tolist()
                record["body_detected"] = True
                detected += 1
            except RTMPoseNoPersonDetectedError:
                pass
            fh.write(json.dumps(record, sort_keys=True) + "\n")
            processed += 1
            frame_idx += 1
    cap.release()
    print({"video_opened": True, "processed_frames": processed, "body_detected_count": detected, "output_jsonl": str(output)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
