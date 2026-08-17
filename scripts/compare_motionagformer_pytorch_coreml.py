"""Compare MotionAGFormer-XS PyTorch and Core ML outputs from JSONL input."""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.coreml_motionagformer import CoreMLMotionAGFormerRunner  # noqa: E402
from pose_feedback.body.live_motionagformer import run_live_motionagformer_sequence  # noqa: E402
from pose_feedback.body.motionagformer_runner import MotionAGFormerRunner  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pytorch-jsonl", required=True)
    parser.add_argument("--coreml-jsonl", required=True)
    parser.add_argument("--output-json", default="assets/smoke/motionagformer_pytorch_coreml_comparison.json")
    parser.add_argument("--motionagformer-coreml", default="assets/coreml/motionagformer_xs.mlpackage")
    parser.add_argument("--motionagformer-config", default="external/MotionAGFormer/configs/h36m/MotionAGFormer-xsmall.yaml")
    parser.add_argument("--motionagformer-checkpoint", default="external/MotionAGFormer/checkpoint/motionagformer-xs-h36m.pth.tr")
    parser.add_argument("--motionagformer-device", default="cpu")
    parser.add_argument("--lookahead", type=int, default=5)
    parser.add_argument("--image-width", type=int, default=None)
    parser.add_argument("--image-height", type=int, default=None)
    parser.add_argument("--max-frames", type=int, default=0)
    return parser.parse_args()


def main():
    args = parse_args()
    source_rows = load_rows(Path(args.pytorch_jsonl))
    coreml_rows = load_rows(Path(args.coreml_jsonl))
    sequence, frame_indices, image_w, image_h = load_motionagformer_input_sequence(
        source_rows,
        fallback_width=args.image_width,
        fallback_height=args.image_height,
        max_frames=args.max_frames,
    )
    result = {
        "pytorch_jsonl": args.pytorch_jsonl,
        "coreml_jsonl": args.coreml_jsonl,
        "image_width": image_w,
        "image_height": image_h,
        "input_frames": int(len(sequence)),
        "logged_output_comparison": compare_logged_outputs(source_rows, coreml_rows),
        "rerun_input_comparison": None,
        "coreml_vs_logged_pytorch_comparison": None,
        "ane_verified": False,
    }
    if sequence:
        result["coreml_vs_logged_pytorch_comparison"] = run_coreml_and_compare_logged_pytorch(
            args,
            sequence,
            frame_indices,
            image_w,
            image_h,
            source_rows,
        )
        if result["coreml_vs_logged_pytorch_comparison"].get("frames_compared", 0) == 0:
            result["rerun_input_comparison"] = rerun_and_compare(
                args,
                sequence,
                frame_indices,
                image_w,
                image_h,
            )

    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    coreml_logged = result.get("coreml_vs_logged_pytorch_comparison") or {}
    rerun = result.get("rerun_input_comparison") or {}
    logged = result.get("logged_output_comparison") or {}
    return 0 if coreml_logged.get("frames_compared") or rerun.get("frames_compared") or logged.get("frames_compared") else 1


