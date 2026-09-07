import argparse
import csv
import json
from pathlib import Path
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
for path in (ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from pose_feedback.body.motionagformer_adapter import (
    coco17_to_motionagformer_h36m17,
    motionagformer_angles,
    normalize_motionagformer_2d,
)
from pose_feedback.body.motionagformer_buffer import MotionAGFormerWindowBuilder
from pose_feedback.body.motionagformer_runner import MotionAGFormerRunner


LOOKAHEAD = 5


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark MotionAGFormer lookahead5 real-time feasibility.")
    parser.add_argument("--video", default="assets/smoke/vedio_1.mp4")
    parser.add_argument("--input-npz", default="assets/smoke/vedio_1_motionagformer_input_debug.npz")
    parser.add_argument("--rtmpose-jsonl", default="assets/smoke/vedio_1_rtmpose_2d_keypoints.jsonl")
    parser.add_argument(
        "--mode",
        choices=(
            "lifter_only",
            "lifter_batched",
            "full_pipeline_from_jsonl",
            "full_pipeline_with_rtmpose",
        ),
        default="lifter_only",
    )
    parser.add_argument("--motionagformer-repo", default="external/MotionAGFormer")
    parser.add_argument("--config", default="external/MotionAGFormer/configs/h36m/MotionAGFormer-base.yaml")
    parser.add_argument(
        "--checkpoint",
        default="external/MotionAGFormer/checkpoint/motionagformer-b-h36m.pth.tr",
    )
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-frames", type=int, default=240)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--output-json", default="assets/smoke/motionagformer_realtime_benchmark.json")
    parser.add_argument("--output-csv", default="assets/smoke/motionagformer_realtime_benchmark.csv")
    parser.add_argument("--rtmpose-config", default="models/rtmpose/rtmpose-s_8xb256-420e_coco-256x192.py")
    parser.add_argument("--rtmpose-checkpoint", default="models/rtmpose/rtmpose-s_coco.pth")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.mode == "lifter_only":
        result, rows = benchmark_lifter_only(args)
    elif args.mode == "lifter_batched":
        result, rows = benchmark_lifter_batched(args)
    elif args.mode == "full_pipeline_from_jsonl":
        result, rows = benchmark_full_pipeline_from_jsonl(args)
    else:
        result, rows = benchmark_full_pipeline_with_rtmpose(args)

    save_outputs(result, rows, Path(args.output_json), Path(args.output_csv))
    print(compact_summary(result))
    return 0


def benchmark_lifter_only(args):
    windows, fps_video = load_lookahead_windows(Path(args.input_npz), args.max_frames)
    runner, load_time_ms = load_runner(args, windows.shape[1])
    warmup_time_ms = warmup_runner(runner, windows, args.warmup)

    rows = []
    for idx, window in enumerate(windows):
        inference_ms, pred = timed_call(runner, lambda: runner.predict_3d(window))
        rows.append(
            {
                "mode": args.mode,
                "frame_idx": idx,
                "adapter_preprocess_ms": None,
                "window_build_ms": None,
                "lifter_inference_ms": inference_ms,
                "postprocess_ms": None,
                "total_ms": inference_ms,
                "batch_size": 1,
                "output_shape": list(pred.shape),
            },
        )
    result = build_result(
        args=args,
        rows=rows,
        timing_key="total_ms",
        fps_video=fps_video,
        device=runner.device_name,
        load_time_ms=load_time_ms,
        warmup_time_ms=warmup_time_ms,
        extra={"benchmark_kind": "streaming_lifter_only"},
    )
    return result, rows


def benchmark_lifter_batched(args):
    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")
    windows, fps_video = load_lookahead_windows(Path(args.input_npz), args.max_frames)
    runner, load_time_ms = load_runner(args, windows.shape[1])
    warmup_time_ms = warmup_runner(runner, windows, args.warmup)

    rows = []
    for batch_start in range(0, len(windows), args.batch_size):
        batch = windows[batch_start : batch_start + args.batch_size]
        inference_ms, pred = timed_call(runner, lambda: runner.predict_3d(batch))
        per_window_ms = inference_ms / len(batch)
        for offset in range(len(batch)):
            rows.append(
                {
                    "mode": args.mode,
                    "frame_idx": batch_start + offset,
                    "adapter_preprocess_ms": None,
                    "window_build_ms": None,
                    "lifter_inference_ms": per_window_ms,
                    "postprocess_ms": None,
                    "total_ms": per_window_ms,
                    "batch_size": len(batch),
                    "output_shape": list(pred.shape),
                },
            )
    result = build_result(
        args=args,
        rows=rows,
        timing_key="total_ms",
        fps_video=fps_video,
        device=runner.device_name,
        load_time_ms=load_time_ms,
        warmup_time_ms=warmup_time_ms,
        extra={"benchmark_kind": "batched_throughput", "batch_size": args.batch_size},
    )
    return result, rows


