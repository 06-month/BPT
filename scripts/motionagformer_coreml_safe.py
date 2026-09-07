"""Export-only Core ML compatibility helpers for MotionAGFormer-XS.

Core ML rejects tensors with rank > 5. The stock MotionAGFormer attention
(``model.modules.attention.Attention``) builds a rank-6 intermediate:

    qkv = self.qkv(x).reshape(B, T, J, 3, num_heads, head_dim)  # rank 6

This module provides an *export-only* monkeypatch that replaces
``Attention.forward`` with a numerically equivalent implementation whose every
intermediate tensor has rank <= 5. It does this by folding the leading batch
axes before splitting heads:

* spatial mode mixes over joints J and is independent across (B, T), so we run
  attention on a merged ``[B*T, J, C]`` tensor.
* temporal mode mixes over frames T and is independent across (B, J), so we run
  attention on a merged ``[B*J, T, C]`` tensor.

The qkv / proj linear layers and the softmax are applied to exactly the same
per-token values as the original code, so the output is identical up to
floating point. The original repository files are NOT modified; the patch is
applied to live module instances right before tracing.
"""

import sys
import types as _types
from pathlib import Path

import torch
import yaml


ROOT = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT / "external/MotionAGFormer"
CONFIG_PATH = REPO_DIR / "configs/h36m/MotionAGFormer-xsmall.yaml"
CHECKPOINT_PATH = REPO_DIR / "checkpoint/motionagformer-xs-h36m.pth.tr"


def coreml_safe_attention_forward(self, x):
    """Rank<=5 replacement for ``Attention.forward`` (spatial/temporal).

    Mathematically identical to the stock implementation but never materialises
    a rank-6 tensor, so Core ML conversion accepts it.
    """
    B, T, J, C = x.shape
    num_heads = self.num_heads
    head_dim = C // num_heads

    if self.mode == "spatial":
        # Spatial attention is independent across (B, T): fold them together.
        tokens = x.reshape(B * T, J, C)
        qkv = self.qkv(tokens).reshape(B * T, J, 3, num_heads, head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)  # (3, B*T, H, J, head_dim) -> rank 5
        q, k, v = qkv[0], qkv[1], qkv[2]
        attn = (q @ k.transpose(-2, -1)) * self.scale  # (B*T, H, J, J)
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)
        out = attn @ v  # (B*T, H, J, head_dim)
        out = out.permute(0, 2, 1, 3).reshape(B * T, J, num_heads * head_dim)
        out = out.reshape(B, T, J, C)
    elif self.mode == "temporal":
        # Temporal attention is independent across (B, J): fold them together.
        tokens = x.permute(0, 2, 1, 3).reshape(B * J, T, C)
        qkv = self.qkv(tokens).reshape(B * J, T, 3, num_heads, head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)  # (3, B*J, H, T, head_dim) -> rank 5
        q, k, v = qkv[0], qkv[1], qkv[2]
        attn = (q @ k.transpose(-2, -1)) * self.scale  # (B*J, H, T, T)
        attn = attn.softmax(dim=-1)
        attn = self.attn_drop(attn)
        out = attn @ v  # (B*J, H, T, head_dim)
        out = out.permute(0, 2, 1, 3).reshape(B * J, T, num_heads * head_dim)
        out = out.reshape(B, J, T, C).permute(0, 2, 1, 3)  # (B, T, J, C)
    else:
        raise NotImplementedError(self.mode)

    out = self.proj(out)
    out = self.proj_drop(out)
    return out


def apply_coreml_safe_attention(model):
    """Patch every stock ``Attention`` instance in ``model`` in place.

    Returns the number of attention modules that were patched. Only modules
    whose class name is exactly ``Attention`` (the rank-6 source) are touched;
    GCN / TCN / CTRAttention modules are left untouched.
    """
    patched = 0
    for module in model.modules():
        if type(module).__name__ == "Attention" and hasattr(module, "mode"):
            module.forward = _types.MethodType(coreml_safe_attention_forward, module)
            patched += 1
    return patched


def ensure_timm_droppath():
    try:
        from timm.models.layers import DropPath  # noqa: F401
        return
    except Exception:
        pass

    class DropPath(torch.nn.Module):
        def __init__(self, drop_prob=0.0):
            super().__init__()
            self.drop_prob = float(drop_prob)

        def forward(self, x):
            if self.drop_prob == 0.0 or not self.training:
                return x
            keep_prob = 1.0 - self.drop_prob
            shape = (x.shape[0],) + (1,) * (x.ndim - 1)
            random_tensor = keep_prob + torch.rand(shape, dtype=x.dtype, device=x.device)
            random_tensor.floor_()
            return x.div(keep_prob) * random_tensor

    timm = _types.ModuleType("timm")
    models = _types.ModuleType("timm.models")
    layers = _types.ModuleType("timm.models.layers")
    layers.DropPath = DropPath
    models.layers = layers
    timm.models = models
    sys.modules.setdefault("timm", timm)
    sys.modules.setdefault("timm.models", models)
    sys.modules.setdefault("timm.models.layers", layers)


def load_checkpoint(path):
    try:
        return torch.load(str(path), map_location="cpu", weights_only=False)
    except TypeError:
        return torch.load(str(path), map_location="cpu")


def strip_dataparallel_prefix(state):
    if not isinstance(state, dict) or not any(str(key).startswith("module.") for key in state):
        return state
    return {key[7:] if key.startswith("module.") else key: value for key, value in state.items()}


def load_xs_model():
    ensure_timm_droppath()
    if str(REPO_DIR) not in sys.path:
        sys.path.insert(0, str(REPO_DIR))
    from model.MotionAGFormer import MotionAGFormer

    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    act_layer = {"gelu": torch.nn.GELU, "relu": torch.nn.ReLU}[cfg["act_layer"]]
    model = MotionAGFormer(
        n_layers=cfg["n_layers"],
        dim_in=cfg["dim_in"],
        dim_feat=cfg["dim_feat"],
        dim_rep=cfg["dim_rep"],
        dim_out=cfg["dim_out"],
        mlp_ratio=cfg["mlp_ratio"],
        act_layer=act_layer,
        attn_drop=cfg["attn_drop"],
        drop=cfg["drop"],
        drop_path=cfg["drop_path"],
        use_layer_scale=cfg["use_layer_scale"],
        layer_scale_init_value=cfg["layer_scale_init_value"],
        use_adaptive_fusion=cfg["use_adaptive_fusion"],
        num_heads=cfg["num_heads"],
        qkv_bias=cfg["qkv_bias"],
        qkv_scale=cfg["qkv_scale"],
        hierarchical=cfg["hierarchical"],
        num_joints=cfg["num_joints"],
        use_temporal_similarity=cfg["use_temporal_similarity"],
        temporal_connection_len=cfg["temporal_connection_len"],
        use_tcn=cfg["use_tcn"],
        graph_only=cfg["graph_only"],
        neighbour_num=cfg["neighbour_num"],
        n_frames=cfg["n_frames"],
    )
    checkpoint = load_checkpoint(CHECKPOINT_PATH)
    state = checkpoint.get("model", checkpoint.get("model_pos", checkpoint.get("state_dict", checkpoint)))
    model.load_state_dict(strip_dataparallel_prefix(state), strict=True)
    return model
