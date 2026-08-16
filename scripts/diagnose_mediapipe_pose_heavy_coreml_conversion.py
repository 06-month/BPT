"""Diagnose MediaPipe Pose Heavy TFLite to Core ML conversion routes.

This script is intentionally isolated from production pose/feedback code. It
does not create placeholder models and only reports Core ML success when a real
model package is produced and loadable.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata as metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import textwrap
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from mediapipe_pose_coreml_common import (  # noqa: E402
    COREML_DIR,
    OUTPUT_DIR,
    POSE_DETECTOR_COREML,
    POSE_DETECTOR_TFLITE,
    POSE_LANDMARKS_COREML,
    POSE_LANDMARKS_TFLITE,
)


ENV_REPORT = OUTPUT_DIR / "mediapipe_pose_heavy_coreml_env_report.md"
TFLITE_INSPECTION_JSON = OUTPUT_DIR / "mediapipe_pose_heavy_tflite_inspection.json"
TFLITE_INSPECTION_MD = OUTPUT_DIR / "mediapipe_pose_heavy_tflite_inspection.md"
FINAL_BLOCKER_REPORT = OUTPUT_DIR / "mediapipe_pose_heavy_coreml_final_blocker_report.md"
LOG_DIR = OUTPUT_DIR / "mediapipe_pose_heavy_coreml_logs"
INTERMEDIATE_DIR = OUTPUT_DIR / "mediapipe_pose_heavy_intermediate"


TARGETS = (
    {
        "name": "pose_detector",
        "tflite": POSE_DETECTOR_TFLITE,
        "coreml": POSE_DETECTOR_COREML,
        "dummy_kind": "detector",
    },
    {
        "name": "pose_landmarks_detector",
        "tflite": POSE_LANDMARKS_TFLITE,
        "coreml": POSE_LANDMARKS_COREML,
        "dummy_kind": "landmark",
    },
)


PACKAGE_NAMES = (
    "coremltools",
    "tensorflow",
    "tensorflow-macos",
    "tflite_runtime",
    "tf2onnx",
    "onnx",
    "onnxruntime",
    "onnx-coreml",
    "tflite2tensorflow",
    "numpy",
    "protobuf",
    "flatbuffers",
)


@dataclass
class RouteResult:
    name: str
    attempted: bool = False
    succeeded: bool = False
    command: str | None = None
    log_path: str | None = None
    failure_class: str | None = None
    message: str | None = None
    produced_files: list[str] = field(default_factory=list)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-conversion", action="store_true")
    parser.add_argument("--run-direct-coremltools", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--run-tf2onnx", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--run-tflite2tensorflow", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    COREML_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

    env = collect_environment()
    write_env_report(env)
    inspection = inspect_tflite_models()
    write_tflite_inspection(inspection)

    routes: list[RouteResult] = []
    if not args.skip_conversion:
        if args.run_direct_coremltools:
            routes.extend(run_direct_coremltools_routes())
        routes.extend(run_savedmodel_coreml_routes())
        if args.run_tf2onnx:
            routes.extend(run_tf2onnx_routes())
        if args.run_tflite2tensorflow:
            routes.extend(run_tflite2tensorflow_routes())
        routes.append(document_tflite_coreml_delegate())

    summary = {
        "environment": env,
        "inspection": inspection,
        "routes": [asdict(route) for route in routes],
        "converted_detector": POSE_DETECTOR_COREML.exists(),
        "converted_landmark": POSE_LANDMARKS_COREML.exists(),
        "converted_all": POSE_DETECTOR_COREML.exists() and POSE_LANDMARKS_COREML.exists(),
    }
    write_final_report(summary)
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))
    return 0 if summary["converted_all"] else 2


def collect_environment() -> dict[str, Any]:
    packages = {}
    for name in PACKAGE_NAMES:
        try:
            packages[name] = metadata.version(name)
        except Exception as exc:  # noqa: BLE001
            packages[name] = f"MISSING ({type(exc).__name__})"

    imports = {}
    for module_name in (
        "coremltools",
        "tensorflow",
        "tflite_runtime.interpreter",
        "tf2onnx",
        "onnx",
        "onnxruntime",
        "onnx_coreml",
        "tflite2tensorflow",
    ):
        try:
            module = importlib.import_module(module_name)
            imports[module_name] = {
                "available": True,
                "version": getattr(module, "__version__", None),
            }
        except Exception as exc:  # noqa: BLE001
            imports[module_name] = {
                "available": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    docker_daemon = None
    if shutil.which("docker"):
        try:
            proc = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}} {{.Architecture}}"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            docker_daemon = {
                "available": proc.returncode == 0,
                "stdout": (proc.stdout or "").strip(),
                "stderr": (proc.stderr or "").strip(),
                "returncode": proc.returncode,
            }
        except Exception as exc:  # noqa: BLE001
            docker_daemon = {
                "available": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    return {
        "python_executable": sys.executable,
        "python_version": sys.version.replace("\n", " "),
        "conda_default_env": os.environ.get("CONDA_DEFAULT_ENV"),
        "platform": platform.platform(),
        "mac_ver": platform.mac_ver(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "packages": packages,
        "imports": imports,
        "docker_binary": shutil.which("docker"),
        "docker_daemon": docker_daemon,
        "flatc_binary": shutil.which("flatc"),
        "tflite2tensorflow_binary": shutil.which("tflite2tensorflow"),
    }


def write_env_report(env: dict[str, Any]) -> None:
    lines = [
        "# MediaPipe Pose Heavy Core ML Environment Report",
        "",
        f"- Python executable: `{env['python_executable']}`",
        f"- Python version: `{env['python_version']}`",
        f"- Conda env: `{env['conda_default_env']}`",
        f"- Platform: `{env['platform']}`",
        f"- macOS: `{env['mac_ver']}`",
        f"- Machine: `{env['machine']}`",
        f"- Processor: `{env['processor']}`",
        f"- Docker binary: `{env['docker_binary']}`",
        f"- Docker daemon: `{env['docker_daemon']}`",
        f"- flatc binary: `{env['flatc_binary']}`",
        f"- tflite2tensorflow binary: `{env['tflite2tensorflow_binary']}`",
        "",
        "## Packages",
    ]
    for name, version in env["packages"].items():
        lines.append(f"- {name}: `{version}`")
    lines.extend(["", "## Imports"])
    for name, info in env["imports"].items():
        lines.append(f"- {name}: `{info}`")
    ENV_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def inspect_tflite_models() -> dict[str, Any]:
    interpreter_factory, interpreter_source, import_error = get_tflite_interpreter_factory()
    results = {
        "interpreter_source": interpreter_source,
        "interpreter_import_error": import_error,
        "models": {},
    }
    for target in TARGETS:
        model_path = target["tflite"]
        model_result: dict[str, Any] = {
            "path": str(model_path.relative_to(ROOT)),
            "exists": model_path.exists(),
            "size_bytes": model_path.stat().st_size if model_path.exists() else None,
            "inspection_available": False,
        }
        if interpreter_factory is None:
            model_result["error"] = "No TensorFlow Lite Interpreter available"
            results["models"][target["name"]] = model_result
            continue
        try:
            interpreter = interpreter_factory(str(model_path))
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()
            model_result["input_tensors"] = tensor_details_for_json(input_details)
            model_result["output_tensors"] = tensor_details_for_json(output_details)
            model_result["dynamic_tensors"] = dynamic_tensor_names(input_details + output_details)
            try:
                ops = interpreter._get_ops_details()  # noqa: SLF001
                model_result["operators"] = [op.get("op_name") for op in ops]
                model_result["custom_ops"] = [
                    op.get("op_name")
                    for op in ops
                    if "CUSTOM" in str(op.get("op_name", "")).upper()
                ]
            except Exception as exc:  # noqa: BLE001
                model_result["operators_error"] = f"{type(exc).__name__}: {exc}"
            dummy = run_tflite_dummy_inference(interpreter, input_details, output_details)
            model_result.update(dummy)
            model_result["inspection_available"] = True
        except Exception as exc:  # noqa: BLE001
            model_result["error"] = traceback.format_exc()
        results["models"][target["name"]] = model_result
    return results


def get_tflite_interpreter_factory():
    try:
        import tensorflow as tf

        return tf.lite.Interpreter, "tensorflow.lite.Interpreter", None
    except Exception as tf_exc:  # noqa: BLE001
        try:
            from tflite_runtime.interpreter import Interpreter

            return Interpreter, "tflite_runtime.Interpreter", None
        except Exception as tflite_exc:  # noqa: BLE001
            return (
                None,
                None,
                {
                    "tensorflow": f"{type(tf_exc).__name__}: {tf_exc}",
                    "tflite_runtime": f"{type(tflite_exc).__name__}: {tflite_exc}",
                },
            )


def tensor_details_for_json(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in details:
        out.append(
            {
                "name": item.get("name"),
                "index": int(item.get("index")),
                "shape": np_list(item.get("shape")),
                "shape_signature": np_list(item.get("shape_signature")),
                "dtype": str(item.get("dtype")),
                "quantization": item.get("quantization"),
                "quantization_parameters": _json_safe(item.get("quantization_parameters")),
            }
        )
    return out


def dynamic_tensor_names(details: list[dict[str, Any]]) -> list[str]:
    names = []
    for item in details:
        signature = item.get("shape_signature")
        if signature is not None and any(int(value) < 0 for value in signature):
            names.append(str(item.get("name")))
    return names


def run_tflite_dummy_inference(interpreter: Any, input_details: list[dict[str, Any]], output_details: list[dict[str, Any]]) -> dict[str, Any]:
    interpreter.allocate_tensors()
    dummy_inputs = []
    for detail in input_details:
        shape = [int(dim) if int(dim) > 0 else 1 for dim in detail["shape"]]
        dtype = detail["dtype"]
        if "int" in str(dtype):
            value = getattr(dtype, "type", dtype)(0)
            tensor = zeros_array(shape, dtype=dtype) + value
        else:
            tensor = zeros_array(shape, dtype=dtype)
        interpreter.set_tensor(detail["index"], tensor)
        dummy_inputs.append({"name": detail["name"], "shape": shape, "dtype": str(dtype)})
    interpreter.invoke()
    outputs = []
    for detail in output_details:
        tensor = interpreter.get_tensor(detail["index"])
        outputs.append(
            {
                "name": detail["name"],
                "shape": list(tensor.shape),
                "dtype": str(tensor.dtype),
                "min": float(tensor.min()) if tensor.size else None,
                "max": float(tensor.max()) if tensor.size else None,
            }
        )
    return {
        "dummy_inference_succeeded": True,
        "dummy_inputs": dummy_inputs,
        "dummy_outputs": outputs,
    }


def zeros_array(shape: list[int], dtype: Any):
    import numpy as np

    return np.zeros(shape, dtype=dtype)


def write_tflite_inspection(inspection: dict[str, Any]) -> None:
    TFLITE_INSPECTION_JSON.write_text(json.dumps(_json_safe(inspection), indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# MediaPipe Pose Heavy TFLite Inspection",
        "",
        f"- Interpreter source: `{inspection.get('interpreter_source')}`",
        f"- Interpreter import error: `{inspection.get('interpreter_import_error')}`",
    ]
    for name, info in inspection["models"].items():
        lines.extend(
            [
                "",
                f"## {name}",
                f"- Path: `{info.get('path')}`",
                f"- Exists: `{info.get('exists')}`",
                f"- Size bytes: `{info.get('size_bytes')}`",
                f"- Inspection available: `{info.get('inspection_available')}`",
            ]
        )
        if info.get("error"):
            lines.extend(["", "### Error", "```text", str(info["error"]).strip(), "```"])
        if info.get("input_tensors"):
            lines.extend(["", "### Inputs"])
            for item in info["input_tensors"]:
                lines.append(f"- `{item['name']}` shape={item['shape']} dtype={item['dtype']} quant={item['quantization']}")
        if info.get("output_tensors"):
            lines.extend(["", "### Outputs"])
            for item in info["output_tensors"]:
                lines.append(f"- `{item['name']}` shape={item['shape']} dtype={item['dtype']} quant={item['quantization']}")
        if info.get("operators"):
            lines.extend(["", "### Operators"])
            lines.append(", ".join(str(op) for op in info["operators"]))
        if info.get("dummy_outputs"):
            lines.extend(["", "### Dummy Outputs"])
            for item in info["dummy_outputs"]:
                lines.append(f"- `{item['name']}` shape={item['shape']} dtype={item['dtype']} min={item['min']} max={item['max']}")
    TFLITE_INSPECTION_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_direct_coremltools_routes() -> list[RouteResult]:
    routes = []
    try:
        import coremltools as ct
    except Exception as exc:  # noqa: BLE001
        return [
            RouteResult(
                name="direct_coremltools",
                attempted=False,
                failure_class="missing_converter_tool",
                message=f"coremltools import failed: {type(exc).__name__}: {exc}",
            )
        ]

    for target in TARGETS:
        log_path = LOG_DIR / f"{target['name']}_direct_coremltools.log"
        route = RouteResult(name=f"{target['name']}: direct TFLite -> CoreML", attempted=True, log_path=str(log_path.relative_to(ROOT)))
        try:
            model = ct.convert(
                str(target["tflite"]),
                convert_to="mlprogram",
                minimum_deployment_target=ct.target.iOS16,
            )
            target["coreml"].parent.mkdir(parents=True, exist_ok=True)
            model.save(str(target["coreml"]))
            _load_coreml_model(target["coreml"])
            route.succeeded = True
            route.produced_files.append(str(target["coreml"].relative_to(ROOT)))
            log_path.write_text("direct coremltools conversion succeeded\n", encoding="utf-8")
        except Exception:  # noqa: BLE001
            error = traceback.format_exc()
            route.failure_class = "unsupported_source_framework"
            route.message = _first_error_line(error)
            log_path.write_text(error, encoding="utf-8")
        routes.append(route)
    return routes


def run_savedmodel_coreml_routes() -> list[RouteResult]:
    # TensorFlow can run TFLite but does not provide a native lossless
    # TFLite-to-SavedModel reconstruction API. A third-party bridge such as
    # tflite2tensorflow is required, so this route records that distinction.
    try:
        import tensorflow  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return [
            RouteResult(
                name="TFLite -> SavedModel -> CoreML",
                attempted=False,
                failure_class="missing_converter_tool",
                message=f"TensorFlow is not importable: {type(exc).__name__}: {exc}",
            )
        ]
    if shutil.which("tflite2tensorflow") is None:
        return [
            RouteResult(
                name="TFLite -> SavedModel -> CoreML",
                attempted=False,
                failure_class="missing_converter_tool",
                message=(
                    "TensorFlow is importable, but no native TensorFlow API reconstructs "
                    "a SavedModel from arbitrary TFLite. tflite2tensorflow is not installed."
                ),
            )
        ]
    return []


def run_tf2onnx_routes() -> list[RouteResult]:
    routes = []
    tf2onnx_available = importlib.util.find_spec("tf2onnx") is not None
    onnx_available = importlib.util.find_spec("onnx") is not None
    ort_available = importlib.util.find_spec("onnxruntime") is not None
    if not tf2onnx_available:
        return [
            RouteResult(
                name="TFLite -> ONNX -> CoreML",
                attempted=False,
                failure_class="missing_converter_tool",
                message="tf2onnx is not installed",
            )
        ]

    for target in TARGETS:
        onnx_path = INTERMEDIATE_DIR / f"{target['name']}.onnx"
        log_path = LOG_DIR / f"{target['name']}_tf2onnx.log"
        cmd = [
            sys.executable,
            "-m",
            "tf2onnx.convert",
            "--tflite",
            str(target["tflite"]),
            "--output",
            str(onnx_path),
            "--opset",
            "17",
        ]
        route = run_command_route(f"{target['name']}: TFLite -> ONNX", cmd, log_path)
        route.command = " ".join(cmd)
        if route.succeeded and onnx_path.exists():
            route.produced_files.append(str(onnx_path.relative_to(ROOT)))
            if onnx_available:
                check_log = LOG_DIR / f"{target['name']}_onnx_check.log"
                try:
                    import onnx

                    model = onnx.load(str(onnx_path))
                    onnx.checker.check_model(model)
                    check_log.write_text("onnx.checker succeeded\n", encoding="utf-8")
                except Exception:  # noqa: BLE001
                    error = traceback.format_exc()
                    route.succeeded = False
                    route.failure_class = "ONNX conversion failure"
                    route.message = _first_error_line(error)
                    check_log.write_text(error, encoding="utf-8")
            if route.succeeded and ort_available:
                run_onnx_dummy(target, onnx_path, route)
            if route.succeeded:
                coreml_route = try_onnx_to_coreml(target, onnx_path)
                routes.append(route)
                routes.append(coreml_route)
                continue
        routes.append(route)
    return routes


def run_tflite2tensorflow_routes() -> list[RouteResult]:
    binary = shutil.which("tflite2tensorflow")
    if binary is None:
        return [
            RouteResult(
                name="tflite2tensorflow / PINTO route",
                attempted=False,
                failure_class="missing_converter_tool",
                message="tflite2tensorflow CLI is not installed",
            )
        ]

    help_log = LOG_DIR / "tflite2tensorflow_help.log"
    help_result = subprocess.run([binary, "--help"], capture_output=True, text=True, cwd=str(ROOT), check=False)
    help_log.write_text((help_result.stdout or "") + "\n" + (help_result.stderr or ""), encoding="utf-8")
    flatc = shutil.which("flatc")
    if flatc is None:
        return [
            RouteResult(
                name="tflite2tensorflow / PINTO route",
                attempted=False,
                failure_class="missing_converter_tool",
                log_path=str(help_log.relative_to(ROOT)),
                message="tflite2tensorflow exists, but flatc is missing; conversion command was not run",
            )
        ]
    schema_path = INTERMEDIATE_DIR / "schema.fbs"
    if not schema_path.exists():
        return [
            RouteResult(
                name="tflite2tensorflow / PINTO route",
                attempted=False,
                failure_class="missing_converter_tool",
                log_path=str(help_log.relative_to(ROOT)),
                message=f"tflite2tensorflow exists, but schema.fbs is missing: {schema_path}",
            )
        ]

    routes: list[RouteResult] = []
    for target in TARGETS:
        model_dir = target["tflite"].parent
        model_name = target["tflite"].name
        for mode, extra_args in (
            ("SavedModel/PB", ["--output_pb"]),
            ("ONNX", ["--output_onnx", "--onnx_opset", "17"]),
        ):
            output_path = INTERMEDIATE_DIR / f"tflite2tensorflow_{target['name']}_{mode.lower().replace('/', '_')}"
            log_path = LOG_DIR / f"{target['name']}_tflite2tensorflow_{mode.lower().replace('/', '_')}.log"
            cmd = [
                binary,
                "--model_path",
                model_name,
                "--flatc_path",
                flatc,
                "--schema_path",
                str(schema_path),
                "--model_output_path",
                str(output_path),
                *extra_args,
            ]
            routes.append(run_command_route_with_cwd(
                name=f"{target['name']}: tflite2tensorflow {mode}",
                cmd=cmd,
                log_path=log_path,
                cwd=model_dir,
            ))
    return routes


def document_tflite_coreml_delegate() -> RouteResult:
    return RouteResult(
        name="LiteRT/TFLite Core ML delegate note",
        attempted=False,
        succeeded=False,
        failure_class="not_model_conversion",
        message=(
            "A TFLite Core ML delegate may accelerate a TFLite model through Core ML, "
            "but it does not produce .mlmodel/.mlpackage artifacts and does not satisfy this task."
        ),
    )


def run_command_route(name: str, cmd: list[str], log_path: Path) -> RouteResult:
    return run_command_route_with_cwd(name=name, cmd=cmd, log_path=log_path, cwd=ROOT)


def run_command_route_with_cwd(name: str, cmd: list[str], log_path: Path, cwd: Path) -> RouteResult:
    result = RouteResult(name=name, attempted=True, command=" ".join(cmd), log_path=str(log_path.relative_to(ROOT)))
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    log_path.write_text(
        "COMMAND: " + " ".join(cmd) + "\nCWD: " + str(cwd) + "\nRETURN_CODE: "
        + str(proc.returncode) + "\n\nSTDOUT:\n" + (proc.stdout or "") + "\nSTDERR:\n" + (proc.stderr or ""),
        encoding="utf-8",
    )
    result.succeeded = proc.returncode == 0
    if not result.succeeded:
        result.failure_class = "ONNX conversion failure" if "tf2onnx" in name or "ONNX" in name else "conversion issue"
        result.message = _best_error_line(proc.stderr or proc.stdout or f"return code {proc.returncode}", proc.returncode)
    return result


def run_onnx_dummy(target: dict[str, Any], onnx_path: Path, route: RouteResult) -> None:
    log_path = LOG_DIR / f"{target['name']}_onnxruntime_dummy.log"
    try:
        import numpy as np
        import onnxruntime as ort

        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        feed = {}
        for input_item in session.get_inputs():
            shape = [int(dim) if isinstance(dim, int) and dim > 0 else 1 for dim in input_item.shape]
            feed[input_item.name] = np.zeros(shape, dtype=np.float32)
        outputs = session.run(None, feed)
        summary = [
            f"{item.name}: shape={list(output.shape)} dtype={output.dtype} min={float(output.min()) if output.size else None} max={float(output.max()) if output.size else None}"
            for item, output in zip(session.get_outputs(), outputs)
        ]
        log_path.write_text("\n".join(summary) + "\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        error = traceback.format_exc()
        route.succeeded = False
        route.failure_class = "ONNX runtime failure"
        route.message = _first_error_line(error)
        log_path.write_text(error, encoding="utf-8")


def try_onnx_to_coreml(target: dict[str, Any], onnx_path: Path) -> RouteResult:
    log_path = LOG_DIR / f"{target['name']}_onnx_to_coreml.log"
    route = RouteResult(
        name=f"{target['name']}: ONNX -> CoreML",
        attempted=True,
        log_path=str(log_path.relative_to(ROOT)),
    )
    try:
        import onnx_coreml

        model = onnx_coreml.convert(model=str(onnx_path))
        model.save(str(target["coreml"]))
        _load_coreml_model(target["coreml"])
        route.succeeded = True
        route.produced_files.append(str(target["coreml"].relative_to(ROOT)))
        log_path.write_text("onnx-coreml conversion succeeded\n", encoding="utf-8")
    except Exception:  # noqa: BLE001
        error = traceback.format_exc()
        route.failure_class = "CoreML conversion failure"
        route.message = _first_error_line(error)
        log_path.write_text(error, encoding="utf-8")
    return route


def _load_coreml_model(path: Path) -> None:
    import coremltools as ct

    ct.models.MLModel(str(path))


def write_final_report(summary: dict[str, Any]) -> None:
    lines = [
        "# MediaPipe Pose Heavy Core ML Final Blocker Report",
        "",
        "## Conversion Status",
        "",
        f"- converted_detector: `{summary['converted_detector']}`",
        f"- converted_landmark: `{summary['converted_landmark']}`",
        f"- converted_all: `{summary['converted_all']}`",
        "",
        "## Environment",
        "",
        f"- Python executable: `{summary['environment']['python_executable']}`",
        f"- Python version: `{summary['environment']['python_version']}`",
        f"- Conda env: `{summary['environment']['conda_default_env']}`",
        f"- Platform: `{summary['environment']['platform']}`",
        f"- Machine: `{summary['environment']['machine']}`",
        "",
        "## Packages",
    ]
    for name, version in summary["environment"]["packages"].items():
        lines.append(f"- {name}: `{version}`")
    lines.extend(["", "## TFLite Inspection"])
    lines.append(f"- interpreter_source: `{summary['inspection'].get('interpreter_source')}`")
    lines.append(f"- interpreter_import_error: `{summary['inspection'].get('interpreter_import_error')}`")
    for name, info in summary["inspection"]["models"].items():
        lines.append(f"- {name}: inspection_available=`{info.get('inspection_available')}`, error=`{bool(info.get('error'))}`")
    lines.extend(["", "## Route Results"])
    for route in summary["routes"]:
        lines.append(
            f"- {route['name']}: attempted=`{route['attempted']}`, succeeded=`{route['succeeded']}`, "
            f"failure_class=`{route['failure_class']}`, log=`{route['log_path']}`"
        )
        if route.get("message"):
            lines.append(f"  - {route['message']}")
        if route.get("command"):
            lines.append(f"  - command: `{route['command']}`")
        if route.get("produced_files"):
            lines.append(f"  - produced: `{route['produced_files']}`")
    lines.extend(
        [
            "",
            "## Current Decision",
            "",
            (
                "The extracted TFLite models are runnable and inspectable in TensorFlow Lite, and the "
                "landmark model can be converted as far as ONNX. No runnable Core ML model was produced. "
                "The remaining blocker is not the MediaPipe task extraction or a custom-op TFLite runtime "
                "issue; it is the lack of a working end-to-end converter chain from these TFLite graphs to "
                "a Core ML-supported graph on the current macOS arm64 environment."
            ),
        ]
    )
    if not summary["converted_all"]:
        lines.extend(
            [
                "",
                "## Exact Blocker",
                "",
                (
                    "Direct CoreMLTools conversion still rejects TFLite input. The detector model crashes "
                    "tf2onnx conversion before an ONNX graph is produced. The landmark model converts to "
                    "ONNX and passes ONNX Runtime dummy inference, but the available onnx-coreml package is "
                    "obsolete and imports removed CoreMLTools internals. The tflite2tensorflow route starts "
                    "from the flatbuffer JSON but fails while reconstructing PAD tensors because its use of "
                    "TensorFlow Lite private interpreter APIs is incompatible with the TensorFlow version "
                    "available on this Apple Silicon environment. Docker is the next realistic route only "
                    "if a Linux/x86_64 daemon is available."
                ),
                "",
                "## Most Likely Next Step",
                "",
                (
                    "Run the same conversion attempts in a Linux x86_64 environment with a converter stack "
                    "matched to tflite2tensorflow/onnx-coreml, or obtain TensorFlow SavedModel versions of "
                    "the MediaPipe pose detector and landmark models. Continuing to permute macOS arm64 "
                    "TensorFlow/CoreMLTools package versions is unlikely to produce a stable result."
                ),
            ]
        )
    FINAL_BLOCKER_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _first_error_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:500]
    return ""


def _best_error_line(text: str, return_code: int | None = None) -> str:
    interesting = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(token in stripped for token in ("Error", "ERROR", "Exception", "Traceback", "Segmentation fault", "ModuleNotFoundError", "ValueError", "OSError", "TypeError")):
            interesting.append(stripped)
    if interesting:
        return interesting[-1][:500]
    first = _first_error_line(text)
    if first:
        return first
    if return_code is not None:
        return f"return code {return_code}"
    return ""


def np_list(value: Any) -> Any:
    if value is None:
        return None
    try:
        return [int(item) for item in value]
    except Exception:  # noqa: BLE001
        return str(value)


def _json_safe(value: Any) -> Any:
    import numpy as np

    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
