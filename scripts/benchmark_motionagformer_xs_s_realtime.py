import argparse
import csv
import json
import statistics
import time
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.motionagformer_runner import MotionAGFormerRunner


MODELS = {
    "xs": {
        "config": "external/MotionAGFormer/configs/h36m/MotionAGFormer-xsmall.yaml",
        "checkpoint": "external/MotionAGFormer/checkpoint/motionagformer-xs-h36m.pth.tr",
        "input_npz": "assets/smoke/motionagformer_xs_s_test/inputs/pushup_1_motionagformer_xs_input.npz",
    },
    "s": {
        "config": "external/MotionAGFormer/configs/h36m/MotionAGFormer-small.yaml",
        "checkpoint": "external/MotionAGFormer/checkpoint/motionagformer-s-h36m.pth.tr",
        "input_npz": "assets/smoke/motionagformer_xs_s_test/inputs/pushup_1_motionagformer_s_input.npz",
    },
}


WINDOW_KEYS = {
    "full": "full_centered_windows",
    "lookahead3": "lookahead3_windows",
    "lookahead5": "lookahead5_windows",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark MotionAGFormer XS/S feasibility.")
    parser.add_argument("--repo-dir", default="external/MotionAGFormer")
    parser.add_argument("--device", choices=("cpu", "mps", "auto"), default="cpu")
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--xs-input-npz", default=MODELS["xs"]["input_npz"])
    parser.add_argument("--s-input-npz", default=MODELS["s"]["input_npz"])
    parser.add_argument("--modes", nargs="+", choices=tuple(WINDOW_KEYS), default=["full", "lookahead3", "lookahead5"])
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-json", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    rows = []
    models = {
        "xs": {**MODELS["xs"], "input_npz": args.xs_input_npz},
        "s": {**MODELS["s"], "input_npz": args.s_input_npz},
    }
    for model_name, meta in models.items():
        for window_mode in args.modes:
            rows.append(benchmark_one(model_name, meta, args, window_mode, "lifter_only"))
            rows.append(benchmark_one(model_name, meta, args, window_mode, "full_pipeline_from_jsonl"))
    save_csv(Path(args.output_csv), rows)
    summary = {"rows": rows, "device_requested": args.device, "max_frames": args.max_frames}
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(summary)
    return 0


def benchmark_one(model_name, meta, args, window_mode, benchmark_mode):
    config = Path(meta["config"])
    checkpoint = Path(meta["checkpoint"])
    input_npz = Path(meta["input_npz"])
    base = {
        "model": model_name,
        "window_mode": window_mode,
        "benchmark_mode": benchmark_mode,
        "config": str(config),
        "checkpoint": str(checkpoint),
        "input_npz": str(input_npz),
        "device": args.device,
        "status": "skipped",
    }
    if not config.exists():
        return {**base, "reason": "missing_config"}
    if not checkpoint.exists():
        return {**base, "reason": "missing_checkpoint"}
    if not input_npz.exists():
        return {**base, "reason": "missing_input_npz"}
    data = np.load(input_npz, allow_pickle=True)
    window_key = WINDOW_KEYS[window_mode]
    if window_key not in data.files:
        return {**base, "reason": f"missing_{window_key}"}
    windows = np.asarray(data[window_key], dtype="float32")[: args.max_frames]
    if len(windows) == 0:
        return {**base, "reason": "empty_windows"}

    load_start = time.perf_counter()
    try:
        runner = MotionAGFormerRunner(
            repo_dir=args.repo_dir,
            config_path=str(config),
            checkpoint_path=str(checkpoint),
            device=args.device,
            window_size=windows.shape[1],
        )
    except Exception as exc:
        return {**base, "reason": f"{type(exc).__name__}: {exc}"}
    load_ms = elapsed_ms(load_start)

    for window in windows[: min(args.warmup, len(windows))]:
        runner.predict_3d(window)

    times = []
    for window in windows:
        start = time.perf_counter()
        runner.predict_3d(window)
        times.append(elapsed_ms(start))
    stats = summarize_times(times)
    return {
        **base,
        "status": "ran",
        "reason": None,
        "device": runner.device_name,
        "processed_frames": len(windows),
        "model_load_ms": load_ms,
        **stats,
        "realtime_30fps": stats["fps"] >= 30.0,
        "realtime_20fps": stats["fps"] >= 20.0,
    }


def elapsed_ms(start):
    return (time.perf_counter() - start) * 1000.0


def summarize_times(times):
    if not times:
        return {"mean_ms": None, "median_ms": None, "p90_ms": None, "p95_ms": None, "fps": 0.0}
    sorted_times = sorted(times)
    mean = statistics.mean(times)
    return {
        "mean_ms": mean,
        "median_ms": statistics.median(times),
        "p90_ms": percentile(sorted_times, 90),
        "p95_ms": percentile(sorted_times, 95),
        "fps": 1000.0 / mean,
    }


def percentile(sorted_values, value):
    if not sorted_values:
        return None
    index = (len(sorted_values) - 1) * value / 100.0
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model",
        "benchmark_mode",
        "status",
        "reason",
        "device",
        "processed_frames",
        "model_load_ms",
        "window_mode",
        "mean_ms",
        "median_ms",
        "p90_ms",
        "p95_ms",
        "fps",
        "realtime_30fps",
        "realtime_20fps",
        "config",
        "checkpoint",
        "input_npz",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
