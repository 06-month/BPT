try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None


class EMA3DSmoother:
    def __init__(self, alpha=0.3):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = float(alpha)
        self.value = None

    def update(self, joints_3d):
        if np is None:  # pragma: no cover
            raise ImportError("numpy is required for 3D smoothing")
        current = np.asarray(joints_3d, dtype="float32")
        if self.value is None:
            self.value = current.copy()
        else:
            self.value = self.alpha * current + (1.0 - self.alpha) * self.value
        return self.value.copy()

    def reset(self):
        self.value = None
