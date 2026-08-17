"""Trace MotionAGFormer-XS module input/output tensor shapes.

Runs one forward pass of the XS model on a fixed ``torch.zeros(1, 27, 17, 3)``
input and records, via forward hooks, the input/output tensor shapes of every
submodule. Any tensor with rank > 5 is flagged, because Core ML rejects rank-6
tensors (this is what blocks ``op_87`` during conversion).

It then applies the export-only ``coreml_safe`` attention patch and traces the
shapes again, to confirm the patched model no longer produces any rank > 5
tensor while keeping the same output shape.

Output: assets/coreml/motionagformer_xs_shape_trace.txt

This script does NOT require Core ML, GPU, or internet. It only needs the
``bpt-ai`` PyTorch environment.
"""

import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from motionagformer_coreml_safe import apply_coreml_safe_attention, load_xs_model  # noqa: E402

OUTPUT_PATH = ROOT / "assets/coreml/motionagformer_xs_shape_trace.txt"
FIXED_INPUT_SHAPE = (1, 27, 17, 3)


def _tensor_shapes(obj):
    shapes = []
    if isinstance(obj, torch.Tensor):
        shapes.append(tuple(obj.shape))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            shapes.extend(_tensor_shapes(item))
    return shapes


def trace_shapes(model, x):
    """Return (records, max_rank). records: list of dicts per module call."""
    records = []
    handles = []

    def make_hook(name, cls_name):
        def hook(module, inputs, output):
            in_shapes = _tensor_shapes(inputs)
            out_shapes = _tensor_shapes(output)
            ranks = [len(s) for s in in_shapes + out_shapes]
            records.append({
                "module": name,
                "type": cls_name,
                "input_shapes": in_shapes,
                "output_shapes": out_shapes,
                "max_rank": max(ranks) if ranks else 0,
            })
        return hook

    for name, module in model.named_modules():
        if name == "":
            continue
        handles.append(module.register_forward_hook(make_hook(name, type(module).__name__)))

    with torch.no_grad():
        out = model(x)

    for h in handles:
        h.remove()

    max_rank = max((r["max_rank"] for r in records), default=0)
    return records, max_rank, tuple(out.shape)


def _format_section(title, records, max_rank, out_shape):
    lines = [f"=== {title} ===", f"output shape: {list(out_shape)}", f"max tensor rank across all modules: {max_rank}"]
    over = [r for r in records if r["max_rank"] > 5]
    lines.append(f"modules producing rank > 5 tensors: {len(over)}")
    for r in over:
        lines.append(
            f"  RANK>{5} {r['module']} ({r['type']}) "
            f"inputs={[list(s) for s in r['input_shapes']]} "
            f"outputs={[list(s) for s in r['output_shapes']]}"
        )
    lines.append("attention-module shapes (first occurrences):")
    seen = set()
    for r in records:
        if r["type"] in ("Attention", "CTRAttention") and r["type"] not in seen:
            seen.add(r["type"])
            lines.append(
                f"  {r['module']} ({r['type']}) "
                f"inputs={[list(s) for s in r['input_shapes']]} "
                f"outputs={[list(s) for s in r['output_shapes']]} "
                f"max_rank={r['max_rank']}"
            )
    return "\n".join(lines)


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    x = torch.zeros(*FIXED_INPUT_SHAPE, dtype=torch.float32)

    # --- original model ---
    model = load_xs_model().eval()
    orig_records, orig_max_rank, orig_out = trace_shapes(model, x)
    original_section = _format_section("ORIGINAL MODEL", orig_records, orig_max_rank, orig_out)

    # --- coreml_safe patched model ---
    model2 = load_xs_model().eval()
    n_patched = apply_coreml_safe_attention(model2)
    safe_records, safe_max_rank, safe_out = trace_shapes(model2, x)
    safe_section = _format_section("COREML_SAFE MODEL", safe_records, safe_max_rank, safe_out)

    # --- numerical equivalence of original vs patched (PyTorch only) ---
    with torch.no_grad():
        ref = model(x)
        alt = model2(x)
    diff = (ref - alt).abs()

    header = [
        "MotionAGFormer-XS shape trace",
        f"fixed input shape: {list(FIXED_INPUT_SHAPE)}",
        f"coreml_safe attention modules patched: {n_patched}",
        f"original max tensor rank: {orig_max_rank}",
        f"coreml_safe max tensor rank: {safe_max_rank}",
        f"original vs coreml_safe max_abs_diff (PyTorch): {float(diff.max()):.3e}",
        f"original vs coreml_safe mean_abs_diff (PyTorch): {float(diff.mean()):.3e}",
        "",
    ]
    text = "\n".join(header) + original_section + "\n\n" + safe_section + "\n"
    OUTPUT_PATH.write_text(text, encoding="utf-8")
    print(text)
    print(f"saved: {OUTPUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
