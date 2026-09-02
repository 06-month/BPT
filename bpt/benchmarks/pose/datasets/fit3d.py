"""Fit3D loader for the official TEST archive layout.

The distributed TEST archive contains only ``videos/<action>.mp4`` and
``camera_parameters/<action>.json`` per subject; it carries no 2D or 3D
ground truth. This loader therefore exposes RGB frames and camera geometry
for inference, and loads ``joints3d_25`` only if a train-style ground-truth
directory is supplied separately. It never fabricates ground truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Fit3DSequence:
    subject: str
    action: str
    video_path: Path
    camera_path: Path

    @property
    def key(self) -> str:
        return f"{self.subject}/{self.action}"


def discover(root: str | Path, split: str = "test") -> list[Fit3DSequence]:
    split_dir = Path(root) / split if (Path(root) / split).is_dir() else Path(root)
    sequences = []
    for subject_dir in sorted(p for p in split_dir.iterdir() if p.is_dir()):
        video_dir = subject_dir / "videos"
        camera_dir = subject_dir / "camera_parameters"
        if not video_dir.is_dir():
            continue
        for video_path in sorted(video_dir.glob("*.mp4")):
            sequences.append(
                Fit3DSequence(
                    subject=subject_dir.name,
                    action=video_path.stem,
                    video_path=video_path,
                    camera_path=camera_dir / f"{video_path.stem}.json",
                )
            )
    return sequences


def load_camera(path: str | Path) -> dict:
    """Return camera parameters shaped for ``geometry.projection``."""

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    with_distortion = raw["intrinsics_w_distortion"]
    without_distortion = raw["intrinsics_wo_distortion"]
    return {
        "extrinsics": {
            "R": np.asarray(raw["extrinsics"]["R"], dtype=np.float64).reshape(3, 3),
            "T": np.asarray(raw["extrinsics"]["T"], dtype=np.float64).reshape(3),
        },
        "intrinsics_w_distortion": {
            "f": np.asarray(with_distortion["f"], dtype=np.float64).reshape(2),
            "c": np.asarray(with_distortion["c"], dtype=np.float64).reshape(2),
            "k": np.asarray(with_distortion["k"], dtype=np.float64).reshape(3),
            "p": np.asarray(with_distortion["p"], dtype=np.float64).reshape(2),
        },
        "intrinsics_wo_distortion": {
            "f": np.asarray(without_distortion["f"], dtype=np.float64).reshape(2),
            "c": np.asarray(without_distortion["c"], dtype=np.float64).reshape(2),
        },
    }


def video_info(path: str | Path) -> dict:
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(f"cannot open video: {path}")
    try:
        return {
            "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": float(capture.get(cv2.CAP_PROP_FPS)),
            "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }
    finally:
        capture.release()


def iter_frames(path: str | Path, start: int = 0, stop: int | None = None):
    """Yield ``(frame_index, rgb_frame)`` in decode order."""

    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise FileNotFoundError(f"cannot open video: {path}")
    try:
        if start:
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(start))
        index = int(start)
        while stop is None or index < stop:
            ok, frame = capture.read()
            if not ok:
                break
            yield index, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            index += 1
    finally:
        capture.release()


def load_joints3d_25(ground_truth_root: str | Path, subject: str, action: str) -> np.ndarray | None:
    """Load train-style ``joints3d_25`` world joints if private GT is supplied."""

    path = Path(ground_truth_root) / subject / "joints3d_25" / f"{action}.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    joints = raw["joints3d_25"] if isinstance(raw, dict) else raw
    return np.asarray(joints, dtype=np.float64)


def has_ground_truth(ground_truth_root: str | Path | None, subject: str, action: str) -> bool:
    if ground_truth_root is None:
        return False
    return load_joints3d_25(ground_truth_root, subject, action) is not None
