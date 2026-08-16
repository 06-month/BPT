from pathlib import Path
import time

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None


DEFAULT_MOTIONAGFORMER_COREML_PATH = "assets/coreml/motionagformer_xs.mlpackage"
DEFAULT_INPUT_NAME = "input_2d_sequence"
DEFAULT_OUTPUT_NAME = "pred_3d_sequence"
DEFAULT_WINDOW_SIZE = 27


class CoreMLMotionAGFormerRunner:
    """Core ML MotionAGFormer-XS runner with the same window API as PyTorch."""

    def __init__(
        self,
        model_path=DEFAULT_MOTIONAGFORMER_COREML_PATH,
        input_name=DEFAULT_INPUT_NAME,
        output_name=DEFAULT_OUTPUT_NAME,
        compute_units="all",
        window_size=DEFAULT_WINDOW_SIZE,
        model=None,
    ):
        self.model_path = Path(model_path)
        self.input_name = input_name
        self.output_name = output_name
        self.compute_units = compute_units
        self.window_size = int(window_size)
        self.last_inference_ms = None
        self.load_ms = 0.0
        if model is not None:
            self.model = model
            return
        if not self.model_path.exists():
            raise FileNotFoundError(f"MotionAGFormer Core ML model not found: {self.model_path}")
        try:
            import coremltools as ct
        except ImportError as exc:
            raise ImportError(
                "coremltools is required for Core ML MotionAGFormer inference",
            ) from exc
        load_start = time.perf_counter()
        self.model = ct.models.MLModel(
            str(self.model_path),
            compute_units=_compute_units(ct, compute_units),
        )
        self.load_ms = (time.perf_counter() - load_start) * 1000.0

    def predict_3d(self, window_2d):
        arr = _as_array(window_2d)
        if arr.shape[-3:] != (self.window_size, 17, arr.shape[-1]):
            raise ValueError(
                f"window_2d must have shape ({self.window_size}, 17, C) or batched equivalent",
            )
        if arr.shape[-1] != 3:
            raise ValueError("MotionAGFormer-XS Core ML input must have 3 channels")
        batched = arr[None, ...] if arr.ndim == 3 else arr
        if batched.shape[0] != 1:
            raise ValueError("MotionAGFormer-XS Core ML runner currently supports batch size 1")

        start = time.perf_counter()
        prediction = self.model.predict({self.input_name: batched.astype("float32", copy=False)})
        self.last_inference_ms = (time.perf_counter() - start) * 1000.0

        if self.output_name not in prediction:
            available = ", ".join(sorted(prediction.keys()))
            raise KeyError(f"Core ML output '{self.output_name}' not found. Available: {available}")
        pred = np.asarray(prediction[self.output_name], dtype="float32")
        if pred.shape != (1, self.window_size, 17, 3):
            raise ValueError(f"Unexpected Core ML output shape: {pred.shape}")
        if arr.ndim == 3:
            return pred[0]
        return pred


def _as_array(values):
    if np is None:  # pragma: no cover
        raise ImportError("numpy is required for Core ML MotionAGFormer runner")
    return np.asarray(values, dtype="float32")


def _compute_units(ct, value):
    normalized = str(value).lower()
    if normalized == "all":
        return ct.ComputeUnit.ALL
    if normalized == "cpu_only":
        return ct.ComputeUnit.CPU_ONLY
    if normalized == "cpu_and_gpu":
        return ct.ComputeUnit.CPU_AND_GPU
    if normalized == "cpu_and_ne":
        return ct.ComputeUnit.CPU_AND_NE
    raise ValueError(f"Unsupported Core ML compute units: {value}")
