"""Compare RTMPose-s PyTorch forward trace against Core ML forward outputs."""

import json
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from rtmpose_s_coreml_common import (  # noqa: E402
    COREML_MODEL_PATH,
    INPUT_NAME,
    OUTPUT_NAMES,
    TRACE_PATH,
    load_or_create_forward_input,
    shape_dict,
)


OUTPUT_JSON = ROOT / "assets/coreml/rtmpose_s_coreml_smoke.json"


def main():
    import coremltools as ct

    input_tensor = load_or_create_forward_input()
    traced = torch.jit.load(str(TRACE_PATH), map_location="cpu").eval()
    with torch.no_grad():
        torch_outputs = traced(torch.from_numpy(input_tensor))
    pytorch_values = outputs_to_numpy(torch_outputs)

    coreml_model = ct.models.MLModel(str(COREML_MODEL_PATH), compute_units=ct.ComputeUnit.ALL)
    pred = coreml_model.predict({INPUT_NAME: input_tensor.astype("float32", copy=False)})
    coreml_values = {name: np.asarray(pred[name], dtype="float32") for name in OUTPUT_NAMES}

    result = {
        "coreml_model_path": "assets/coreml/rtmpose_s_forward.mlpackage",
        "input_shape": list(input_tensor.shape),
        "pytorch_output_shapes": shape_dict(pytorch_values),
        "coreml_output_shapes": shape_dict(coreml_values),
        "max_abs_diff_per_output": {},
        "mean_abs_diff_per_output": {},
        "precision": coreml_model.user_defined_metadata.get("precision", "unknown"),
        "ane_verified": False,
    }
    for name in OUTPUT_NAMES:
        diff = np.abs(pytorch_values[name] - coreml_values[name])
        result["max_abs_diff_per_output"][name] = float(diff.max())
        result["mean_abs_diff_per_output"][name] = float(diff.mean())

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def outputs_to_numpy(outputs):
    if isinstance(outputs, torch.Tensor):
        outputs = (outputs,)
    return {
        name: value.detach().cpu().numpy().astype("float32")
        for name, value in zip(OUTPUT_NAMES, outputs)
    }


if __name__ == "__main__":
    raise SystemExit(main())
