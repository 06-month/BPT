"""Inspect MediaPipe Hand Landmarker .task Core ML conversion feasibility.

This script intentionally does not convert the full MediaPipe graph. It extracts
the packaged TFLite neural-network assets and records what would remain outside
Core ML if those tensor forwards are converted.
"""

import hashlib
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mediapipe_hand_coreml_common import (  # noqa: E402
    EXTRACT_DIR,
    INSPECTION_JSON,
    TASK_MODEL_NAMES,
    TASK_PATH,
)


def main():
    result = base_result()

    try:
        import coremltools as ct

        result["coremltools_version"] = ct.__version__
        result["coremltools_direct_tflite_hint"] = "tflite" in (ct.convert.__doc__ or "").lower()
    except Exception as exc:
        result["coremltools_import_error"] = f"{type(exc).__name__}: {exc}"

    try:
        extracted = extract_task_models()
        result["task_exists"] = True
        result["task_members"] = list_task_members()
        result["extracted_models"] = [model_summary(path) for path in extracted]
    except Exception as exc:
        result["task_error"] = f"{type(exc).__name__}: {exc}"

    INSPECTION_JSON.parent.mkdir(parents=True, exist_ok=True)
    INSPECTION_JSON.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def base_result():
    return {
        "task_path": str(TASK_PATH.relative_to(ROOT)),
        "task_exists": TASK_PATH.exists(),
        "conversion_scope": "MediaPipe hand detector and landmark TFLite neural-network forwards only",
        "not_in_scope": [
            "full MediaPipe Tasks graph conversion",
            "RTMPose Core ML reconversion",
            "MotionAGFormer-XS Core ML reconversion",
            "camera integration",
            "feedback, scoring, or rep phase logic",
        ],
        "expected_task_models": list(TASK_MODEL_NAMES),
        "postprocess_outside_coreml": [
            "RTMPose wrist-based hand crop generation",
            "crop clamping and image resize/normalization",
            "MediaPipe detector decode and ROI tracking if the detector model is used",
            "landmark tensor decode to 21 normalized image landmarks",
            "world landmark interpretation and wrist-relative hand shape attachment",
            "crop-local to original-frame coordinate mapping",
            "left/right side ownership from RTMPose wrists",
        ],
        "coreml_conversion_risk_notes": [
            "MediaPipe .task is a packaged graph with TFLite models, not a Core ML model.",
            "Converting the TFLite model forwards would not convert MediaPipe Tasks tracking or calculators.",
            "coremltools 9 does not advertise direct TFLite conversion in the local environment.",
            "A TensorFlow SavedModel, ONNX export, or a dedicated TFLite conversion bridge may be required.",
            "Core ML conversion success would not imply ANE execution.",
        ],
        "ane_verified": False,
    }


def list_task_members():
    with zipfile.ZipFile(TASK_PATH) as archive:
        return [
            {
                "name": info.filename,
                "size_bytes": info.file_size,
            }
            for info in archive.infolist()
        ]


def extract_task_models():
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(TASK_PATH) as archive:
        names = set(archive.namelist())
        missing = [name for name in TASK_MODEL_NAMES if name not in names]
        if missing:
            raise FileNotFoundError(f"missing task members: {missing}")
        for name in TASK_MODEL_NAMES:
            output_path = EXTRACT_DIR / name
            output_path.write_bytes(archive.read(name))
            extracted.append(output_path)
    return extracted


def model_summary(path):
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(ROOT)),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "is_tflite_flatbuffer": data[4:8] == b"TFL3",
    }


if __name__ == "__main__":
    raise SystemExit(main())
