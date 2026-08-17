"""Shared paths for MediaPipe Hand Landmarker Core ML feasibility scripts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TASK_PATH = ROOT / "assets/mediapipe/hand_landmarker.task"
OUTPUT_DIR = ROOT / "assets/coreml"
EXTRACT_DIR = OUTPUT_DIR / "mediapipe_hand_tflite"

INSPECTION_JSON = OUTPUT_DIR / "mediapipe_hand_coreml_inspection.json"
CONVERSION_FAILURE_PATH = OUTPUT_DIR / "mediapipe_hand_coreml_conversion_failure.txt"

HAND_DETECTOR_TFLITE = EXTRACT_DIR / "hand_detector.tflite"
HAND_LANDMARKS_TFLITE = EXTRACT_DIR / "hand_landmarks_detector.tflite"

HAND_DETECTOR_COREML = OUTPUT_DIR / "mediapipe_hand_detector.mlpackage"
HAND_LANDMARKS_COREML = OUTPUT_DIR / "mediapipe_hand_landmarks_detector.mlpackage"

TASK_MODEL_NAMES = (
    "hand_detector.tflite",
    "hand_landmarks_detector.tflite",
)
