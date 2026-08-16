from pathlib import Path
import sys

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None


class MotionAGFormerRunner:
    """Lazy MotionAGFormer wrapper for staged smoke inference.

    Unit tests can inject a fake model. Real MotionAGFormer imports and PyTorch
    checkpoint loading happen only when no model is injected.
    """

    def __init__(
        self,
        repo_dir="external/MotionAGFormer",
        config_path=None,
        checkpoint_path=None,
        device="auto",
        window_size=243,
        model=None,
    ):
        self.repo_dir = Path(repo_dir)
        self.config_path = Path(config_path) if config_path else self.repo_dir / "configs/h36m/MotionAGFormer-base.yaml"
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self.device = device
        self.window_size = int(window_size)
        if model is not None:
            self.model = model
            self.torch = None
            self.device_name = "injected"
        else:
            self.model, self.torch, self.device_name = self._load_real_model()

    def predict_3d(self, window_2d):
        arr = _as_array(window_2d)
        if arr.shape[-3:] != (self.window_size, 17, arr.shape[-1]):
            raise ValueError(
                f"window_2d must have shape ({self.window_size}, 17, C) or batched equivalent",
            )
        if arr.shape[-1] not in (2, 3):
            raise ValueError("MotionAGFormer input must have 2 or 3 channels")
        batched = arr[None, ...] if arr.ndim == 3 else arr
        if self.torch is None:
            pred = self.model.predict(batched) if hasattr(self.model, "predict") else self.model(batched)
            pred = np.asarray(pred, dtype="float32")
        else:
            tensor = self.torch.from_numpy(batched.astype("float32")).to(self.device_name)
            self.model.eval()
            with self.torch.no_grad():
                pred = self.model(tensor).detach().cpu().numpy().astype("float32")
        if arr.ndim == 3:
            return pred[0]
        return pred

    def _load_real_model(self):
        if not self.repo_dir.exists():
            raise FileNotFoundError(f"MotionAGFormer repo not found: {self.repo_dir}")
        if self.checkpoint_path is None:
            raise FileNotFoundError(
                "MotionAGFormer checkpoint is required. Download an official H36M checkpoint "
                "from external/MotionAGFormer README and pass --checkpoint.",
            )
        if not self.checkpoint_path.exists():
            raise FileNotFoundError(f"MotionAGFormer checkpoint not found: {self.checkpoint_path}")
        if not self.config_path.exists():
            raise FileNotFoundError(f"MotionAGFormer config not found: {self.config_path}")
        try:
            import torch
        except ImportError as exc:
            raise ImportError("PyTorch is required for MotionAGFormer inference") from exc

        repo_path = str(self.repo_dir.resolve())
        if repo_path not in sys.path:
            sys.path.insert(0, repo_path)
        try:
            from utils.learning import load_model
            from utils.tools import get_config
        except Exception as exc:
            raise ImportError(f"Could not import MotionAGFormer code from {self.repo_dir}: {exc}") from exc

        args = get_config(str(self.config_path))
        self.window_size = int(getattr(args, "n_frames", self.window_size))
        device_name = self._resolve_device(torch)
        model = load_model(args)
        checkpoint = _load_trusted_legacy_checkpoint(
            torch,
            self.checkpoint_path,
            map_location=device_name,
        )
        state = checkpoint.get("model", checkpoint.get("model_pos", checkpoint))
        state = _strip_dataparallel_prefix(state)
        model.load_state_dict(state, strict=True)
        model.to(device_name)
        model.eval()
        return model, torch, device_name

    def _resolve_device(self, torch):
        if self.device != "auto":
            return self.device
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"


def _as_array(values):
    if np is None:  # pragma: no cover
        raise ImportError("numpy is required for MotionAGFormer runner")
    return np.asarray(values, dtype="float32")


def _load_trusted_legacy_checkpoint(torch, checkpoint_path, map_location):
    # Official MotionAGFormer checkpoints are legacy pickle checkpoints. Under
    # PyTorch 2.6+, torch.load defaults to weights_only=True, which rejects them.
    # Only use weights_only=False for trusted official checkpoints.
    try:
        return torch.load(
            str(checkpoint_path),
            map_location=map_location,
            weights_only=False,
        )
    except TypeError:
        return torch.load(str(checkpoint_path), map_location=map_location)


def _strip_dataparallel_prefix(state):
    if not isinstance(state, dict):
        return state
    if not state or not all(isinstance(key, str) for key in state):
        return state
    if not any(key.startswith("module.") for key in state):
        return state
    return {
        key[7:] if key.startswith("module.") else key: value
        for key, value in state.items()
    }
