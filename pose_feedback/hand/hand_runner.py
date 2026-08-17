from pose_feedback.wrist.geometry import crop_to_image_coords

try:
    import numpy as np
except ModuleNotFoundError:
    class _NumpyCompat:
        @staticmethod
        def array(values, dtype=None):
            return tuple(float(value) for value in values)

    np = _NumpyCompat()


class HandRunner:
    def __init__(self, mode: str = "crop"):
        if mode not in ("crop", "fullframe"):
            raise ValueError('mode must be "crop" or "fullframe"')
        self.mode = mode

    def run_crop(self, image, crop_box):
        raise NotImplementedError("Crop-mode hand runtime is not connected yet.")

    def run_fullframe(self, image):
        raise NotImplementedError("Fullframe hand runtime is not connected yet.")


def mp_wrist_to_image_coords(hand_landmarks, image_w, image_h):
    landmark = hand_landmarks.landmark[0]
    return np.array(
        [landmark.x * image_w, landmark.y * image_h],
        dtype="float32",
    )


def mp_wrist_crop_to_image_coords(hand_landmarks, crop_box):
    landmark = hand_landmarks.landmark[0]
    return np.array(
        crop_to_image_coords(landmark, *crop_box),
        dtype="float32",
    )
