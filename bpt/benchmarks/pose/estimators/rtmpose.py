"""RTMPose-s 2D front-end with a swappable inference backend.

The preprocessing, SimCC decode and inverse affine here are ported verbatim
from ``scripts/run_coreml_rtmpose_s_motionagformer_xs_pipeline.py`` so a run on
another machine stays numerically comparable to the macOS Core ML prototype.
Only the tensor-in/tensor-out step is swappable:

``coreml``
    the bundled ``rtmpose_s_forward.mlpackage`` (macOS only)
``onnx``
    an ONNX Runtime session, which is how this runs on Linux/CUDA
``callable``
    any object mapping ``[1,3,256,192] -> (simcc_x, simcc_y)``, for tests

Whatever the backend, it must honour the M0 contract: input ``input_image``
``[1,3,256,192]`` NCHW normalized RGB, outputs ``simcc_x [1,17,384]`` and
``simcc_y [1,17,512]``, SimCC split ratio 2.0, no DARK refinement, no flip
test, and one full-image bbox per frame (there is no person detector).
"""

from __future__ import annotations

import numpy as np

INPUT_SIZE = (192, 256)  # (width, height)
SIMCC_SPLIT_RATIO = 2.0
BBOX_SCALE_FACTOR = 1.25
MEAN_RGB = np.asarray([123.675, 116.28, 103.53], dtype=np.float32)
STD_RGB = np.asarray([58.395, 57.12, 57.375], dtype=np.float32)
EXPECTED_SIMCC_X = 384
EXPECTED_SIMCC_Y = 512


def fix_aspect_ratio(scale: np.ndarray, aspect_ratio: float) -> np.ndarray:
    width, height = float(scale[0]), float(scale[1])
    if width > height * aspect_ratio:
        return np.asarray([width, width / aspect_ratio], dtype=np.float32)
    return np.asarray([height * aspect_ratio, height], dtype=np.float32)


def rotate_point(point: np.ndarray, angle_rad: float) -> np.ndarray:
    sin, cos = np.sin(angle_rad), np.cos(angle_rad)
    return np.asarray([point[0] * cos - point[1] * sin, point[0] * sin + point[1] * cos], dtype=np.float32)


def third_point(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    direction = a - b
    return b + np.asarray([-direction[1], direction[0]], dtype=np.float32)


def warp_matrix(center, scale, rotation_deg, output_size, inverse=False) -> np.ndarray:
    import cv2

    source_width = scale[0]
    destination_width, destination_height = output_size[:2]
    rotation = np.deg2rad(rotation_deg)
    source_direction = rotate_point(np.asarray([source_width * -0.5, 0.0], dtype=np.float32), rotation)
    destination_direction = np.asarray([destination_width * -0.5, 0.0], dtype=np.float32)
    source = np.zeros((3, 2), dtype=np.float32)
    source[0] = center
    source[1] = center + source_direction
    source[2] = third_point(source[0], source[1])
    destination = np.zeros((3, 2), dtype=np.float32)
    destination[0] = [destination_width * 0.5, destination_height * 0.5]
    destination[1] = destination[0] + destination_direction
    destination[2] = third_point(destination[0], destination[1])
    if inverse:
        return cv2.getAffineTransform(np.float32(destination), np.float32(source))
    return cv2.getAffineTransform(np.float32(source), np.float32(destination))


def preprocess_full_image(frame_bgr: np.ndarray):
    """Return ``(tensor, warp, inverse_warp)`` for one full-image bbox."""

    import cv2

    height, width = frame_bgr.shape[:2]
    center = np.asarray([width * 0.5, height * 0.5], dtype=np.float32)
    scale = np.asarray([width, height], dtype=np.float32) * BBOX_SCALE_FACTOR
    scale = fix_aspect_ratio(scale, INPUT_SIZE[0] / INPUT_SIZE[1])
    forward = warp_matrix(center, scale, 0.0, INPUT_SIZE, inverse=False)
    inverse = warp_matrix(center, scale, 0.0, INPUT_SIZE, inverse=True)
    warped = cv2.warpAffine(frame_bgr, forward, INPUT_SIZE, flags=cv2.INTER_LINEAR)
    rgb = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB).astype(np.float32)
    tensor = ((rgb - MEAN_RGB) / STD_RGB).transpose(2, 0, 1)[None, ...].astype(np.float32)
    return tensor, forward, inverse


