"""Extract and inspect internal models in MediaPipe Pose Heavy .task.

The inspection prefers a real TFLite Interpreter so tensor shapes, dtypes, and
operator details come from the model runtime. If no interpreter is installed,
the script still extracts the models and records the exact inspection blocker.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mediapipe_pose_coreml_common import (  # noqa: E402
    EXTRACT_DIR,
    INSPECTION_JSON,
    TASK_MODEL_NAMES,
    TASK_PATH,
)


def main() -> int:
    result = {
        "task_path": rel(TASK_PATH),
        "task_exists": TASK_PATH.exists(),
        "extraction_dir": rel(EXTRACT_DIR),
        "expected_models": list(TASK_MODEL_NAMES),
        "models": [],
        "inspection_notes": [],
    }
    if not TASK_PATH.exists():
        result["inspection_notes"].append(f"missing task file: {TASK_PATH}")
        write_result(result)
        return 1

    extracted = extract_task_models()
    for path in extracted:
        result["models"].append(inspect_model(path))

    write_result(result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def extract_task_models() -> list[Path]:
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TASK_PATH) as archive:
        names = set(archive.namelist())
        missing = [name for name in TASK_MODEL_NAMES if name not in names]
        if missing:
            raise FileNotFoundError(f"missing task members: {missing}")
        extracted = []
        for name in TASK_MODEL_NAMES:
            output_path = EXTRACT_DIR / name
            output_path.write_bytes(archive.read(name))
            extracted.append(output_path)
        return extracted


def inspect_model(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    summary: dict[str, Any] = {
        "name": path.name,
        "path": rel(path),
        "role": role_from_name(path.name),
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "is_tflite_flatbuffer": data[4:8] == b"TFL3",
        "input_tensors": None,
        "output_tensors": None,
        "operators": None,
        "custom_op_presence": None,
        "dynamic_shape_presence": None,
        "inspection_backend": None,
        "inspection_error": None,
    }
    try:
        interpreter = make_interpreter(path)
        interpreter.allocate_tensors()
        inputs = tensor_details(interpreter.get_input_details())
        outputs = tensor_details(interpreter.get_output_details())
        operators = operator_details(interpreter)
        summary["input_tensors"] = inputs
        summary["output_tensors"] = outputs
        summary["operators"] = operators
        summary["custom_op_presence"] = any(str(op.get("op_name", "")).upper() == "CUSTOM" for op in operators)
        summary["dynamic_shape_presence"] = any(
            tensor_has_dynamic_shape(tensor)
            for tensor in list(inputs) + list(outputs)
        )
        summary["inspection_backend"] = "tflite_interpreter"
    except Exception as exc:  # noqa: BLE001
        summary["inspection_error"] = f"{type(exc).__name__}: {exc}"
        summary["inspection_backend"] = "unavailable"
        summary["fallback_strings"] = tflite_string_hints(data)
    return summary


def make_interpreter(path: Path):
    try:
        import tensorflow as tf

        return tf.lite.Interpreter(model_path=str(path))
    except Exception as tf_exc:  # noqa: BLE001
        try:
            from tflite_runtime.interpreter import Interpreter

            return Interpreter(model_path=str(path))
        except Exception as rt_exc:  # noqa: BLE001
            raise RuntimeError(
                "no TensorFlow Lite interpreter available "
                f"(tensorflow: {type(tf_exc).__name__}: {tf_exc}; "
                f"tflite_runtime: {type(rt_exc).__name__}: {rt_exc})",
            ) from rt_exc


def tensor_details(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in details:
        shape = item.get("shape")
        shape_signature = item.get("shape_signature")
        out.append(
            {
                "name": item.get("name"),
                "index": int(item.get("index", -1)),
                "shape": to_list(shape),
                "shape_signature": to_list(shape_signature),
                "dtype": str(item.get("dtype")),
                "quantization": to_list(item.get("quantization")),
            }
        )
    return out


def operator_details(interpreter: Any) -> list[dict[str, Any]]:
    get_ops = getattr(interpreter, "_get_ops_details", None)
    if get_ops is None:
        return []
    ops = []
    for op in get_ops():
        ops.append(
            {
                "op_name": op.get("op_name"),
                "inputs": to_list(op.get("inputs")),
                "outputs": to_list(op.get("outputs")),
            }
        )
    return ops


def tensor_has_dynamic_shape(tensor: dict[str, Any]) -> bool:
    sig = tensor.get("shape_signature")
    if sig is None:
        return False
    return any(int(dim) < 0 for dim in sig)


def tflite_string_hints(data: bytes) -> list[str]:
    # Minimal fallback when no TFLite schema/interpreter is available. This is
    # not authoritative; it is only useful for seeing embedded tensor names.
    text = data.decode("latin1", errors="ignore")
    candidates = []
    for token in ("serving_default", "Identity", "input", "output", "landmark", "score", "box"):
        if token in text:
            candidates.append(token)
    return candidates


def role_from_name(name: str) -> str:
    if "detector" in name and "landmark" not in name:
        return "pose_detector"
    if "landmark" in name:
        return "pose_landmark_model"
    return "unknown"


def to_list(value: Any):
    if value is None:
        return None
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return value
    return value


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_result(result: dict[str, Any]) -> None:
    INSPECTION_JSON.parent.mkdir(parents=True, exist_ok=True)
    INSPECTION_JSON.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
