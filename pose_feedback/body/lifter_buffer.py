class SlidingWindowLifterBuffer:
    def __init__(self, window_size, stride=1, centered=True):
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        if stride <= 0:
            raise ValueError("stride must be positive")
        self.window_size = int(window_size)
        self.stride = int(stride)
        self.centered = bool(centered)
        self.latency_frames = self.window_size // 2 if self.centered else self.window_size - 1
        self._frames = []

    def push(self, frame):
        self._frames.append(frame)
        if len(self._frames) > self.window_size:
            self._frames = self._frames[-self.window_size:]

    def ready(self):
        return len(self._frames) >= self.window_size

    def get_window(self):
        if not self.ready():
            raise ValueError("buffer does not contain a full window")
        return list(self._frames[-self.window_size:])

    def reset(self):
        self._frames = []

    def latency_seconds(self, fps):
        if fps <= 0:
            raise ValueError("fps must be positive")
        return float(self.latency_frames) / float(fps)

    def latency_summary(self, fps=30.0):
        return {
            "latency_frames": self.latency_frames,
            "latency_seconds": self.latency_seconds(fps),
            "fps": float(fps),
        }