def decode_simcc(simcc_x: np.ndarray, simcc_y: np.ndarray):
    """Argmax SimCC decode; confidence is ``min(max_x, max_y)``, no DARK."""

    simcc_x = np.asarray(simcc_x, dtype=np.float32)
    simcc_y = np.asarray(simcc_y, dtype=np.float32)
    if simcc_x.shape[-1] != EXPECTED_SIMCC_X or simcc_y.shape[-1] != EXPECTED_SIMCC_Y:
        raise ValueError(f"unexpected SimCC shapes: {simcc_x.shape}, {simcc_y.shape}")
    batch, joints, _ = simcc_x.shape
    x_flat = simcc_x.reshape(batch * joints, -1)
    y_flat = simcc_y.reshape(batch * joints, -1)
    scores = np.minimum(x_flat.max(axis=1), y_flat.max(axis=1)).astype(np.float32)
    locations = np.stack([x_flat.argmax(axis=1), y_flat.argmax(axis=1)], axis=-1).astype(np.float32)
    locations[scores <= 0.0] = -1.0
    locations = (locations / SIMCC_SPLIT_RATIO).reshape(batch, joints, 2)
    return locations.astype(np.float32), scores.reshape(batch, joints)


def apply_affine(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float32)
    ones = np.ones((points.shape[0], 1), dtype=np.float32)
    return (np.concatenate([points, ones], axis=1) @ np.asarray(matrix, dtype=np.float32).T).astype(np.float32)


class RTMPoseEstimator:
    """Frame in, COCO17 ``[17,3]`` in original image pixels out."""

    def __init__(self, backend: str = "coreml", model_path: str | None = None, session=None, providers=None):
        self.backend = backend
        self.model_path = model_path
        self._session = session
        self._providers = providers
        if session is None:
            self._session = self._load(backend, model_path, providers)

    @staticmethod
    def _load(backend, model_path, providers):
        if backend == "coreml":
            import coremltools as ct

            return ct.models.MLModel(str(model_path))
        if backend == "onnx":
            import onnxruntime as ort

            available = ort.get_available_providers()
            chosen = providers or [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available]
            return ort.InferenceSession(str(model_path), providers=chosen)
        raise ValueError(f"unknown RTMPose backend: {backend}")

    def forward(self, tensor: np.ndarray):
        if self.backend == "coreml":
            output = self._session.predict({"input_image": tensor})
            return np.asarray(output["simcc_x"]), np.asarray(output["simcc_y"])
        if self.backend == "onnx":
            names = [output.name for output in self._session.get_outputs()]
            input_name = self._session.get_inputs()[0].name
            outputs = self._session.run(names, {input_name: tensor})
            return _pick_simcc(names, outputs)
        simcc_x, simcc_y = self._session(tensor)
        return np.asarray(simcc_x), np.asarray(simcc_y)

    def predict(self, frame_bgr: np.ndarray) -> np.ndarray:
        tensor, _, inverse = preprocess_full_image(frame_bgr)
        simcc_x, simcc_y = self.forward(tensor)
        locations, scores = decode_simcc(simcc_x, simcc_y)
        pixels = apply_affine(locations[0], inverse)
        return np.concatenate([pixels, scores[0][:, None]], axis=1).astype(np.float32)


def _pick_simcc(names, outputs):
    """Match outputs by their last dimension, not by name order."""

    lookup = dict(zip(names, [np.asarray(value) for value in outputs]))
    by_name = {name.lower(): value for name, value in lookup.items()}
    if "simcc_x" in by_name and "simcc_y" in by_name:
        return by_name["simcc_x"], by_name["simcc_y"]
    values = list(lookup.values())
    x = next((v for v in values if v.shape[-1] == EXPECTED_SIMCC_X), None)
    y = next((v for v in values if v.shape[-1] == EXPECTED_SIMCC_Y), None)
    if x is None or y is None:
        raise ValueError(f"could not identify SimCC outputs among shapes {[v.shape for v in values]}")
    return x, y
