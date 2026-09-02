"""MediaPipe Pose Landmarker (BlazePose GHUM) in VIDEO running mode.

This is the second benchmark arm: one RGB frame in, 3D body pose out, with no
separate lifter. VIDEO mode is required, not IMAGE mode — it carries detection
state across frames, which is the fair comparison against our 27-frame
temporal window.

The landmarker emits 33 BlazePose joints in two spaces: normalized image
coordinates (x, y in [0,1], z relative) and world landmarks in metres with the
hip midpoint as origin. Both are mapped to H36M17 by the same synthesis rule
our COCO17 adapter uses, so the two arms are scored on identical joints.
"""

from __future__ import annotations

import numpy as np

from bpt.benchmarks.pose.adapters.blazepose import blazepose33_to_h36m17

METRE_TO_MILLIMETRE = 1000.0


class MediaPipePoseEstimator:
    """Wraps ``PoseLandmarker`` in VIDEO mode with monotonic timestamps."""

    def __init__(
        self,
        model_path: str,
        num_poses: int = 1,
        min_pose_detection_confidence: float = 0.5,
        min_pose_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        delegate: str = "cpu",
    ):
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        self._mp = mp
        self._vision = mp_vision
        delegates = {
            "cpu": mp_python.BaseOptions.Delegate.CPU,
            "gpu": mp_python.BaseOptions.Delegate.GPU,
        }
        options = mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(
                model_asset_path=str(model_path), delegate=delegates[delegate]
            ),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=num_poses,
            min_pose_detection_confidence=min_pose_detection_confidence,
            min_pose_presence_confidence=min_pose_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
            output_segmentation_masks=False,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        self._last_timestamp_ms = -1

    def detect(self, frame_rgb: np.ndarray, timestamp_ms: int):
        """Return ``(landmarks_2d [33,3], world_3d [33,3])`` or ``(None, None)``.

        ``timestamp_ms`` must strictly increase; VIDEO mode rejects a repeat.
        """

        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp_ms
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(frame_rgb))
        result = self._landmarker.detect_for_video(image, timestamp_ms)
        if not result.pose_landmarks:
            return None, None
        landmarks = np.asarray(
            [[point.x, point.y, getattr(point, "visibility", 1.0)] for point in result.pose_landmarks[0]],
            dtype=np.float32,
        )
        world = np.asarray(
            [[point.x, point.y, point.z] for point in result.pose_world_landmarks[0]], dtype=np.float32
        )
        return landmarks, world

    def close(self):
        self._landmarker.close()


def landmarks_to_pixels(landmarks_2d: np.ndarray, width: int, height: int) -> np.ndarray:
    """Normalized landmarks to pixel ``[33,3]`` with visibility kept as score."""

    landmarks = np.asarray(landmarks_2d, dtype=np.float32).copy()
    landmarks[:, 0] *= float(width)
    landmarks[:, 1] *= float(height)
    return landmarks


def to_h36m17_pixels(landmarks_2d: np.ndarray, width: int, height: int) -> np.ndarray:
    return blazepose33_to_h36m17(landmarks_to_pixels(landmarks_2d, width, height))


def to_h36m17_millimetres(world_3d: np.ndarray) -> np.ndarray:
    """World landmarks (metres, hip-centred) to H36M17 millimetres."""

    world = np.asarray(world_3d, dtype=np.float64) * METRE_TO_MILLIMETRE
    padded = np.concatenate([world, np.ones((len(world), 1))], axis=1)
    return blazepose33_to_h36m17(padded)[:, :3]
