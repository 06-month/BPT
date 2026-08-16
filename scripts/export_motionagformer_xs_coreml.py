"""Export MotionAGFormer-XS to Core ML with a fixed [1, 27, 17, 3] input.

Two export modes:

* ``--export-mode original``  : trace the stock model unchanged. This is
  expected to FAIL Core ML conversion with a rank-6 reshape error (``op_87``).
* ``--export-mode coreml_safe``: apply the export-only attention patch from
  ``motionagformer_coreml_safe`` (keeps all tensors rank <= 5, numerically
  identical) and then convert.

Precision policy: try fp16 first, fall back to fp32. On success the model is
saved to assets/coreml/motionagformer_xs.mlpackage. On failure the exact
exception is written to a failure log (mode-specific filename) instead of being
silently skipped.
"""

import argparse
import shutil
import sys
import traceback
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from motionagformer_coreml_safe import apply_coreml_safe_attention, load_xs_model  # noqa: E402

OUTPUT_PATH = ROOT / "assets/coreml/motionagformer_xs.mlpackage"
FAILURE_PATH_ORIGINAL = ROOT / "assets/coreml/motionagformer_xs_coreml_conversion_failure.txt"
FAILURE_PATH_SAFE = ROOT / "assets/coreml/motionagformer_xs_coreml_conversion_failure_coreml_safe.txt"
INPUT_NAME = "input_2d_sequence"
OUTPUT_NAME = "pred_3d_sequence"


class _OneTensorMotionAGFormer(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, input_2d_sequence):
        return self.model(input_2d_sequence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--export-mode",
        choices=("original", "coreml_safe"),
        default="coreml_safe",
        help="original = stock model (rank-6, expected to fail); "
             "coreml_safe = rank<=5 attention patch (default).",
    )
    args = parser.parse_args()
    mode = args.export_mode
    failure_path = FAILURE_PATH_SAFE if mode == "coreml_safe" else FAILURE_PATH_ORIGINAL

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    model = load_xs_model().eval()

    if mode == "coreml_safe":
        n_patched = apply_coreml_safe_attention(model)
        print(f"export mode: coreml_safe (patched {n_patched} attention modules)")
    else:
        print("export mode: original (stock model, rank-6 reshape expected)")

    wrapped = _OneTensorMotionAGFormer(model).eval()
    dummy = torch.zeros(1, 27, 17, 3, dtype=torch.float32)

    with torch.no_grad():
        torch_output = wrapped(dummy)
    print(f"PyTorch forward output shape: {list(torch_output.shape)}")

    traced = torch.jit.trace(wrapped, dummy)
    traced.eval()
    print("torch.jit.trace status: succeeded")

    failures = []
    for precision in ("fp16", "fp32"):
        try:
            mlmodel = convert_traced_model(traced, precision)
            mlmodel.user_defined_metadata["precision"] = precision
            mlmodel.user_defined_metadata["export_mode"] = mode
            mlmodel.user_defined_metadata["source"] = (
                f"MotionAGFormer-XS fixed shape [1,27,17,3] ({mode})"
            )
            if OUTPUT_PATH.exists():
                if OUTPUT_PATH.is_dir():
                    shutil.rmtree(OUTPUT_PATH)
                else:
                    OUTPUT_PATH.unlink()
            mlmodel.save(str(OUTPUT_PATH))
            if failure_path.exists():
                failure_path.unlink()
            print(f"Core ML conversion status: succeeded ({precision})")
            print(f"saved: {OUTPUT_PATH.relative_to(ROOT)}")
            return 0
        except Exception:
            failure = f"=== {mode} {precision} conversion failure ===\n{traceback.format_exc()}"
            failures.append(failure)
            print(f"Core ML conversion status: failed ({precision})")

    failure_path.write_text("\n\n".join(failures), encoding="utf-8")
    print("Core ML conversion status: failed")
    print(f"failure log: {failure_path.relative_to(ROOT)}")
    return 1


def convert_traced_model(traced, precision):
    import coremltools as ct

    compute_precision = ct.precision.FLOAT16 if precision == "fp16" else ct.precision.FLOAT32
    return ct.convert(
        traced,
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.iOS16,
        inputs=[ct.TensorType(name=INPUT_NAME, shape=(1, 27, 17, 3), dtype=np.float32)],
        outputs=[ct.TensorType(name=OUTPUT_NAME)],
        compute_precision=compute_precision,
    )


if __name__ == "__main__":
    raise SystemExit(main())
