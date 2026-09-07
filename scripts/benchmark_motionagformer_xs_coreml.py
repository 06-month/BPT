"""Benchmark MotionAGFormer-XS Core ML prediction latency on macOS.

This measures prediction-only steady-state latency for the already-converted
``assets/coreml/motionagformer_xs.mlpackage``. Model load/compile and the first
prediction are reported separately and are not included in steady-state stats.
ANE placement is not inferred from this script.
"""

import csv
import json
import statistics
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "assets/coreml/motionagformer_xs.mlpackage"
INPUT_NPZ = ROOT / "assets/smoke/motionagformer_xs_s_test/inputs/vedio_1_motionagformer_xs_input.npz"
OUTPUT_JSON = ROOT / "assets/coreml/motionagformer_xs_coreml_benchmark_macos.json"
OUTPUT_CSV = ROOT / "assets/coreml/motionagformer_xs_coreml_benchmark_macos.csv"
INPUT_NAME = "input_2d_sequence"
OUTPUT_NAME = "pred_3d_sequence"
WARMUP = 10
ITERATIONS = 100


def main():
    import coremltools as ct

    windows = load_windows()

    load_start = time.perf_counter()
    model = ct.models.MLModel(str(MODEL_PATH), compute_units=ct.ComputeUnit.ALL)
    model_load_ms = elapsed_ms(load_start)

    first_input = windows[0:1]
    first_start = time.perf_counter()
    first_pred = model.predict({INPUT_NAME: first_input})
    first_prediction_ms = elapsed_ms(first_start)
    output = np.asarray(first_pred.get(OUTPUT_NAME, next(iter(first_pred.values()))), dtype="float32")
    if output.shape != (1, 27, 17, 3):
        raise ValueError(f"Expected Core ML output shape [1, 27, 17, 3], got {output.shape}")

    for index in range(WARMUP):
        model.predict({INPUT_NAME: next_window(windows, index)})

    times = []
    for index in range(ITERATIONS):
        window = next_window(windows, WARMUP + index)
        start = time.perf_counter()
        model.predict({INPUT_NAME: window})
        times.append(elapsed_ms(start))

    stats = summarize_times(times)
    metadata = model.user_defined_metadata
    result = {
        "coreml_model_path": "assets/coreml/motionagformer_xs.mlpackage",
        "input_npz": "assets/smoke/motionagformer_xs_s_test/inputs/vedio_1_motionagformer_xs_input.npz",
        "input_key": "lookahead5_windows",
        "input_shape": [1, 27, 17, 3],
        "output_shape": list(output.shape),
        "model_load_ms": float(model_load_ms),
        "first_prediction_ms": float(first_prediction_ms),
        "warmup_count": WARMUP,
        "iteration_count": ITERATIONS,
        "ane_verified": False,
        "compute_units_requested": "ALL",
        "precision": metadata.get("precision", "unknown"),
        "export_mode": metadata.get("export_mode", "unknown"),
        **stats,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def load_windows():
    data = np.load(INPUT_NPZ, allow_pickle=True)
    windows = np.asarray(data["lookahead5_windows"], dtype="float32")
    if windows.ndim != 4 or windows.shape[1:] != (27, 17, 3):
        raise ValueError(f"Expected lookahead5_windows shape [N, 27, 17, 3], got {windows.shape}")
    if len(windows) == 0:
        raise ValueError("lookahead5_windows is empty")
    return windows


def next_window(windows, index):
    return windows[index % len(windows)][None, ...].astype("float32", copy=False)


def elapsed_ms(start):
    return (time.perf_counter() - start) * 1000.0


def summarize_times(times):
    sorted_times = sorted(times)
    mean_ms = statistics.mean(times)
    return {
        "mean_ms": float(mean_ms),
        "median_ms": float(statistics.median(times)),
        "p90_ms": float(percentile(sorted_times, 90)),
        "p95_ms": float(percentile(sorted_times, 95)),
        "min_ms": float(min(times)),
        "max_ms": float(max(times)),
        "fps": float(1000.0 / mean_ms if mean_ms > 0 else 0.0),
    }


def percentile(sorted_values, value):
    index = (len(sorted_values) - 1) * value / 100.0
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def write_csv(result):
    fieldnames = [
        "coreml_model_path",
        "input_npz",
        "input_key",
        "input_shape",
        "output_shape",
        "model_load_ms",
        "first_prediction_ms",
        "warmup_count",
        "iteration_count",
        "mean_ms",
        "median_ms",
        "p90_ms",
        "p95_ms",
        "min_ms",
        "max_ms",
        "fps",
        "precision",
        "export_mode",
        "compute_units_requested",
        "ane_verified",
    ]
    row = dict(result)
    row["input_shape"] = json.dumps(row["input_shape"])
    row["output_shape"] = json.dumps(row["output_shape"])
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({key: row.get(key) for key in fieldnames})


if __name__ == "__main__":
    raise SystemExit(main())
