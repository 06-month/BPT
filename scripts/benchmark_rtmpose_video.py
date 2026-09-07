import argparse
import csv
import json
import statistics
import time
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
    parser = argparse.ArgumentParser(description="Benchmark RTMPose video inference without video writing.")
    parser.add_argument("--video", required=True)
    parser.add_argument("--model", action="append", required=True, help="name=config=checkpoint")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-frames", type=int, default=240)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    models = [parse_model(value) for value in args.model]
    results = []
    for model in models:
        results.append(benchmark_model(args.video, model, args.device, args.max_frames, args.warmup))
    save_csv(Path(args.output_csv), results)
    output = {
        "video": args.video,
        "device": args.device,
        "max_frames": args.max_frames,
        "results": results,
    }
    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_json).write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(output)
    return 0


def parse_model(value):
    parts = value.split("=", 2)
    if len(parts) != 3:
        raise ValueError("Expected --model name=config=checkpoint")
    return {"name": parts[0], "config": parts[1], "checkpoint": parts[2]}


def benchmark_model(video, model, device, max_frames, warmup):
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return {"model": model["name"], "video_opened": False}
    frames = []
    while len(frames) < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()

    load_start = time.perf_counter()
    with legacy_openmmlab_checkpoint_load():
        runner = RTMPoseRunner(model["config"], model["checkpoint"], device=device)
    load_sec = time.perf_counter() - load_start

    warmup_frames = frames[: min(warmup, len(frames))]
    for frame in warmup_frames:
        try:
            runner.predict_keypoints(frame)
        except RTMPoseNoPersonDetectedError:
            pass

    times_ms = []
    detected = 0
    for frame in frames:
        start = time.perf_counter()
        try:
            runner.predict_keypoints(frame)
            detected += 1
        except RTMPoseNoPersonDetectedError:
            pass
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        times_ms.append(elapsed_ms)

    summary = summarize_times(times_ms)
    summary.update(
        {
            "model": model["name"],
            "config": model["config"],
            "checkpoint": model["checkpoint"],
            "device": device,
            "video_opened": True,
            "model_load_sec": load_sec,
            "processed_frames": len(frames),
            "detected_frames": detected,
            "realtime_30fps": summary["fps"] >= 30.0,
            "realtime_20fps": summary["fps"] >= 20.0,
        },
    )
    return summary


def summarize_times(times_ms):
    if not times_ms:
        return {"mean_ms": None, "median_ms": None, "p90_ms": None, "p95_ms": None, "fps": 0.0}
    sorted_times = sorted(times_ms)
    return {
        "mean_ms": statistics.mean(times_ms),
        "median_ms": statistics.median(times_ms),
        "p90_ms": percentile(sorted_times, 90),
        "p95_ms": percentile(sorted_times, 95),
        "fps": 1000.0 / statistics.mean(times_ms),
    }


def percentile(sorted_values, percentile_value):
    if not sorted_values:
        return None
    index = (len(sorted_values) - 1) * percentile_value / 100.0
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model",
        "device",
        "processed_frames",
        "detected_frames",
        "model_load_sec",
        "mean_ms",
        "median_ms",
        "p90_ms",
        "p95_ms",
        "fps",
        "realtime_30fps",
        "realtime_20fps",
        "config",
        "checkpoint",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
