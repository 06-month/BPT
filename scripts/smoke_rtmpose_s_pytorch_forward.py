"""Run RTMPose-s PyTorch neural-network forward smoke test."""

import json
import statistics
import sys
import time
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rtmpose_s_coreml_common import (  # noqa: E402
    CHECKPOINT_PATH,
    CONFIG_PATH,
    FORWARD_INPUT_NPY,
    TRACE_PATH,
    forward_output_dict,
    load_rtmpose_model,
    prepare_input_tensor_from_frame,
    read_first_video_frame,
    save_forward_input,
    shape_dict,
    stats_dict,
    trace_forward_model,
)


OUTPUT_JSON = ROOT / "assets/coreml/rtmpose_s_pytorch_forward_smoke.json"
WARMUP = 3
ITERATIONS = 20


def main():
    model = load_rtmpose_model(device="cpu")
    input_tensor = prepare_input_tensor_from_frame(read_first_video_frame())
    save_forward_input(input_tensor)
    tensor = torch.from_numpy(input_tensor)

    with torch.no_grad():
        raw_outputs = model.head(model.extract_feat(tensor))
    output_values = {
        name: value.detach().cpu().numpy().astype("float32")
        for name, value in forward_output_dict(raw_outputs).items()
    }

    for _ in range(WARMUP):
        with torch.no_grad():
            model.head(model.extract_feat(tensor))

    times = []
    for _ in range(ITERATIONS):
        start = time.perf_counter()
        with torch.no_grad():
            model.head(model.extract_feat(tensor))
        times.append((time.perf_counter() - start) * 1000.0)

    traced = trace_forward_model(model, input_tensor)
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    traced.save(str(TRACE_PATH))

    result = {
        "config_path": str(CONFIG_PATH.relative_to(ROOT)),
        "checkpoint_path": str(CHECKPOINT_PATH.relative_to(ROOT)),
        "model_loaded": True,
        "forward_scope": "model.extract_feat + model.head only",
        "input_tensor_path": str(FORWARD_INPUT_NPY.relative_to(ROOT)),
        "torchscript_trace_path": str(TRACE_PATH.relative_to(ROOT)),
        "input_tensor_shape": list(input_tensor.shape),
        "raw_output_shapes": shape_dict(output_values),
        "raw_output_stats": stats_dict(output_values),
        "warmup_count": WARMUP,
        "iteration_count": ITERATIONS,
        "mean_ms": float(statistics.mean(times)),
        "median_ms": float(statistics.median(times)),
        "min_ms": float(min(times)),
        "max_ms": float(max(times)),
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(f"input tensor shape: {result['input_tensor_shape']}")
    print(f"raw output tensor shapes: {result['raw_output_shapes']}")
    for name, stats in result["raw_output_stats"].items():
        print(f"{name} min/max/mean: {stats['min']:.8f} / {stats['max']:.8f} / {stats['mean']:.8f}")
    print(f"mean ms/forward: {result['mean_ms']:.4f}")
    print(f"median ms/forward: {result['median_ms']:.4f}")
    print(f"saved: {OUTPUT_JSON.relative_to(ROOT)}")
    print(f"saved trace: {TRACE_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
