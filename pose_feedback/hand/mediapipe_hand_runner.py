import os

from pose_feedback.hand.hand_runner import HandRunner, mp_wrist_crop_to_image_coords


class MediaPipeHandsRuntimeError(RuntimeError):
    pass


class MediaPipeHandsRunner(HandRunner):
    def __init__(
        self,
        static_image_mode: bool = False,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        cpu_only: bool = True,
        input_color_format: str = "BGR",
        hands=None,
    ):
        super().__init__(mode="crop")
        if input_color_format not in ("BGR", "RGB"):
            raise ValueError('input_color_format must be "BGR" or "RGB"')
        if cpu_only:
            os.environ["MEDIAPIPE_DISABLE_GPU"] = "1"
        if hands is None:
            try:
                import mediapipe as mp
            except ModuleNotFoundError as exc:
                raise ImportError(
                    "mediapipe is required to create MediaPipeHandsRunner "
                    "without an injected hands object.",
                ) from exc
            try:
                hands = mp.solutions.hands.Hands(
                    static_image_mode=static_image_mode,
                    max_num_hands=max_num_hands,
                    min_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence,
                )
            except Exception as exc:
                raise MediaPipeHandsRuntimeError(
                    "Legacy mp.solutions.hands.Hands failed during construction. "
                    "This can happen on macOS/GL runtimes when MediaPipe cannot "
                    "create its kGpuService/OpenGL context. Keep this runner "
                    "optional; use a clean conda environment or implement a "
                    "MediaPipe Tasks HandLandmarker runner for a more reliable "
                    "runtime path."
                ) from exc
        self.hands = hands
        self.input_color_format = input_color_format

    def run_crop(self, image, crop_box):
        crop = _crop_image(image, crop_box)
        results = self.hands.process(_to_mediapipe_rgb(crop, self.input_color_format))
        hand_landmarks_list = getattr(results, "multi_hand_landmarks", None) or []
        hand_world_list = getattr(results, "multi_hand_world_landmarks", None) or []
        handedness_list = getattr(results, "multi_handedness", None) or []

        normalized_results = []
        for index, hand_landmarks in enumerate(hand_landmarks_list):
            hand_world_landmarks = (
                hand_world_list[index] if index < len(hand_world_list) else None
            )
            handedness = _handedness_label(
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
        close = getattr(self.hands, "close", None)
        if close is not None:
            close()


def _crop_image(image, crop_box):
    x1, y1, x2, y2 = (int(value) for value in crop_box)
    try:
        return image[y1:y2, x1:x2]
    except TypeError:
        return [row[x1:x2] for row in image[y1:y2]]


def _to_mediapipe_rgb(crop, input_color_format):
    if input_color_format == "RGB":
        return crop
    shape = getattr(crop, "shape", None)
    if shape is not None and len(shape) >= 3 and shape[2] >= 3:
        try:
            import cv2

            return cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        except ModuleNotFoundError:
            return crop[:, :, ::-1]
    return crop


def _handedness_label(handedness):
    if handedness is None:
        return None
    classification = getattr(handedness, "classification", None)
    if not classification:
        return None
    label = getattr(classification[0], "label", None)
    if label in ("Left", "Right"):
        return label
    return None
