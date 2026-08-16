"""Shared paths for MediaPipe Pose Landmarker Core ML feasibility scripts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TASK_PATH = ROOT / "assets/mediapipe/pose_landmarker_heavy.task"
OUTPUT_DIR = ROOT / "assets/coreml"
EXTRACT_DIR = OUTPUT_DIR / "mediapipe_pose_heavy_tflite"
COREML_DIR = OUTPUT_DIR / "mediapipe_pose_heavy_coreml"

INSPECTION_JSON = OUTPUT_DIR / "mediapipe_pose_heavy_coreml_inspection.json"
CONVERSION_REPORT_PATH = OUTPUT_DIR / "mediapipe_pose_heavy_coreml_conversion_report.md"
CONVERSION_FAILURE_PATH = OUTPUT_DIR / "mediapipe_pose_heavy_coreml_conversion_failure.txt"

POSE_DETECTOR_TFLITE = EXTRACT_DIR / "pose_detector.tflite"
POSE_LANDMARKS_TFLITE = EXTRACT_DIR / "pose_landmarks_detector.tflite"

POSE_DETECTOR_COREML = COREML_DIR / "pose_detector.mlpackage"
POSE_LANDMARKS_COREML = COREML_DIR / "pose_landmarks_detector.mlpackage"

TASK_MODEL_NAMES = (
    "pose_detector.tflite",
    "pose_landmarks_detector.tflite",
)
