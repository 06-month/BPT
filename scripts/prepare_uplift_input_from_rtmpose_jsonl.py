import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.uplift_upsample_adapter import (
    coco17_to_uplift_h36m17,
    normalize_uplift_2d,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare Uplift-Upsample NPZ input from RTMPose JSONL.")
    parser.add_argument("--input-jsonl", default="assets/smoke/vedio_1_rtmpose_2d_keypoints.jsonl")
    parser.add_argument("--output-npz", default="assets/smoke/vedio_1_uplift_input_debug.npz")
    parser.add_argument("--window-size", type=int, default=71)
    parser.add_argument("--stride", type=int, default=1)
    return parser.parse_args()


def main():
    args = parse_args()
    frames = load_frames(Path(args.input_jsonl))
    if not frames:
        print({"input_loaded": False, "reason": "no frames", "input_jsonl": args.input_jsonl})
        return 0
    raw, converted, normalized, confidences = convert_frames(frames)
    frame_indices = build_window_indices(len(frames), args.window_size, args.stride)
    windows = normalized[frame_indices]
    output = Path(args.output_npz)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output,
        raw_coco17=raw,
        converted_2d=converted,
        normalized_2d=normalized,
        normalized_windows=windows,
        confidences=confidences,
        frame_indices=frame_indices,
        image_width=np.asarray([frames[0]["image_width"]], dtype="int32"),
        image_height=np.asarray([frames[0]["image_height"]], dtype="int32"),
    )
    print(
        {
            "input_loaded": True,
            "frames": len(frames),
            "raw_coco17_shape": tuple(raw.shape),
            "converted_2d_shape": tuple(converted.shape),
            "normalized_2d_shape": tuple(normalized.shape),
            "normalized_windows_shape": tuple(windows.shape),
            "frame_indices_shape": tuple(frame_indices.shape),
            "sample_normalized_root": normalized[0, 6].tolist(),
            "output_npz": str(output),
        },
    )
    return 0


def load_frames(path):
    if not path.exists():
        return []
    frames = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("keypoints_coco17") is not None:
                frames.append(record)
    return frames


def convert_frames(frames):
    raw_rows = []
    converted_rows = []
    normalized_rows = []
    conf_rows = []
    for frame in frames:
        coco = np.asarray(frame["keypoints_coco17"], dtype="float32")
        converted, conf = coco17_to_uplift_h36m17(coco)
        normalized = normalize_uplift_2d(converted, frame["image_width"], frame["image_height"])
        raw_rows.append(coco)
        converted_rows.append(converted)
        normalized_rows.append(normalized)
        conf_rows.append(conf)
    return (
        np.asarray(raw_rows, dtype="float32"),
        np.asarray(converted_rows, dtype="float32"),
        np.asarray(normalized_rows, dtype="float32"),
        np.asarray(conf_rows, dtype="float32"),
    )


def build_window_indices(num_frames, window_size, stride):
    if window_size <= 0 or stride <= 0:
        raise ValueError("window_size and stride must be positive")
    centers = np.arange(0, num_frames, stride, dtype=int)
    half = window_size // 2
    rows = []
    for center in centers:
        idx = np.arange(center - half, center - half + window_size, dtype=int)
        rows.append(np.clip(idx, 0, num_frames - 1))
    return np.asarray(rows, dtype="int32")


if __name__ == "__main__":
    raise SystemExit(main())
