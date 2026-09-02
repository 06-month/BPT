"""Export the RTMPose-s forward-only module to ONNX for non-Apple machines.

Same scope and same trace as ``export_rtmpose_s_coreml.py``: MMPose's
``extract_feat + head`` only, fixed ``[1,3,256,192]`` input, ``simcc_x`` and
``simcc_y`` outputs. Preprocessing, SimCC decode and the inverse affine stay in
``bpt/benchmarks/pose/estimators/rtmpose.py``, so a CUDA run reproduces the
macOS Core ML numbers.

Requires MMPose plus the RTMPose-s config/checkpoint:

    python scripts/setup_rtmpose_s_model.py
    PYTHONPATH=. python3 scripts/export_rtmpose_s_onnx.py --out models/rtmpose_s_forward.onnx

Then verify the export against the Core ML package's contract:

    PYTHONPATH=. python3 scripts/export_rtmpose_s_onnx.py --verify-only \\
        --out models/rtmpose_s_forward.onnx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rtmpose_s_coreml_common import (  # noqa: E402
    INPUT_NAME,
    INPUT_SHAPE,
    OUTPUT_NAMES,
    TRACE_PATH,
    load_or_create_forward_input,
    load_rtmpose_model,
    trace_forward_model,
)

EXPECTED_SIMCC = {"simcc_x": 384, "simcc_y": 512}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="models/rtmpose_s_forward.onnx")
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--verify-only", action="store_true", help="skip export, only check an existing file")
    parser.add_argument("--tolerance", type=float, default=1e-3, help="max abs difference against PyTorch")
    return parser.parse_args()


def load_traced():
    if TRACE_PATH.exists():
        traced = torch.jit.load(str(TRACE_PATH))
        print(f"loaded existing trace: {TRACE_PATH}")
    else:
        model = load_rtmpose_model(device="cpu")
        traced = trace_forward_model(model)
        print("created a fresh trace from the MMPose checkpoint")
    traced.eval()
    return traced


def export(traced, out_path: Path, opset: int, sample: np.ndarray):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        traced,
        torch.from_numpy(sample),
        str(out_path),
        input_names=[INPUT_NAME],
        output_names=list(OUTPUT_NAMES),
        opset_version=opset,
        dynamic_axes=None,  # the M0 contract is a fixed [1,3,256,192] batch
    )
    print(f"wrote {out_path}")


def verify(out_path: Path, sample: np.ndarray, traced=None, tolerance: float = 1e-3) -> int:
    import onnxruntime as ort

    session = ort.InferenceSession(str(out_path), providers=["CPUExecutionProvider"])
    names = [output.name for output in session.get_outputs()]
    outputs = session.run(names, {session.get_inputs()[0].name: sample})
    shapes = {name: np.asarray(value).shape for name, value in zip(names, outputs)}
    print("onnx outputs:", shapes)
    for name, expected in EXPECTED_SIMCC.items():
        matching = [shape for shape in shapes.values() if shape[-1] == expected]
        if not matching:
            print(f"FAIL: no output with last dimension {expected} for {name}")
            return 1
    if traced is not None:
        with torch.no_grad():
            reference = traced(torch.from_numpy(sample))
        reference = [np.asarray(tensor) for tensor in reference]
        for produced, expected_tensor in zip(outputs, reference):
            difference = float(np.max(np.abs(np.asarray(produced) - expected_tensor)))
            print(f"max abs difference vs PyTorch: {difference:.2e}")
            if difference > tolerance:
                print(f"FAIL: difference exceeds {tolerance}")
                return 1
    print("PASS: ONNX export honours the SimCC contract")
    return 0


def main():
    args = parse_args()
    out_path = Path(args.out)
    sample = load_or_create_forward_input().astype(np.float32)
    if tuple(sample.shape) != INPUT_SHAPE:
        raise ValueError(f"expected {INPUT_SHAPE}, got {sample.shape}")
    if args.verify_only:
        return verify(out_path, sample, tolerance=args.tolerance)
    traced = load_traced()
    export(traced, out_path, args.opset, sample)
    return verify(out_path, sample, traced, tolerance=args.tolerance)


if __name__ == "__main__":
    raise SystemExit(main())
