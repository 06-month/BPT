import os
from pathlib import Path
from types import SimpleNamespace

from pose_feedback.hand.hand_runner import HandRunner, mp_wrist_crop_to_image_coords
from pose_feedback.hand.mediapipe_hand_runner import (
    MediaPipeHandsRuntimeError,
    _crop_image,
    _to_mediapipe_rgb,
)


class MediaPipeHandLandmarkerRunner(HandRunner):
    """MediaPipe Tasks HandLandmarker crop-mode runner.

    This runner uses the same normalized return schema as MediaPipeHandsRunner:
    crop-local landmarks are kept in `hand_landmarks`, and `wrist_px` is restored
    to original frame coordinates using the crop box.
    """

    def __init__(
        self,
        task_model_path,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.3,
        min_presence_confidence: float = 0.3,
        min_tracking_confidence: float = 0.3,
        input_color_format: str = "BGR",
        running_mode: str = "image",
        delegate: str = "cpu",
        landmarker=None,
        mediapipe_module=None,
    ):
        super().__init__(mode="crop")
        if input_color_format not in ("BGR", "RGB"):
            raise ValueError('input_color_format must be "BGR" or "RGB"')
        if running_mode not in ("image", "video"):
            raise ValueError('running_mode must be "image" or "video"')
        if delegate not in ("cpu", "gpu"):
            raise ValueError('delegate must be "cpu" or "gpu"')
        self.input_color_format = input_color_format
        self.running_mode = running_mode
        self.delegate = delegate
        self._last_timestamp_ms = None
        self._mp = mediapipe_module

        if landmarker is None:
            # Force CPU for the Python smoke path unless GPU is explicitly asked
            # for. On macOS the Tasks graph still spins up a GL context, but the
            # XNNPACK CPU delegate avoids relying on a GPU inference delegate.
            if delegate == "cpu":
                os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
            model_path = Path(task_model_path)
            if not model_path.exists():
                raise MediaPipeHandsRuntimeError(
                    "MediaPipe HandLandmarker task model is missing: "
                    f"{model_path}. Place a hand_landmarker.task file in the "
                    "repository and pass --hand-landmarker-task.",
                )
            try:
                import mediapipe as mp
                from mediapipe.tasks import python
                from mediapipe.tasks.python import vision
            except ModuleNotFoundError as exc:
                raise ImportError(
                    "mediapipe is required to create MediaPipeHandLandmarkerRunner.",
                ) from exc
            self._mp = mp
            task_running_mode = (
                vision.RunningMode.VIDEO
                if running_mode == "video"
                else vision.RunningMode.IMAGE
            )
            delegate_enum = (
                python.BaseOptions.Delegate.GPU
                if delegate == "gpu"
                else python.BaseOptions.Delegate.CPU
            )
            options = vision.HandLandmarkerOptions(
                base_options=python.BaseOptions(
                    model_asset_path=str(model_path),
                    delegate=delegate_enum,
                ),
                running_mode=task_running_mode,
                num_hands=max_num_hands,
                min_hand_detection_confidence=min_detection_confidence,
                min_hand_presence_confidence=min_presence_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
            landmarker = vision.HandLandmarker.create_from_options(options)
        self.landmarker = landmarker

    def run_crop(self, image, crop_box, timestamp_ms=None):
        crop = _crop_image(image, crop_box)
        crop_rgb = _to_mediapipe_rgb(crop, self.input_color_format)
        mp_image = self._make_mp_image(crop_rgb)
        if self.running_mode == "video":
            timestamp_ms = self._validate_video_timestamp(timestamp_ms)
            result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
        else:
            result = self.landmarker.detect(mp_image)

        hand_landmarks_list = getattr(result, "hand_landmarks", None) or []
        hand_world_list = getattr(result, "hand_world_landmarks", None) or []
        handedness_list = getattr(result, "handedness", None) or []

        normalized_results = []
        for index, landmarks in enumerate(hand_landmarks_list):
            hand_landmarks = _landmark_list(landmarks)
            hand_world_landmarks = (
                _landmark_list(hand_world_list[index])
                if index < len(hand_world_list)
                else None
            )
            handedness = _task_handedness_label(
                handedness_list[index] if index < len(handedness_list) else None,
            )
            normalized_results.append(
                {
                    "hand_landmarks": hand_landmarks,
                    "hand_world_landmarks": hand_world_landmarks,
                    "handedness": handedness,
                    "wrist_px": mp_wrist_crop_to_image_coords(
                        hand_landmarks,
                        crop_box,
                    ),
                    "crop_box": crop_box,
                },
            )
        return normalized_results

    def close(self):
        close = getattr(self.landmarker, "close", None)
        if close is not None:
            close()

    def _make_mp_image(self, crop_rgb):
        if self._mp is None:
            return crop_rgb
        return self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=crop_rgb,
        )

    def _validate_video_timestamp(self, timestamp_ms):
        if timestamp_ms is None:
            raise ValueError("timestamp_ms is required when running_mode='video'")
        timestamp_ms = int(timestamp_ms)
        if self._last_timestamp_ms is not None and timestamp_ms <= self._last_timestamp_ms:
            raise ValueError(
                "MediaPipe Tasks VIDEO mode requires monotonically increasing "
                f"timestamp_ms per runner instance: got {timestamp_ms} after "
                f"{self._last_timestamp_ms}",
            )
        self._last_timestamp_ms = timestamp_ms
        return timestamp_ms


def _landmark_list(landmarks):
    if hasattr(landmarks, "landmark"):
        return landmarks
    return SimpleNamespace(landmark=list(landmarks))


def _task_handedness_label(handedness):
    if not handedness:
        return None
    category = handedness[0]
    label = (
        getattr(category, "category_name", None)
        or getattr(category, "display_name", None)
        or getattr(category, "label", None)
    )
    if label in ("Left", "Right"):
        return label
    return None
