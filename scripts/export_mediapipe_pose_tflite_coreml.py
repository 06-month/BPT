"""Attempt Core ML conversion for MediaPipe Pose Landmarker TFLite forwards.

This is a feasibility probe. It targets the two packaged TFLite neural-network
files inside ``assets/mediapipe/pose_landmarker_heavy.task`` and intentionally
excludes MediaPipe Tasks calculators, tracking, ROI generation, and landmark
decode.
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

from inspect_mediapipe_pose_task_coreml_path import extract_task_models  # noqa: E402
from mediapipe_pose_coreml_common import (  # noqa: E402
    CONVERSION_FAILURE_PATH,
    CONVERSION_REPORT_PATH,
    POSE_DETECTOR_COREML,
    POSE_DETECTOR_TFLITE,
    POSE_LANDMARKS_COREML,
    POSE_LANDMARKS_TFLITE,
)


TARGETS = (
    {
        "name": "pose_detector",
        "source": POSE_DETECTOR_TFLITE,
        "output": POSE_DETECTOR_COREML,
        "scope": "MediaPipe Pose detector TFLite forward only",
    },
    {
        "name": "pose_landmarks_detector_heavy",
        "source": POSE_LANDMARKS_TFLITE,
        "output": POSE_LANDMARKS_COREML,
        "scope": "MediaPipe Pose heavy landmark TFLite forward only",
    },
)


def main():
    extract_task_models()
    results = []
    failures = []
    route_status = {
        "route_a_direct_coremltools": {
            "attempted": True,
            "succeeded": False,
            "note": "Direct coremltools conversion from TFLite file path.",
        },
        "route_b_tflite_to_savedmodel_to_coreml": {
            "attempted": True,
            "succeeded": False,
            "note": bridge_route_status(),
        },
        "route_c_document_blockers": {
            "attempted": True,
            "succeeded": True,
            "note": "Failure report is written when conversion cannot produce runnable Core ML models.",
        },
    }

    for target in TARGETS:
        target_result, target_failures = convert_target(target)
        results.append(target_result)
        failures.extend(target_failures)

    succeeded = all(result["converted"] for result in results)
    route_status["route_a_direct_coremltools"]["succeeded"] = succeeded
    summary = {
        "converted_all": succeeded,
        "targets": results,
        "routes": route_status,
        "ane_verified": False,
        "note": "Only TFLite neural-network forwards are targeted; MediaPipe preprocessing/postprocess remain outside Core ML.",
    }

    write_markdown_report(summary, failures)
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
            "Use TensorFlow SavedModel/ONNX versions of the MediaPipe Pose detector and landmark models, "
            "or add a dedicated TFLite-to-CoreML bridge in an isolated conversion environment."
        ),
    ]
    CONVERSION_FAILURE_PATH.write_text("\n".join(failure_text), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"failure log: {CONVERSION_FAILURE_PATH.relative_to(ROOT)}")
    return 1


def bridge_route_status():
    missing = []
    for module_name in ("tensorflow", "tflite_runtime"):
        try:
            __import__(module_name)
        except Exception as exc:  # noqa: BLE001
            missing.append(f"{module_name}: {type(exc).__name__}: {exc}")
    if missing:
        return (
            "Bridge not available locally. TFLite to TensorFlow SavedModel/concrete-function "
            "conversion requires additional tooling that is not installed: "
            + "; ".join(missing)
        )
    return (
        "TensorFlow/TFLite runtime is importable, but this script does not have a verified "
        "lossless TFLite-to-SavedModel reconstruction path for MediaPipe Pose."
    )


def write_markdown_report(summary, failures):
    lines = [
        "# MediaPipe Pose Heavy Core ML Conversion Report",
        "",
        "## Scope",
        "",
        "This experiment targets only the two neural-network forwards packaged in "
        "`assets/mediapipe/pose_landmarker_heavy.task`: `pose_detector.tflite` "
        "and `pose_landmarks_detector.tflite`. The MediaPipe Tasks calculators, "
        "tracking, ROI generation, landmark decode, and smoothing are not Core ML "
        "models and must be reimplemented separately.",
        "",
        "## Route Status",
    ]
    for name, info in summary["routes"].items():
        lines.append(f"- {name}: attempted=`{info['attempted']}`, succeeded=`{info['succeeded']}`")
        lines.append(f"  - {info['note']}")
    lines.extend(["", "## Target Status"])
    for target in summary["targets"]:
        lines.append(
            f"- {target['name']}: converted=`{target['converted']}`, "
            f"source=`{target['source']}`, output=`{target['output']}`"
        )
    lines.extend(
        [
            "",
            "## Feasibility Decision",
            "",
            f"- converted_all: `{summary['converted_all']}`",
            "- ane_verified: `False`",
        ]
    )
    if not summary["converted_all"]:
        lines.extend(
            [
                "- blocker_class: `conversion issue`",
                "- current_blocker: local coremltools cannot convert TFLite directly, "
                "and no verified TFLite-to-SavedModel bridge is installed.",
            ]
        )
    if failures:
        lines.extend(["", "## Exceptions"])
        for failure in failures:
            lines.extend(["```text", failure.strip(), "```", ""])
    CONVERSION_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONVERSION_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


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
        except Exception:  # noqa: BLE001
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
