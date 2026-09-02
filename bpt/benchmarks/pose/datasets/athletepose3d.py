"""AthletePose3D loader for the official ``valid.pkl`` / ``train.pkl`` records.

Each record is one annotated frame carrying H36M17 image-space joints
(``joint_3d_image``: x, y pixels and root-relative depth), metric camera-space
joints in millimetres (``joint_3d_camera``), the person box, the source video
size and fps. Records are grouped into per-camera sequences ordered by
``imageid`` so the 27-frame temporal window sees real neighbouring frames.

Only the validation split is used for evaluation; ``train.pkl`` is loadable for
inspection but must never be reported as an evaluation result.
"""

from __future__ import annotations

import pickle
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np


H36M17_JOINT_COUNT = 17


@dataclass(frozen=True)
class AthleteSequence:
    subject: str
    action: str
    subaction: str
    camera: str
    records: list

    @property
    def key(self) -> str:
        return f"{self.subject}/{self.action}/{self.subaction}/{self.camera}"

    def __len__(self) -> int:
        return len(self.records)


def load_records(source: str | Path, member: str | None = None, limit: int | None = None) -> list:
    """Load records from a ``.pkl`` file or from a member inside a ``.zip``."""

    source = Path(source)
    if source.suffix == ".zip":
        with zipfile.ZipFile(source) as archive:
            name = member or _default_member(archive)
            records = pickle.loads(archive.read(name))
    else:
        with source.open("rb") as handle:
            records = pickle.load(handle)
    if not isinstance(records, list):
        raise ValueError(f"expected a list of frame records, got {type(records)!r}")
    return records[:limit] if limit else records


def _default_member(archive: zipfile.ZipFile) -> str:
    for name in archive.namelist():
        if name.endswith("valid.pkl"):
            return name
    raise FileNotFoundError("no valid.pkl inside archive; pass member explicitly")


def group_sequences(records: list, min_length: int = 1) -> list[AthleteSequence]:
    grouped: dict[tuple, list] = {}
    for record in records:
        key = (record["subject"], record["action"], record["subaction"], record["cameraid"])
        grouped.setdefault(key, []).append(record)
    sequences = []
    for (subject, action, subaction, camera), frames in sorted(grouped.items()):
        frames.sort(key=lambda item: int(item["imageid"]))
        if len(frames) < min_length:
            continue
        sequences.append(AthleteSequence(subject, action, subaction, camera, frames))
    return sequences


def sequence_arrays(sequence: AthleteSequence) -> dict:
    """Stack one sequence into the arrays the metrics modules consume."""

    frames = sequence.records
    joints_image = np.stack([np.asarray(f["joint_3d_image"], dtype=np.float64) for f in frames])
    joints_camera = np.stack([np.asarray(f["joint_3d_camera"], dtype=np.float64) for f in frames])
    if joints_image.shape[1:] != (H36M17_JOINT_COUNT, 3):
        raise ValueError(f"expected H36M17 joints, got {joints_image.shape}")
    first = frames[0]
    return {
        "key": sequence.key,
        "joints_2d": joints_image[..., :2],
        "joints_3d_image": joints_image,
        "joints_3d_camera": joints_camera,
        "boxes_xyxy": np.stack([np.asarray(f["box"], dtype=np.float64) for f in frames]),
        "image_paths": [f["image_path"] for f in frames],
        "frame_ids": np.asarray([int(f["imageid"]) for f in frames], dtype=np.int64),
        "width": int(first["video_width"]),
        "height": int(first["video_height"]),
        "fps": float(first["fps"]),
        "camera": sequence.camera,
        "units": "millimetre",
    }


def load_camera_parameters(path: str | Path) -> dict:
    """Load ``cam_param.json`` shaped for ``geometry.projection.athlete_*``."""

    import json

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    cameras = {}
    for name, camera in raw.items():
        cameras[name] = {
            "affine_intrinsics_matrix": np.asarray(camera["affine_intrinsics_matrix"], dtype=np.float64),
            "extrinsic_matrix": np.asarray(camera["extrinsic_matrix"], dtype=np.float64).reshape(3, 3),
            "xyz": np.asarray(camera["xyz"], dtype=np.float64).reshape(3),
            "distortion": np.asarray(camera.get("distortion", []), dtype=np.float64),
        }
    return cameras
