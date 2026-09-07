"""Export one real MotionAGFormer-XS lookahead5 input window for iPhone tests."""

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
INPUT_NPZ = ROOT / "assets/smoke/motionagformer_xs_s_test/inputs/vedio_1_motionagformer_xs_input.npz"
OUTPUT_NPY = ROOT / "assets/coreml/motionagformer_xs_test_input.npy"
OUTPUT_JSON = ROOT / "assets/coreml/motionagformer_xs_test_input.json"


def main():
    data = np.load(INPUT_NPZ, allow_pickle=True)
    window = np.asarray(data["lookahead5_windows"], dtype="float32")[:1]
    if window.shape != (1, 27, 17, 3):
        raise ValueError(f"Expected one window with shape [1, 27, 17, 3], got {window.shape}")

    OUTPUT_NPY.parent.mkdir(parents=True, exist_ok=True)
    np.save(OUTPUT_NPY, window)
    payload = {
        "source_npz": "assets/smoke/motionagformer_xs_s_test/inputs/vedio_1_motionagformer_xs_input.npz",
        "source_key": "lookahead5_windows",
        "shape": list(window.shape),
        "dtype": str(window.dtype),
        "layout": "[batch, frames, joints, channels]",
        "input_name": "input_2d_sequence",
        "data_flat": window.reshape(-1).astype(float).tolist(),
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"saved: {OUTPUT_NPY.relative_to(ROOT)}")
    print(f"saved: {OUTPUT_JSON.relative_to(ROOT)}")
    print(f"shape: {list(window.shape)}")
    print(f"dtype: {window.dtype}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
