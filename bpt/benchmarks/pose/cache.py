"""Resumable npz+json cache for per-sequence benchmark stage outputs.

Every cache entry is one compressed ``.npz`` of arrays plus a ``.json``
sidecar holding the cache version and the metadata the entry was produced
with. A resumed run reloads an entry only when both the version and the
caller's expected metadata still match, so a changed model, preprocessing
policy or temporal contract invalidates stale results instead of silently
mixing them into a report.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


CACHE_VERSION = 1


def entry_paths(root: str | Path, key: str) -> tuple[Path, Path]:
    base = Path(root) / key
    return base.parent / f"{base.name}.npz", base.parent / f"{base.name}.json"


def save(root: str | Path, key: str, arrays: dict, metadata: dict) -> Path:
    array_path, meta_path = entry_paths(root, key)
    array_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {name: np.asarray(value) for name, value in arrays.items()}
    np.savez_compressed(array_path, **payload)
    meta_path.write_text(
        json.dumps(
            {
                "version": CACHE_VERSION,
                "key": key,
                "shapes": {name: list(value.shape) for name, value in payload.items()},
                "metadata": metadata,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return array_path


def load(root: str | Path, key: str, expect: dict | None = None) -> tuple[dict, dict] | None:
    """Return ``(arrays, metadata)``, or ``None`` when missing or stale."""

    array_path, meta_path = entry_paths(root, key)
    if not array_path.exists() or not meta_path.exists():
        return None
    try:
        sidecar = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if sidecar.get("version") != CACHE_VERSION:
        return None
    metadata = sidecar.get("metadata", {})
    if expect and any(metadata.get(name) != value for name, value in expect.items()):
        return None
    with np.load(array_path) as handle:
        arrays = {name: handle[name] for name in handle.files}
    return arrays, metadata


def is_cached(root: str | Path, key: str, expect: dict | None = None) -> bool:
    return load(root, key, expect) is not None


def cached_keys(root: str | Path) -> list[str]:
    root = Path(root)
    if not root.exists():
        return []
    keys = []
    for meta_path in sorted(root.rglob("*.json")):
        if meta_path.with_suffix(".npz").exists():
            keys.append(str(meta_path.relative_to(root).with_suffix("")))
    return keys
