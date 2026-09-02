"""M0 temporal indexing with explicit target-frame identity."""

from __future__ import annotations

import numpy as np


def temporal_window_indices(
    sequence_length: int,
    target_frame: int,
    window_size: int = 27,
    lookahead: int = 5,
) -> np.ndarray:
    if sequence_length <= 0:
        raise ValueError("sequence_length must be positive")
    if not 0 <= target_frame < sequence_length:
        raise IndexError(f"target frame {target_frame} outside sequence of {sequence_length}")
    if not 0 <= lookahead < window_size:
        raise ValueError("lookahead must be in [0, window_size)")
    target_index = window_size - 1 - lookahead
    raw = np.arange(window_size, dtype=np.int64) + target_frame - target_index
    return np.clip(raw, 0, sequence_length - 1)


def build_temporal_window(
    sequence: np.ndarray,
    target_frame: int,
    window_size: int = 27,
    lookahead: int = 5,
) -> tuple[np.ndarray, np.ndarray, int]:
    sequence = np.asarray(sequence)
    indices = temporal_window_indices(len(sequence), target_frame, window_size, lookahead)
    target_index = window_size - 1 - lookahead
    if indices[target_index] != target_frame:
        raise AssertionError("temporal target identity was lost")
    return sequence[indices], indices, target_index


def full_real_context_mask(sequence_length: int, window_size: int = 27, lookahead: int = 5) -> np.ndarray:
    target_index = window_size - 1 - lookahead
    frame_ids = np.arange(sequence_length)
    return (frame_ids >= target_index) & (frame_ids <= sequence_length - 1 - lookahead)
