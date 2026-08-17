try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None


class MotionAGFormerWindowBuilder:
    """Build fixed-length MotionAGFormer windows for offline and low-latency tests."""

    def __init__(self, window_size=243):
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        self.window_size = int(window_size)

    def build_full_centered(self, sequence, center_index):
        seq = _sequence(sequence)
        indices = self.full_centered_indices(len(seq), center_index)
        return seq[indices], indices

    def build_lookahead_padded(self, sequence, current_index, lookahead):
        if lookahead < 0:
            raise ValueError("lookahead must be >= 0")
        seq = _sequence(sequence)
        indices = self.lookahead_indices(len(seq), current_index, lookahead)
        return seq[indices], indices

    def full_centered_indices(self, sequence_length, center_index):
        if sequence_length <= 0:
            raise ValueError("sequence_length must be positive")
        center_index = int(center_index)
        half = self.window_size // 2
        indices = np.arange(center_index - half, center_index - half + self.window_size)
        return np.clip(indices, 0, sequence_length - 1).astype(int)

    def lookahead_indices(self, sequence_length, current_index, lookahead):
        if sequence_length <= 0:
            raise ValueError("sequence_length must be positive")
        current_index = int(current_index)
        lookahead = int(lookahead)
        end = current_index + lookahead
        start = end - self.window_size + 1
        indices = np.arange(start, end + 1)
        return np.clip(indices, 0, sequence_length - 1).astype(int)

    def latency_frames(self, mode, lookahead=None):
        if mode == "full":
            return self.window_size // 2
        if mode == "lookahead":
            if lookahead is None:
                raise ValueError("lookahead is required for lookahead mode")
            return int(lookahead)
        raise ValueError("mode must be 'full' or 'lookahead'")

    def latency_seconds(self, fps, mode, lookahead=None):
        if fps <= 0:
            raise ValueError("fps must be positive")
        return self.latency_frames(mode, lookahead=lookahead) / float(fps)


def _sequence(sequence):
    if np is None:  # pragma: no cover
        raise ImportError("numpy is required for MotionAGFormer window building")
    arr = np.asarray(sequence, dtype="float32")
    if arr.ndim < 2:
        raise ValueError("sequence must include a frame dimension")
    if len(arr) == 0:
        raise ValueError("sequence must not be empty")
    return arr
