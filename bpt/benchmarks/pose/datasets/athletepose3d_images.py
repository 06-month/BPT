"""Resolve AthletePose3D RGB frames for the annotation records.

Records carry ``image_path`` strings like ``pose_3d/valid_img/S1_Axel_1_0.jpg``
but the images ship in a separate archive. This module resolves those strings
against a local image root, tolerating the common case where the extracted
directory starts one or two levels deeper than the recorded prefix, and reports
missing frames instead of silently scoring fewer of them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class ImageResolution:
    root: Path
    prefix_dropped: int
    found: int
    missing: int

    @property
    def complete(self) -> bool:
        return self.missing == 0


def resolve_root(image_root: str | Path, sample_paths: list[str]) -> tuple[Path, int]:
    """Find how many leading path components of ``image_path`` to drop."""

    root = Path(image_root)
    if not root.is_dir():
        raise FileNotFoundError(f"image root does not exist: {root}")
    sample = [Path(path) for path in sample_paths if path]
    if not sample:
        return root, 0
    for drop in range(len(sample[0].parts)):
        if all((root / Path(*path.parts[drop:])).exists() for path in sample[:8]):
            return root, drop
    raise FileNotFoundError(
        f"none of {sample[0]} resolve under {root}; point --image-root at the directory holding the frames"
    )


def frame_paths(image_root: str | Path, image_paths: list[str], prefix_dropped: int) -> list[Path]:
    root = Path(image_root)
    return [root / Path(*Path(path).parts[prefix_dropped:]) for path in image_paths]


def check_sequence(image_root: str | Path, image_paths: list[str], prefix_dropped: int) -> ImageResolution:
    paths = frame_paths(image_root, image_paths, prefix_dropped)
    missing = sum(0 if path.exists() else 1 for path in paths)
    return ImageResolution(Path(image_root), prefix_dropped, len(paths) - missing, missing)


def load_frames_bgr(paths: list[Path]) -> np.ndarray:
    """Read frames in order. Raises on the first unreadable file."""

    import cv2

    frames = []
    for path in paths:
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if frame is None:
            raise FileNotFoundError(f"could not read frame: {path}")
        frames.append(frame)
    return np.stack(frames)


def iter_frames_bgr(paths: list[Path]):
    """Yield ``(index, frame_bgr)`` one at a time, for long sequences."""

    import cv2

    for index, path in enumerate(paths):
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if frame is None:
            raise FileNotFoundError(f"could not read frame: {path}")
        yield index, frame