def load_rows(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_motionagformer_input_sequence(rows, fallback_width=None, fallback_height=None, max_frames=0):
    sequence = []
    frame_indices = []
    image_w = fallback_width
    image_h = fallback_height
    for row in rows:
        value = row.get("motionagformer_input_2d")
        if value is None:
            continue
        if image_w is None:
            image_w = row.get("image_width")
        if image_h is None:
            image_h = row.get("image_height")
        arr = np.asarray(value, dtype="float32")
        if arr.shape != (17, 3):
            continue
        sequence.append(arr)
        frame_indices.append(int(row["frame_idx"]))
        if max_frames and len(sequence) >= max_frames:
            break
    if image_w is None or image_h is None:
        raise ValueError("image_width/image_height missing from JSONL; pass --image-width and --image-height")
    return sequence, frame_indices, int(image_w), int(image_h)


def rerun_and_compare(args, sequence, frame_indices, image_w, image_h):
    pytorch_start = time.perf_counter()
    pytorch_runner = MotionAGFormerRunner(
        repo_dir=str(ROOT / "external/MotionAGFormer"),
        config_path=str(ROOT / args.motionagformer_config),
        checkpoint_path=str(ROOT / args.motionagformer_checkpoint),
        device=args.motionagformer_device,
        window_size=27,
    )
    pytorch_load_ms = elapsed_ms(pytorch_start)
    pytorch_selected, _, _, _ = run_live_motionagformer_sequence(
        sequence,
        runner=pytorch_runner,
        image_width=image_w,
        image_height=image_h,
        lookahead=args.lookahead,
        window_size=27,
    )

    coreml_runner = CoreMLMotionAGFormerRunner(model_path=str(ROOT / args.motionagformer_coreml))
    coreml_selected, _, _, _ = run_live_motionagformer_sequence(
        sequence,
        runner=coreml_runner,
        image_width=image_w,
        image_height=image_h,
        lookahead=args.lookahead,
        window_size=27,
    )
    comparison = compare_arrays(pytorch_selected, coreml_selected)
    comparison.update(
        {
            "frames_compared": int(len(frame_indices)),
            "first_frame_index": int(frame_indices[0]),
            "last_frame_index": int(frame_indices[-1]),
            "pytorch_model_load_ms": pytorch_load_ms,
            "coreml_model_load_ms": coreml_runner.load_ms,
            "coreml_model_path": args.motionagformer_coreml,
            "coreml_precision_expected": "fp16",
        },
    )
    return comparison


def run_coreml_and_compare_logged_pytorch(args, sequence, frame_indices, image_w, image_h, source_rows):
    logged = body_3d_by_frame(source_rows)
    if not logged:
        return {"frames_compared": 0, "warning": "pytorch JSONL has no logged motionagformer_body_3d"}
    coreml_runner = CoreMLMotionAGFormerRunner(model_path=str(ROOT / args.motionagformer_coreml))
    coreml_selected, _, _, _ = run_live_motionagformer_sequence(
        sequence,
        runner=coreml_runner,
        image_width=image_w,
        image_height=image_h,
        lookahead=args.lookahead,
        window_size=27,
    )
    common_positions = [
        (position, frame_idx)
        for position, frame_idx in enumerate(frame_indices)
        if frame_idx in logged
    ]
    if not common_positions:
        return {"frames_compared": 0, "warning": "no logged PyTorch frames match input sequence"}
    pytorch_values = np.stack([logged[frame_idx] for _, frame_idx in common_positions]).astype("float32")
    coreml_values = np.stack([coreml_selected[position] for position, _ in common_positions]).astype("float32")
    comparison = compare_arrays(pytorch_values, coreml_values)
    comparison.update(
        {
            "frames_compared": int(len(common_positions)),
            "first_frame_index": int(common_positions[0][1]),
            "last_frame_index": int(common_positions[-1][1]),
            "pytorch_source": "logged_jsonl",
            "coreml_source": "rerun_from_motionagformer_input_2d",
            "coreml_model_load_ms": coreml_runner.load_ms,
            "coreml_model_path": args.motionagformer_coreml,
            "coreml_precision_expected": "fp16",
        },
    )
    return comparison


def compare_logged_outputs(pytorch_rows, coreml_rows):
    pytorch = body_3d_by_frame(pytorch_rows)
    coreml = body_3d_by_frame(coreml_rows)
    common = sorted(set(pytorch) & set(coreml))
    if not common:
        return {"frames_compared": 0, "warning": "no common logged motionagformer_body_3d frames"}
    pytorch_values = np.stack([pytorch[index] for index in common]).astype("float32")
    coreml_values = np.stack([coreml[index] for index in common]).astype("float32")
    result = compare_arrays(pytorch_values, coreml_values)
    result.update(
        {
            "frames_compared": int(len(common)),
            "first_frame_index": int(common[0]),
            "last_frame_index": int(common[-1]),
        },
    )
    return result


def body_3d_by_frame(rows):
    by_frame = {}
    for row in rows:
        body = row.get("motionagformer_body_3d")
        if body is None:
            continue
        arr = np.asarray(body, dtype="float32")
        if arr.shape == (17, 3):
            by_frame[int(row["frame_idx"])] = arr
    return by_frame


def compare_arrays(a, b):
    diff = np.abs(np.asarray(a, dtype="float32") - np.asarray(b, dtype="float32"))
    joint_l2 = np.linalg.norm(np.asarray(a, dtype="float32") - np.asarray(b, dtype="float32"), axis=-1)
    return {
        "max_abs_error": float(diff.max()),
        "mean_abs_error": float(diff.mean()),
        "p95_abs_error": float(np.percentile(diff, 95)),
        "mean_joint_l2_error": float(joint_l2.mean()),
        "p95_joint_l2_error": float(np.percentile(joint_l2, 95)),
        "per_joint_mean_l2_error": [float(value) for value in joint_l2.mean(axis=0)],
    }


def elapsed_ms(start):
    return (time.perf_counter() - start) * 1000.0


if __name__ == "__main__":
    raise SystemExit(main())
