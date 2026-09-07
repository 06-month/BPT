"""Core ML smoke test for MotionAGFormer-XS.

Loads the converted assets/coreml/motionagformer_xs.mlpackage, runs the same
real input window through the stock (unpatched) PyTorch XS model and the Core ML
model, and reports the numerical difference. Comparing the Core ML output (built
from the coreml_safe-patched graph) against the *original* PyTorch model is the
correct equivalence check, since the patch is meant to be numerically identical.

Writes assets/coreml/motionagformer_xs_coreml_smoke.json.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from motionagformer_coreml_safe import load_xs_model  # noqa: E402

INPUT_NPZ = ROOT / "assets/smoke/motionagformer_xs_s_test/inputs/vedio_1_motionagformer_xs_input.npz"
COREML_MODEL_PATH = ROOT / "assets/coreml/motionagformer_xs.mlpackage"
SMOKE_JSON_PATH = ROOT / "assets/coreml/motionagformer_xs_coreml_smoke.json"
INPUT_NAME = "input_2d_sequence"
OUTPUT_NAME = "pred_3d_sequence"


def main():
    import coremltools as ct

    window = load_one_window()
    torch_model = load_xs_model().eval()
    with torch.no_grad():
        pytorch_output = torch_model(torch.from_numpy(window)).detach().cpu().numpy().astype("float32")

    coreml_model = ct.models.MLModel(str(COREML_MODEL_PATH), compute_units=ct.ComputeUnit.ALL)
    start = time.perf_counter()
    pred = coreml_model.predict({INPUT_NAME: window.astype(np.float32)})
    prediction_ms = (time.perf_counter() - start) * 1000.0
    coreml_output = np.asarray(pred.get(OUTPUT_NAME, next(iter(pred.values()))), dtype="float32")

    diff = np.abs(pytorch_output - coreml_output)
    meta = coreml_model.user_defined_metadata
    result = {
        "coreml_model_path": "assets/coreml/motionagformer_xs.mlpackage",
        "input_shape": list(window.shape),
        "pytorch_output_shape": list(pytorch_output.shape),
        "coreml_output_shape": list(coreml_output.shape),
        "max_abs_diff": float(diff.max()),
        "mean_abs_diff": float(diff.mean()),
        "pytorch_output_min": float(pytorch_output.min()),
        "pytorch_output_max": float(pytorch_output.max()),
        "pytorch_output_mean": float(pytorch_output.mean()),
        "coreml_output_min": float(coreml_output.min()),
        "coreml_output_max": float(coreml_output.max()),
        "coreml_output_mean": float(coreml_output.mean()),
        "coreml_prediction_ms": float(prediction_ms),
        "precision": meta.get("precision", "unknown"),
        "export_mode": meta.get("export_mode", "unknown"),
        "ane_verified": False,
    }
    SMOKE_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    SMOKE_JSON_PATH.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def load_one_window():
    data = np.load(INPUT_NPZ, allow_pickle=True)
    windows = np.asarray(data["lookahead5_windows"], dtype="float32")
    window = windows[:1]
    if window.shape != (1, 27, 17, 3):
        raise ValueError(f"Expected one window with shape [1, 27, 17, 3], got {window.shape}")
    return window


if __name__ == "__main__":
    raise SystemExit(main())
