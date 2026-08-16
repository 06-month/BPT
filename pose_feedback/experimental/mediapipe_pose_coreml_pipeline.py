"""Experimental MediaPipe Pose Heavy Core ML pipeline scaffold.

This module is intentionally isolated from the production body/wrist feedback
pipeline. It attempts to run the two internal MediaPipe Pose TFLite forwards
after Core ML conversion, then documents the non-neural pipeline steps that must
be reimplemented around those forwards.

No placeholder landmarks are generated. If conversion or decode metadata is
missing, the pipeline raises a stage-specific error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import math
import time
from typing import Any

import cv2
import numpy as np


BLAZEPOSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
    (25, 27), (26, 28), (27, 29), (28, 30), (29, 31),
    (30, 32), (27, 31), (28, 32),
    (15, 17), (15, 19), (15, 21), (16, 18), (16, 20), (16, 22),
    (0, 11), (0, 12),
]

POSE_DETECTOR_INPUT_SIZE = 224
POSE_LANDMARK_INPUT_SIZE = 256
POSE_DETECTOR_NUM_BOXES = 2254
POSE_DETECTOR_NUM_COORDS = 12
POSE_DETECTOR_NUM_KEYPOINTS = 4
POSE_LANDMARK_NUM_LANDMARKS = 39
POSE_LANDMARK_OUTPUT_LANDMARKS = 33
POSE_LANDMARK_Z_NORMALIZE = 0.4


class ExperimentalPipelineError(RuntimeError):
    """Stage-specific failure for the experimental Core ML pose pipeline."""

    def __init__(self, stage: str, message: str):
        super().__init__(f"{stage}: {message}")
        self.stage = stage
        self.message = message


@dataclass
class DetectorPreprocessInfo:
    """MediaPipe ImageToTensor letterbox metadata for pose detector input."""

    image_w: int
    image_h: int
    tensor_size: int
    scale: float
    pad_x: float
    pad_y: float

    def tensor_norm_xy_to_image_px(self, xy_norm: np.ndarray) -> np.ndarray:
        pts = np.asarray(xy_norm, dtype=np.float32).copy()
        pts[..., 0] = (pts[..., 0] * self.tensor_size - self.pad_x) / self.scale
        pts[..., 1] = (pts[..., 1] * self.tensor_size - self.pad_y) / self.scale
        pts[..., 0] = np.clip(pts[..., 0], 0.0, float(self.image_w))
        pts[..., 1] = np.clip(pts[..., 1], 0.0, float(self.image_h))
        return pts


@dataclass
class PoseDetection:
    """Decoded pose detector candidate in original image pixel coordinates."""

    score: float
    bbox_xyxy: tuple[float, float, float, float]
    keypoints_xy: np.ndarray  # shape: (4, 2), original image pixels


@dataclass
class PoseRoi:
    """Rotation-aware ROI, matching MediaPipe normalized-rect semantics."""

    center_x: float
    center_y: float
    width: float
    height: float
    rotation: float

    def axis_aligned_box(self, image_shape: tuple[int, int]) -> tuple[float, float, float, float]:
        h, w = image_shape
        corners = _rotated_rect_corners(self.center_x, self.center_y, self.width, self.height, self.rotation)
        x1, y1 = np.min(corners, axis=0)
        x2, y2 = np.max(corners, axis=0)
        return (
            max(0.0, float(x1)),
            max(0.0, float(y1)),
            min(float(w), float(x2)),
            min(float(h), float(y2)),
        )


@dataclass
class PoseCoreMLStageStatus:
    task_extraction: bool = False
    tflite_inspection: bool = False
    coreml_conversion: bool = False
    detector_inference: bool = False
    detector_decode: bool = False
    roi_crop: bool = False
    landmark_inference: bool = False
    coordinate_restore: bool = False
    tracking: bool = False
    comparison: bool = False
    failures: list[dict[str, str]] = field(default_factory=list)

    def mark_failure(self, stage: str, message: str) -> None:
        self.failures.append({"stage": stage, "message": message})


@dataclass
class PosePipelineResult:
    landmarks_px: np.ndarray | None
    landmarks_norm: np.ndarray | None
    presence: float | None
    roi: tuple[float, float, float, float] | None
    used_detector: bool
    stage_status: PoseCoreMLStageStatus
    inference_ms: float


class CoreMLForwardModel:
    """Small Core ML model wrapper for tensor-forward experiments."""

    def __init__(self, model_path: str | Path, compute_units: str = "all"):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Core ML model not found: {self.model_path}")
        try:
            import coremltools as ct
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise ImportError("coremltools is required for Core ML inference") from exc

        self._ct = ct
        self.model = ct.models.MLModel(
            str(self.model_path),
            compute_units=_compute_units(ct, compute_units),
        )
        spec = self.model.get_spec()
        self.input_names = [item.name for item in spec.description.input]
        self.output_names = [item.name for item in spec.description.output]
        if not self.input_names:
            raise ExperimentalPipelineError("coreml_model_load", f"no model inputs: {self.model_path}")

    def predict(self, tensor: np.ndarray, input_name: str | None = None) -> dict[str, Any]:
        name = input_name or self.input_names[0]
        return self.model.predict({name: tensor.astype("float32", copy=False)})


class ExperimentalMediaPipePoseHeavyCoreMLPipeline:
    """Experimental reimplementation of the MediaPipe Pose Heavy body path."""

    def __init__(
        self,
        detector_model: str | Path,
        landmark_model: str | Path,
        compute_units: str = "all",
        score_threshold: float = 0.5,
        tracking_threshold: float = 0.5,
    ):
        self.status = PoseCoreMLStageStatus(coreml_conversion=True)
        self.detector = CoreMLForwardModel(detector_model, compute_units=compute_units)
        self.landmark = CoreMLForwardModel(landmark_model, compute_units=compute_units)
        self.score_threshold = float(score_threshold)
        self.tracking_threshold = float(tracking_threshold)
        self.previous_roi: PoseRoi | None = None
        self.detector_anchors = generate_pose_detector_anchors()

    def process_frame(self, frame_bgr: np.ndarray, frame_index: int = 0) -> PosePipelineResult:
        start = time.perf_counter()
        status = PoseCoreMLStageStatus(coreml_conversion=True)
        used_detector = self.previous_roi is None
        try:
            if used_detector:
                detector_input, detector_preprocess = self._preprocess_detector(frame_bgr)
                detector_outputs = self.detector.predict(detector_input)
                status.detector_inference = True
                roi = self._decode_detector_outputs(
                    detector_outputs,
                    frame_bgr.shape[:2],
                    detector_preprocess,
                )
                status.detector_decode = True
            else:
                roi = self.previous_roi
                status.tracking = True

            crop, transform = crop_rotated_roi(frame_bgr, roi, output_size=(256, 256))
            status.roi_crop = True
            landmark_input = crop.astype("float32") / 255.0
            landmark_input = landmark_input[None, ...]
            landmark_outputs = self.landmark.predict(landmark_input)
            status.landmark_inference = True
            landmarks_norm, presence = self._decode_landmark_outputs(landmark_outputs)
            landmarks_px = restore_landmarks_to_image(landmarks_norm, transform)
            status.coordinate_restore = True
            self.previous_roi = update_roi_from_landmarks(landmarks_px, frame_bgr.shape[:2])
            if presence is not None and presence < self.tracking_threshold:
                self.previous_roi = None
        except ExperimentalPipelineError as exc:
            status.mark_failure(exc.stage, exc.message)
            raise

        elapsed = (time.perf_counter() - start) * 1000.0
        return PosePipelineResult(
            landmarks_px=landmarks_px,
            landmarks_norm=landmarks_norm,
            presence=presence,
            roi=roi.axis_aligned_box(frame_bgr.shape[:2]) if roi is not None else None,
            used_detector=used_detector,
            stage_status=status,
            inference_ms=elapsed,
        )

    def _preprocess_detector(self, frame_bgr: np.ndarray) -> tuple[np.ndarray, DetectorPreprocessInfo]:
        # Source: mediapipe/modules/pose_detection/pose_detection_cpu.pbtxt.
        # ImageToTensorCalculator uses a 224x224 RGB tensor, keeps aspect ratio,
        # zero pads the border, and maps float values to [-1, 1].
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        scale = min(POSE_DETECTOR_INPUT_SIZE / float(w), POSE_DETECTOR_INPUT_SIZE / float(h))
        resized_w = max(1, int(round(w * scale)))
        resized_h = max(1, int(round(h * scale)))
        resized = cv2.resize(rgb, (resized_w, resized_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.zeros((POSE_DETECTOR_INPUT_SIZE, POSE_DETECTOR_INPUT_SIZE, 3), dtype=np.uint8)
        pad_x = (POSE_DETECTOR_INPUT_SIZE - resized_w) / 2.0
        pad_y = (POSE_DETECTOR_INPUT_SIZE - resized_h) / 2.0
        x0 = int(round(pad_x))
        y0 = int(round(pad_y))
        canvas[y0:y0 + resized_h, x0:x0 + resized_w] = resized
        tensor = canvas.astype("float32") / 127.5 - 1.0
        info = DetectorPreprocessInfo(
            image_w=w,
            image_h=h,
            tensor_size=POSE_DETECTOR_INPUT_SIZE,
            scale=scale,
            pad_x=float(x0),
            pad_y=float(y0),
        )
        return tensor[None, ...], info

    def _decode_detector_outputs(
        self,
        outputs: dict[str, Any],
        image_shape: tuple[int, int],
        preprocess: DetectorPreprocessInfo,
    ) -> PoseRoi:
        raw_boxes, raw_scores = _extract_detector_tensors(outputs)
        detections = decode_pose_detector_tensors(
            raw_boxes=raw_boxes,
            raw_scores=raw_scores,
            anchors=self.detector_anchors,
            preprocess=preprocess,
            score_threshold=self.score_threshold,
        )
        if not detections:
            raise ExperimentalPipelineError(
                "detector_decode",
                f"no pose detection above score threshold {self.score_threshold}",
            )
        detection = detections[0]
        return pose_detection_to_roi(detection, image_shape=image_shape)

    def _decode_landmark_outputs(self, outputs: dict[str, Any]) -> tuple[np.ndarray, float | None]:
        return decode_pose_landmark_tensors(outputs)


def generate_pose_detector_anchors() -> np.ndarray:
    """Generate MediaPipe Pose detector SSD anchors.

    Ported from mediapipe/calculators/tflite/ssd_anchors_calculator.cc using
    pose_detection_cpu.pbtxt options. The default interpolated anchor ratio is
    1.0, which is why this detector has 2254 anchors instead of 1127.
    Returned columns are x_center, y_center, width, height in normalized tensor
    coordinates.
    """

    input_size = POSE_DETECTOR_INPUT_SIZE
    num_layers = 5
    min_scale = 0.1484375
    max_scale = 0.75
    strides = [8, 16, 32, 32, 32]
    aspect_ratios = [1.0]
    interpolated_scale_aspect_ratio = 1.0
    anchor_offset_x = 0.5
    anchor_offset_y = 0.5
    fixed_anchor_size = True

    def calculate_scale(stride_index: int) -> float:
        if len(strides) == 1:
            return (min_scale + max_scale) * 0.5
        return min_scale + (max_scale - min_scale) * stride_index / (len(strides) - 1.0)

    anchors: list[tuple[float, float, float, float]] = []
    layer_id = 0
    while layer_id < num_layers:
        anchor_heights: list[float] = []
        anchor_widths: list[float] = []
        layer_aspect_ratios: list[float] = []
        layer_scales: list[float] = []

        last_same_stride_layer = layer_id
        while last_same_stride_layer < len(strides) and strides[last_same_stride_layer] == strides[layer_id]:
            scale = calculate_scale(last_same_stride_layer)
            for aspect_ratio in aspect_ratios:
                layer_aspect_ratios.append(aspect_ratio)
                layer_scales.append(scale)
            if interpolated_scale_aspect_ratio > 0.0:
                scale_next = 1.0 if last_same_stride_layer == len(strides) - 1 else calculate_scale(last_same_stride_layer + 1)
                layer_scales.append(math.sqrt(scale * scale_next))
                layer_aspect_ratios.append(interpolated_scale_aspect_ratio)
            last_same_stride_layer += 1

        for scale, aspect_ratio in zip(layer_scales, layer_aspect_ratios):
            ratio_sqrt = math.sqrt(aspect_ratio)
            anchor_heights.append(scale / ratio_sqrt)
            anchor_widths.append(scale * ratio_sqrt)

        stride = strides[layer_id]
        feature_map_h = int(math.ceil(input_size / stride))
        feature_map_w = int(math.ceil(input_size / stride))
        for y in range(feature_map_h):
            for x in range(feature_map_w):
                x_center = (x + anchor_offset_x) / feature_map_w
                y_center = (y + anchor_offset_y) / feature_map_h
                for anchor_w, anchor_h in zip(anchor_widths, anchor_heights):
                    if fixed_anchor_size:
                        anchors.append((x_center, y_center, 1.0, 1.0))
                    else:
                        anchors.append((x_center, y_center, anchor_w, anchor_h))
        layer_id = last_same_stride_layer

    out = np.asarray(anchors, dtype=np.float32)
    if out.shape != (POSE_DETECTOR_NUM_BOXES, 4):
        raise ValueError(f"expected {POSE_DETECTOR_NUM_BOXES} pose anchors, got {out.shape}")
    return out


def decode_pose_detector_tensors(
    raw_boxes: np.ndarray,
    raw_scores: np.ndarray,
    anchors: np.ndarray,
    preprocess: DetectorPreprocessInfo,
    score_threshold: float = 0.5,
    nms_iou_threshold: float = 0.3,
) -> list[PoseDetection]:
    """Decode MediaPipe Pose detector tensors into image-space candidates."""

    boxes = np.asarray(raw_boxes, dtype=np.float32).reshape(POSE_DETECTOR_NUM_BOXES, POSE_DETECTOR_NUM_COORDS)
    scores = np.asarray(raw_scores, dtype=np.float32).reshape(POSE_DETECTOR_NUM_BOXES, -1)[:, 0]
    scores = 1.0 / (1.0 + np.exp(-np.clip(scores, -100.0, 100.0)))

    # reverse_output_order=true maps box format to XYWH in MediaPipe.
    x_center = boxes[:, 0] / 224.0 * anchors[:, 2] + anchors[:, 0]
    y_center = boxes[:, 1] / 224.0 * anchors[:, 3] + anchors[:, 1]
    width = boxes[:, 2] / 224.0 * anchors[:, 2]
    height = boxes[:, 3] / 224.0 * anchors[:, 3]

    xmin = x_center - width / 2.0
    ymin = y_center - height / 2.0
    xmax = x_center + width / 2.0
    ymax = y_center + height / 2.0

    keypoints = np.zeros((POSE_DETECTOR_NUM_BOXES, POSE_DETECTOR_NUM_KEYPOINTS, 2), dtype=np.float32)
    for idx in range(POSE_DETECTOR_NUM_KEYPOINTS):
        offset = 4 + idx * 2
        keypoints[:, idx, 0] = boxes[:, offset] / 224.0 * anchors[:, 2] + anchors[:, 0]
        keypoints[:, idx, 1] = boxes[:, offset + 1] / 224.0 * anchors[:, 3] + anchors[:, 1]

    candidates: list[PoseDetection] = []
    for i in np.where(scores >= score_threshold)[0]:
        bbox_norm_xy = np.asarray(
            [[xmin[i], ymin[i]], [xmax[i], ymax[i]]],
            dtype=np.float32,
        )
        bbox_px = preprocess.tensor_norm_xy_to_image_px(bbox_norm_xy)
        kps_px = preprocess.tensor_norm_xy_to_image_px(keypoints[i])
        candidates.append(
            PoseDetection(
                score=float(scores[i]),
                bbox_xyxy=(
                    float(bbox_px[0, 0]),
                    float(bbox_px[0, 1]),
                    float(bbox_px[1, 0]),
                    float(bbox_px[1, 1]),
                ),
                keypoints_xy=kps_px,
            )
        )

    candidates.sort(key=lambda item: item.score, reverse=True)
    return _nms_pose_detections(candidates, iou_threshold=nms_iou_threshold)


def pose_detection_to_roi(
    detection: PoseDetection,
    image_shape: tuple[int, int],
    scale: float = 1.25,
) -> PoseRoi:
    """Convert detector keypoints to MediaPipe pose landmark ROI.

    Source graph:
    pose_detection_to_roi.pbtxt uses AlignmentPointsRectsCalculator with
    start keypoint 0, end keypoint 1, target angle 90 degrees, then scales the
    square rect by 1.25.
    """

    image_h, image_w = image_shape
    center = detection.keypoints_xy[0]
    scale_point = detection.keypoints_xy[1]
    vector = scale_point - center
    box_size = float(np.linalg.norm(vector) * 2.0 * scale)
    if not np.isfinite(box_size) or box_size <= 1.0:
        x1, y1, x2, y2 = detection.bbox_xyxy
        box_size = max(x2 - x1, y2 - y1) * scale
        center = np.asarray([(x1 + x2) * 0.5, (y1 + y2) * 0.5], dtype=np.float32)
    rotation = _normalize_radians((math.pi / 2.0) - math.atan2(-float(vector[1]), float(vector[0])))
    return PoseRoi(
        center_x=float(np.clip(center[0], 0.0, float(image_w))),
        center_y=float(np.clip(center[1], 0.0, float(image_h))),
        width=box_size,
        height=box_size,
        rotation=rotation,
    )


def decode_pose_landmark_tensors(outputs: dict[str, Any]) -> tuple[np.ndarray, float | None]:
    """Decode pose landmark tensors using source-derived MediaPipe layout.

    The landmark graph decodes 39 landmarks from tensor[0], refines them with a
    heatmap, then keeps the first 33 pose landmarks. This experimental decoder
    currently performs the raw tensor decode only; heatmap refinement is a known
    remaining parity gap until converted output ordering is verified by a real
    Core ML forward.
    """

    landmark_tensor: np.ndarray | None = None
    pose_flag_tensor: np.ndarray | None = None
    for value in outputs.values():
        arr = np.asarray(value)
        if arr.size % POSE_LANDMARK_NUM_LANDMARKS == 0:
            dims = arr.size // POSE_LANDMARK_NUM_LANDMARKS
            if dims >= 5 and landmark_tensor is None:
                landmark_tensor = arr.astype(np.float32, copy=False)
        if arr.size == 1:
            pose_flag_tensor = arr.astype(np.float32, copy=False)

    if landmark_tensor is None:
        available = {name: np.asarray(value).shape for name, value in outputs.items()}
        raise ExperimentalPipelineError(
            "landmark_decode",
            f"could not identify 39-landmark output tensor. Available Core ML outputs: {available}",
        )

    dims = landmark_tensor.size // POSE_LANDMARK_NUM_LANDMARKS
    raw = landmark_tensor.reshape(POSE_LANDMARK_NUM_LANDMARKS, dims)
    landmarks = np.zeros((POSE_LANDMARK_OUTPUT_LANDMARKS, max(5, dims)), dtype=np.float32)
    landmarks[:, : min(dims, landmarks.shape[1])] = raw[:POSE_LANDMARK_OUTPUT_LANDMARKS, : min(dims, landmarks.shape[1])]
    landmarks[:, 0] = landmarks[:, 0] / POSE_LANDMARK_INPUT_SIZE
    landmarks[:, 1] = landmarks[:, 1] / POSE_LANDMARK_INPUT_SIZE
    if landmarks.shape[1] > 2:
        landmarks[:, 2] = landmarks[:, 2] / POSE_LANDMARK_INPUT_SIZE / POSE_LANDMARK_Z_NORMALIZE
    if landmarks.shape[1] > 3:
        landmarks[:, 3] = _sigmoid(landmarks[:, 3])
    if landmarks.shape[1] > 4:
        landmarks[:, 4] = _sigmoid(landmarks[:, 4])

    presence = None
    if pose_flag_tensor is not None:
        presence = float(_sigmoid(float(np.asarray(pose_flag_tensor).reshape(-1)[0])))
    return landmarks[:, :5], presence


def crop_rotated_roi(
    frame_bgr: np.ndarray,
    roi: PoseRoi | tuple[float, float, float, float],
    output_size: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Crop a MediaPipe-style ROI and return crop plus crop-to-image transform.

    For PoseRoi input, this uses the detector-derived body rotation. Tuple input
    is still accepted for older debug callers and is treated as axis-aligned.
    """

    h, w = frame_bgr.shape[:2]
    out_w, out_h = output_size
    if isinstance(roi, PoseRoi):
        corners = _rotated_rect_corners(roi.center_x, roi.center_y, roi.width, roi.height, roi.rotation)
        src = np.asarray([corners[0], corners[1], corners[3]], dtype=np.float32)
        dst = np.asarray([[0.0, 0.0], [float(out_w), 0.0], [0.0, float(out_h)]], dtype=np.float32)
        image_to_crop = cv2.getAffineTransform(src, dst)
        crop = cv2.warpAffine(
            frame_bgr,
            image_to_crop,
            output_size,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )
        crop_to_image = cv2.invertAffineTransform(image_to_crop)
        transform = np.vstack([crop_to_image, np.asarray([0.0, 0.0, 1.0], dtype=np.float32)]).astype(np.float32)
        return crop, transform

    x1, y1, x2, y2 = roi
    x1_i = max(0, min(w - 1, int(round(x1))))
    y1_i = max(0, min(h - 1, int(round(y1))))
    x2_i = max(x1_i + 1, min(w, int(round(x2))))
    y2_i = max(y1_i + 1, min(h, int(round(y2))))
    crop = frame_bgr[y1_i:y2_i, x1_i:x2_i]
    crop = cv2.resize(crop, output_size, interpolation=cv2.INTER_LINEAR)

    sx = (x2_i - x1_i) / float(output_size[0])
    sy = (y2_i - y1_i) / float(output_size[1])
    transform = np.array(
        [
            [sx, 0.0, float(x1_i)],
            [0.0, sy, float(y1_i)],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )
    return crop, transform


def restore_landmarks_to_image(landmarks_norm: np.ndarray, crop_to_image: np.ndarray) -> np.ndarray:
    pts = np.asarray(landmarks_norm, dtype=np.float32)
    if pts.ndim != 2 or pts.shape[1] < 2:
        raise ValueError(f"landmarks_norm must have shape (N, >=2), got {pts.shape}")
    xy = pts[:, :2].copy()
    xy[:, 0] *= POSE_LANDMARK_INPUT_SIZE
    xy[:, 1] *= POSE_LANDMARK_INPUT_SIZE
    homo = np.concatenate([xy, np.ones((xy.shape[0], 1), dtype=np.float32)], axis=1)
    restored = homo @ crop_to_image.T
    out = pts.copy()
    out[:, :2] = restored[:, :2]
    return out


def update_roi_from_landmarks(
    landmarks_px: np.ndarray,
    image_shape: tuple[int, int],
    margin_ratio: float = 0.25,
) -> PoseRoi | None:
    if landmarks_px is None or len(landmarks_px) == 0:
        return None
    h, w = image_shape
    xy = np.asarray(landmarks_px, dtype=np.float32)[:, :2]
    valid = np.isfinite(xy).all(axis=1)
    if not np.any(valid):
        return None
    xy = xy[valid]
    x1, y1 = np.min(xy, axis=0)
    x2, y2 = np.max(xy, axis=0)
    size = max(x2 - x1, y2 - y1)
    if size <= 1.0:
        return None
    margin = size * margin_ratio
    width = min(float(w), max(1.0, float(size + 2.0 * margin)))
    height = min(float(h), max(1.0, float(size + 2.0 * margin)))
    return PoseRoi(
        center_x=float(np.clip((x1 + x2) * 0.5, 0.0, float(w))),
        center_y=float(np.clip((y1 + y2) * 0.5, 0.0, float(h))),
        width=width,
        height=height,
        rotation=0.0,
    )


def _extract_detector_tensors(outputs: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    raw_boxes: np.ndarray | None = None
    raw_scores: np.ndarray | None = None
    for value in outputs.values():
        arr = np.asarray(value)
        if arr.size == POSE_DETECTOR_NUM_BOXES * POSE_DETECTOR_NUM_COORDS:
            raw_boxes = arr.astype(np.float32, copy=False)
        elif arr.size == POSE_DETECTOR_NUM_BOXES or arr.size == POSE_DETECTOR_NUM_BOXES * 1:
            raw_scores = arr.astype(np.float32, copy=False)
    if raw_boxes is None or raw_scores is None:
        available = {name: np.asarray(value).shape for name, value in outputs.items()}
        raise ExperimentalPipelineError(
            "detector_decode",
            f"could not identify raw detector box/score tensors. Available Core ML outputs: {available}",
        )
    return raw_boxes, raw_scores


def _nms_pose_detections(candidates: list[PoseDetection], iou_threshold: float) -> list[PoseDetection]:
    kept: list[PoseDetection] = []
    for candidate in candidates:
        if all(_bbox_iou(candidate.bbox_xyxy, item.bbox_xyxy) <= iou_threshold for item in kept):
            kept.append(candidate)
    return kept


def _bbox_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = area_a + area_b - inter
    if denom <= 1e-8:
        return 0.0
    return float(inter / denom)


def _rotated_rect_corners(
    center_x: float,
    center_y: float,
    width: float,
    height: float,
    rotation: float,
) -> np.ndarray:
    half_w = width * 0.5
    half_h = height * 0.5
    local = np.asarray(
        [
            [-half_w, -half_h],
            [half_w, -half_h],
            [half_w, half_h],
            [-half_w, half_h],
        ],
        dtype=np.float32,
    )
    cos_r = math.cos(rotation)
    sin_r = math.sin(rotation)
    rot = np.asarray([[cos_r, -sin_r], [sin_r, cos_r]], dtype=np.float32)
    return local @ rot.T + np.asarray([center_x, center_y], dtype=np.float32)


def _normalize_radians(value: float) -> float:
    return float(value - 2.0 * math.pi * math.floor((value + math.pi) / (2.0 * math.pi)))


def _sigmoid(value: float | np.ndarray) -> float | np.ndarray:
    arr = np.asarray(value, dtype=np.float32)
    out = 1.0 / (1.0 + np.exp(-np.clip(arr, -100.0, 100.0)))
    if np.isscalar(value):
        return float(out)
    return out


def draw_pose_landmarks(
    frame_bgr: np.ndarray,
    landmarks_px: np.ndarray | None,
    color: tuple[int, int, int] = (0, 255, 0),
    point_color: tuple[int, int, int] = (0, 0, 255),
) -> np.ndarray:
    out = frame_bgr.copy()
    if landmarks_px is None:
        return out
    pts = np.asarray(landmarks_px, dtype=np.float32)
    for a, b in BLAZEPOSE_CONNECTIONS:
        if a < len(pts) and b < len(pts):
            pa = tuple(np.round(pts[a, :2]).astype(int))
            pb = tuple(np.round(pts[b, :2]).astype(int))
            cv2.line(out, pa, pb, color, 2, cv2.LINE_AA)
    for point in pts[:, :2]:
        cv2.circle(out, tuple(np.round(point).astype(int)), 3, point_color, -1, cv2.LINE_AA)
    return out


def write_feasibility_report(path: str | Path, status: PoseCoreMLStageStatus, details: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MediaPipe Pose Heavy Core ML Pipeline Feasibility",
        "",
        "## Stage Status",
    ]
    for field_name in (
        "task_extraction",
        "tflite_inspection",
        "coreml_conversion",
        "detector_inference",
        "detector_decode",
        "roi_crop",
        "landmark_inference",
        "coordinate_restore",
        "tracking",
        "comparison",
    ):
        lines.append(f"- {field_name}: `{getattr(status, field_name)}`")
    if status.failures:
        lines.extend(["", "## Failures"])
        for failure in status.failures:
            lines.append(f"- `{failure['stage']}`: {failure['message']}")
    lines.extend(["", "## Details"])
    for key, value in details.items():
        lines.append(f"- {key}: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _compute_units(ct: Any, value: str):
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
