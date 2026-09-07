"""Attempt Core ML conversion for MediaPipe Hand Landmarker TFLite forwards.

This is a feasibility probe. It targets the two packaged TFLite neural-network
files inside ``assets/mediapipe/hand_landmarker.task`` and intentionally excludes
MediaPipe Tasks calculators, tracking, crop generation, and landmark decode.
"""

import json
import shutil
import sys
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from inspect_mediapipe_hand_task_coreml_path import extract_task_models  # noqa: E402
from mediapipe_hand_coreml_common import (  # noqa: E402
    CONVERSION_FAILURE_PATH,
    HAND_DETECTOR_COREML,
    HAND_DETECTOR_TFLITE,
    HAND_LANDMARKS_COREML,
    HAND_LANDMARKS_TFLITE,
)


TARGETS = (
    {
        "name": "hand_detector",
        "source": HAND_DETECTOR_TFLITE,
        "output": HAND_DETECTOR_COREML,
        "scope": "MediaPipe palm/hand detector TFLite forward only",
    },
    {
        "name": "hand_landmarks_detector",
        "source": HAND_LANDMARKS_TFLITE,
        "output": HAND_LANDMARKS_COREML,
        "scope": "MediaPipe hand landmark TFLite forward only",
    },
)


def main():
    extract_task_models()
    results = []
    failures = []

    for target in TARGETS:
        target_result, target_failures = convert_target(target)
        results.append(target_result)
        failures.extend(target_failures)

    succeeded = all(result["converted"] for result in results)
    summary = {
        "converted_all": succeeded,
        "targets": results,
        "ane_verified": False,
        "note": "Only TFLite neural-network forwards are targeted; MediaPipe preprocessing/postprocess remain outside Core ML.",
    }

    if succeeded:
        if CONVERSION_FAILURE_PATH.exists():
            CONVERSION_FAILURE_PATH.unlink()
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    CONVERSION_FAILURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    failure_text = [
        json.dumps(summary, indent=2, sort_keys=True),
        "",
        "=== full conversion exceptions ===",
        "\n\n".join(failures),
        "",
        "=== likely next step ===",
        (
            "The local coremltools environment does not provide a direct TFLite conversion path. "
            "Use a TensorFlow SavedModel/ONNX export of the hand detector and landmark models, "
            "or add a dedicated TFLite-to-CoreML bridge in an isolated conversion environment."
        ),
    ]
    CONVERSION_FAILURE_PATH.write_text("\n".join(failure_text), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"failure log: {CONVERSION_FAILURE_PATH.relative_to(ROOT)}")
    return 1


def convert_target(target):
    failures = []
    result = {
        "name": target["name"],
        "source": str(target["source"].relative_to(ROOT)),
        "output": str(target["output"].relative_to(ROOT)),
        "scope": target["scope"],
        "converted": False,
        "precision": None,
    }

    for precision in ("fp16", "fp32"):
        try:
            mlmodel = convert_tflite(target["source"], precision)
            mlmodel.user_defined_metadata["precision"] = precision
            mlmodel.user_defined_metadata["export_scope"] = target["scope"]
            mlmodel.user_defined_metadata["ane_verified"] = "false"
            save_model(mlmodel, target["output"])
            result["converted"] = True
            result["precision"] = precision
            return result, failures
        except Exception:
            failures.append(
                f"=== {target['name']} {precision} conversion failure ===\n"
                f"{traceback.format_exc()}"
            )

    return result, failures


def convert_tflite(path, precision):
    import coremltools as ct

    compute_precision = ct.precision.FLOAT16 if precision == "fp16" else ct.precision.FLOAT32
    return ct.convert(
        str(path),
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.iOS16,
        compute_precision=compute_precision,
    )


def save_model(mlmodel, output_path):
    if output_path.exists():
        if output_path.is_dir():
            shutil.rmtree(output_path)
        else:
            output_path.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mlmodel.save(str(output_path))


if __name__ == "__main__":
    raise SystemExit(main())