def benchmark_full_pipeline_from_jsonl(args):
    raw_coco17, image_width, image_height, frame_numbers, fps_video = load_rtmpose_jsonl(
        Path(args.rtmpose_jsonl),
        args.max_frames,
    )
    runner, load_time_ms = load_runner(args, 243)

    normalized, adapter_rows = preprocess_frames(raw_coco17, image_width, image_height)
    builder = MotionAGFormerWindowBuilder(window_size=243)
    warmup_windows = build_warmup_windows(builder, normalized, args.warmup)
    warmup_time_ms = warmup_runner(runner, warmup_windows, len(warmup_windows))

    rows = []
    for idx in range(len(normalized)):
        t0 = time.perf_counter()
        window, indices = builder.build_lookahead_padded(normalized, idx, LOOKAHEAD)
        window_build_ms = elapsed_ms(t0)
        inference_ms, pred = timed_call(runner, lambda: runner.predict_3d(window))
        t1 = time.perf_counter()
        output_idx = int(np.clip(window.shape[0] - LOOKAHEAD - 1, 0, window.shape[0] - 1))
        _ = motionagformer_angles(pred[output_idx])
        postprocess_ms = elapsed_ms(t1)
        adapter_ms = adapter_rows[idx]["adapter_preprocess_ms"]
        total_ms = adapter_ms + window_build_ms + inference_ms + postprocess_ms
        rows.append(
            {
                "mode": args.mode,
                "frame_idx": int(frame_numbers[idx]),
                "adapter_preprocess_ms": adapter_ms,
                "window_build_ms": window_build_ms,
                "lifter_inference_ms": inference_ms,
                "postprocess_ms": postprocess_ms,
                "total_ms": total_ms,
                "batch_size": 1,
                "output_shape": list(pred.shape),
                "window_first_frame_idx": int(frame_numbers[indices[0]]),
                "window_last_frame_idx": int(frame_numbers[indices[-1]]),
            },
        )
    result = build_result(
        args=args,
        rows=rows,
        timing_key="total_ms",
        fps_video=fps_video,
        device=runner.device_name,
        load_time_ms=load_time_ms,
        warmup_time_ms=warmup_time_ms,
        extra={
            "benchmark_kind": "jsonl_adapter_window_lifter",
            "adapter_preprocess": stats([row["adapter_preprocess_ms"] for row in rows]),
            "window_build": stats([row["window_build_ms"] for row in rows]),
            "lifter_inference": stats([row["lifter_inference_ms"] for row in rows]),
            "postprocess": stats([row["postprocess_ms"] for row in rows]),
        },
    )
    return result, rows


def benchmark_full_pipeline_with_rtmpose(args):
    try:
        import cv2
        from compare_yolo26_rtmpose_full_body import legacy_openmmlab_checkpoint_load
        from pose_feedback.body.rtmpose_runner import RTMPoseNoPersonDetectedError, RTMPoseRunner
    except Exception as exc:
        result = skipped_result(args, f"rtmpose_import_failed: {type(exc).__name__}: {exc}")
        return result, []

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        result = skipped_result(args, f"video_open_failed: {args.video}")
        return result, []
    fps_video = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0
    image_width = float(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    image_height = float(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    try:
        with legacy_openmmlab_checkpoint_load():
            rtmpose = RTMPoseRunner(args.rtmpose_config, args.rtmpose_checkpoint, device="cpu")
        runner, load_time_ms = load_runner(args, 243)
    except Exception as exc:
        cap.release()
        result = skipped_result(args, f"runtime_unavailable: {type(exc).__name__}: {exc}")
        return result, []

    builder = MotionAGFormerWindowBuilder(window_size=243)
    rows = []
    normalized_frames = []
    frame_numbers = []
    processed = 0
    warmup_done = False
    warmup_time_ms = 0.0
    while processed < args.max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        t_rtmpose = time.perf_counter()
        try:
            coco = rtmpose.predict_keypoints(frame)
        except RTMPoseNoPersonDetectedError:
            processed += 1
            continue
        rtmpose_ms = elapsed_ms(t_rtmpose)
        normalized, adapter_ms = preprocess_one(coco, image_width, image_height)
        normalized_frames.append(normalized)
        frame_numbers.append(frame_idx)
        output_index = len(normalized_frames) - LOOKAHEAD - 1
        if output_index < 0:
            processed += 1
            continue
        sequence = np.stack(normalized_frames, axis=0)
        if not warmup_done:
            warmup_windows = build_warmup_windows(builder, sequence, min(args.warmup, len(sequence)))
            warmup_time_ms = warmup_runner(runner, warmup_windows, len(warmup_windows))
            warmup_done = True
        t_window = time.perf_counter()
        window, indices = builder.build_lookahead_padded(sequence, output_index, LOOKAHEAD)
        window_build_ms = elapsed_ms(t_window)
        inference_ms, pred = timed_call(runner, lambda: runner.predict_3d(window))
        t_post = time.perf_counter()
        output_idx = int(np.clip(window.shape[0] - LOOKAHEAD - 1, 0, window.shape[0] - 1))
        _ = motionagformer_angles(pred[output_idx])
        postprocess_ms = elapsed_ms(t_post)
        total_ms = rtmpose_ms + adapter_ms + window_build_ms + inference_ms + postprocess_ms
        rows.append(
            {
                "mode": args.mode,
                "frame_idx": int(frame_numbers[output_index]),
                "rtmpose_ms": rtmpose_ms,
                "adapter_preprocess_ms": adapter_ms,
                "window_build_ms": window_build_ms,
                "lifter_inference_ms": inference_ms,
                "postprocess_ms": postprocess_ms,
                "total_ms": total_ms,
                "batch_size": 1,
                "output_shape": list(pred.shape),
                "window_first_frame_idx": int(frame_numbers[indices[0]]),
                "window_last_frame_idx": int(frame_numbers[indices[-1]]),
            },
        )
        processed += 1
    cap.release()
    if not rows:
        result = skipped_result(args, "no_benchmark_rows")
        return result, rows
    result = build_result(
        args=args,
        rows=rows,
        timing_key="total_ms",
        fps_video=fps_video,
        device=runner.device_name,
        load_time_ms=load_time_ms,
        warmup_time_ms=warmup_time_ms,
        extra={
            "benchmark_kind": "rtmpose_adapter_window_lifter",
            "rtmpose": stats([row["rtmpose_ms"] for row in rows]),
            "adapter_preprocess": stats([row["adapter_preprocess_ms"] for row in rows]),
            "window_build": stats([row["window_build_ms"] for row in rows]),
            "lifter_inference": stats([row["lifter_inference_ms"] for row in rows]),
            "postprocess": stats([row["postprocess_ms"] for row in rows]),
        },
    )
    return result, rows


def load_runner(args, window_size):
    t0 = time.perf_counter()
    runner = MotionAGFormerRunner(
        repo_dir=args.motionagformer_repo,
        config_path=args.config,
        checkpoint_path=args.checkpoint,
        device=args.device,
        window_size=window_size,
    )
    return runner, elapsed_ms(t0)


def load_lookahead_windows(path, max_frames):
    if not path.exists():
        raise FileNotFoundError(f"input NPZ not found: {path}")
    data = np.load(path, allow_pickle=True)
    if "lookahead5_windows" not in data.files:
        raise ValueError(f"{path} missing lookahead5_windows")
    windows = np.asarray(data["lookahead5_windows"], dtype="float32")
    if max_frames > 0:
        windows = windows[:max_frames]
    fps_video = float(np.asarray(data["fps"])[0]) if "fps" in data.files else 30.0
    return windows, fps_video


def load_rtmpose_jsonl(path, max_frames):
    if not path.exists():
        raise FileNotFoundError(f"RTMPose JSONL not found: {path}")
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    valid = [row for row in rows if row.get("keypoints_coco17") is not None]
    if not valid:
        raise ValueError("No JSONL rows contain keypoints_coco17")
    first = valid[0]
    image_width = float(first["image_width"])
    image_height = float(first["image_height"])
    fps_video = infer_fps(rows)
    frame_numbers = []
    keypoints = []
    last = None
    for row in rows:
        if row.get("keypoints_coco17") is not None:
            last = np.asarray(row["keypoints_coco17"], dtype="float32")
        if last is None:
            continue
        frame_numbers.append(int(row["frame_idx"]))
        keypoints.append(last.copy())
        if max_frames > 0 and len(keypoints) >= max_frames:
            break
    return np.stack(keypoints, axis=0), image_width, image_height, np.asarray(frame_numbers, dtype=int), fps_video


def infer_fps(rows):
    timestamps = [float(row["timestamp_sec"]) for row in rows if "timestamp_sec" in row]
    if len(timestamps) >= 2 and timestamps[1] > timestamps[0]:
        return 1.0 / (timestamps[1] - timestamps[0])
    return 30.0


def preprocess_frames(raw_coco17, image_width, image_height):
    normalized = []
    rows = []
    for idx, coco in enumerate(raw_coco17):
        norm, adapter_ms = preprocess_one(coco, image_width, image_height)
        normalized.append(norm)
        rows.append({"frame_idx": idx, "adapter_preprocess_ms": adapter_ms})
    return np.stack(normalized, axis=0).astype("float32"), rows


def preprocess_one(coco, image_width, image_height):
    t0 = time.perf_counter()
    converted, confidences = coco17_to_motionagformer_h36m17(coco)
    normalized_xy = normalize_motionagformer_2d(converted, image_width, image_height)
    normalized = np.concatenate([normalized_xy, confidences[..., None]], axis=-1).astype("float32")
    return normalized, elapsed_ms(t0)


def build_warmup_windows(builder, sequence, warmup):
    count = min(int(warmup), len(sequence))
    if count <= 0:
        return np.empty((0, builder.window_size, 17, 3), dtype="float32")
    windows = []
    for idx in range(count):
        window, _ = builder.build_lookahead_padded(sequence, idx, LOOKAHEAD)
        windows.append(window)
    return np.stack(windows, axis=0).astype("float32")


def warmup_runner(runner, windows, warmup):
    count = min(int(warmup), len(windows))
    if count <= 0:
        return 0.0
    t0 = time.perf_counter()
    for window in windows[:count]:
        _ = runner.predict_3d(window)
    synchronize_if_cuda(runner)
    return elapsed_ms(t0)


def timed_call(runner, fn):
    synchronize_if_cuda(runner)
    t0 = time.perf_counter()
    value = fn()
    synchronize_if_cuda(runner)
    return elapsed_ms(t0), value


def synchronize_if_cuda(runner):
    if getattr(runner, "torch", None) is not None and str(getattr(runner, "device_name", "")) == "cuda":
        runner.torch.cuda.synchronize()


def elapsed_ms(start):
    return (time.perf_counter() - start) * 1000.0


def stats(values):
    arr = np.asarray([value for value in values if value is not None], dtype="float64")
    if arr.size == 0:
        return {
            "mean_ms": None,
            "median_ms": None,
            "p90_ms": None,
            "p95_ms": None,
            "min_ms": None,
            "max_ms": None,
        }
    return {
        "mean_ms": float(np.mean(arr)),
        "median_ms": float(np.median(arr)),
        "p90_ms": float(np.percentile(arr, 90)),
        "p95_ms": float(np.percentile(arr, 95)),
        "min_ms": float(np.min(arr)),
        "max_ms": float(np.max(arr)),
    }


def build_result(args, rows, timing_key, fps_video, device, load_time_ms, warmup_time_ms, extra=None):
    timing = stats([row[timing_key] for row in rows])
    mean_ms = timing["mean_ms"]
    fps = None if mean_ms is None or mean_ms <= 0 else 1000.0 / mean_ms
    latency_sec = LOOKAHEAD / float(fps_video if fps_video > 0 else 30.0)
    result = {
        "mode": args.mode,
        "device": device,
        "num_frames": len(rows),
        "model_load_time_ms": load_time_ms,
        "warmup_time_ms": warmup_time_ms,
        "algorithmic_latency_frames": LOOKAHEAD,
        "algorithmic_latency_sec_at_video_fps": latency_sec,
        "algorithmic_latency_sec_at_30fps": LOOKAHEAD / 30.0,
        "mean_ms": mean_ms,
        "median_ms": timing["median_ms"],
        "p90_ms": timing["p90_ms"],
        "p95_ms": timing["p95_ms"],
        "min_ms": timing["min_ms"],
        "max_ms": timing["max_ms"],
        "fps": fps,
        "realtime_30fps": bool(fps is not None and fps >= 30.0),
        "realtime_20fps": bool(fps is not None and fps >= 20.0),
        "timing_key": timing_key,
    }
    if extra:
        result.update(extra)
    return result


def skipped_result(args, reason):
    return {
        "mode": args.mode,
        "skipped": True,
        "reason": reason,
        "num_frames": 0,
        "algorithmic_latency_frames": LOOKAHEAD,
        "algorithmic_latency_sec_at_30fps": LOOKAHEAD / 30.0,
        "realtime_30fps": False,
        "realtime_20fps": False,
    }


def compact_summary(result):
    keys = [
        "mode",
        "device",
        "num_frames",
        "algorithmic_latency_frames",
        "algorithmic_latency_sec_at_30fps",
        "mean_ms",
        "median_ms",
        "p90_ms",
        "p95_ms",
        "fps",
        "realtime_30fps",
        "realtime_20fps",
    ]
    return {key: result.get(key) for key in keys if key in result}


def save_outputs(result, rows, json_path, csv_path):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump({"summary": result, "rows": rows}, fh, indent=2, sort_keys=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        if not fieldnames:
            fh.write("")
            return
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
