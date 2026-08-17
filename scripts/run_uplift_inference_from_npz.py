import argparse
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.uplift_upsample_adapter import make_stride_mask


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Uplift-Upsample TensorFlow inference from prepared NPZ windows.",
    )
    parser.add_argument("--input-npz", default="assets/smoke/vedio_1_uplift_input_debug.npz")
    parser.add_argument("--repo-dir", default="external/uplift-upsample-3dhpe")
    parser.add_argument("--config", default="external/uplift-upsample-3dhpe/config/h36m_351.json")
    parser.add_argument("--weights", default="external/uplift-upsample-3dhpe/models/h36m_351.h5")
    parser.add_argument("--output-npz", default="assets/smoke/vedio_1_uplift_3d_output_debug.npz")
    parser.add_argument("--max-windows", type=int, default=8)
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input_npz)
    repo_dir = Path(args.repo_dir)
    config_path = Path(args.config)
    weights_path = Path(args.weights)
    output_path = Path(args.output_npz)

    if not input_path.exists():
        print({"inference_ran": False, "reason": "missing input NPZ", "input_npz": str(input_path)})
        return 0

    data = np.load(input_path)
    print_npz_summary(data)

    tf, tf_error = import_tensorflow()
    if tf is None:
        print({"inference_ran": False, "reason": f"tensorflow unavailable: {tf_error}"})
        return 0
    if not repo_dir.exists():
        print({"inference_ran": False, "reason": "missing Uplift repo", "repo_dir": str(repo_dir)})
        return 0
    if not config_path.exists():
        print({"inference_ran": False, "reason": "missing config", "config": str(config_path)})
        return 0
    if not weights_path.exists():
        print({"inference_ran": False, "reason": "missing weights", "weights": str(weights_path)})
        return 0

    if str(repo_dir.resolve()) not in sys.path:
        sys.path.insert(0, str(repo_dir.resolve()))
    try:
        from common.net.uplift_upsample_transformer_config import UpliftUpsampleConfig
        from common.net.uplift_upsample_transformer_constructor import build_uplift_upsample_transformer
        from common.utils import weight_io
    except Exception as exc:
        print({"inference_ran": False, "reason": f"uplift import failed: {type(exc).__name__}: {exc}"})
        return 0

    windows = get_windows(data, args.max_windows)
    if windows is None:
        print({"inference_ran": False, "reason": "NPZ missing normalized_windows or normalized_2d"})
        return 0
    config = UpliftUpsampleConfig(str(config_path))
    config.BATCH_SIZE = max(1, int(windows.shape[0]))
    try:
        model = build_uplift_upsample_transformer(config)
        weight_io.load_weights_with_callback(
            model,
            filepath=str(weights_path),
            skip_mismatch=False,
            verbose=False,
        )
        stride_mask = make_stride_mask(config.SEQUENCE_LENGTH, config.MASK_STRIDE)
        masks = np.tile(stride_mask[None, :], (windows.shape[0], 1))
        model_input = [windows, tf.convert_to_tensor(masks)] if model.has_strided_input else windows
        full_output, central_output = model(model_input, training=False)
    except Exception as exc:
        print({"inference_ran": False, "reason": f"inference failed: {type(exc).__name__}: {exc}"})
        return 0

    central = central_output.numpy()
    full = None if full_output is None else full_output.numpy()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_path,
        pred_3d_central=central,
        pred_3d_full=full,
        input_windows=windows,
    )
    print(
        {
            "inference_ran": True,
            "input_shape": tuple(windows.shape),
            "output_shape": tuple(central.shape),
            "output_min": float(np.min(central)),
            "output_max": float(np.max(central)),
            "central_frame_output_exists": central is not None,
            "full_sequence_output_exists": full is not None,
            "output_npz": str(output_path),
        },
    )
    return 0


def print_npz_summary(data):
    shapes = {}
    for key in data.files:
        value = data[key]
        shapes[key] = tuple(value.shape)
    print({"npz_keys": list(data.files), "npz_shapes": shapes})


def import_tensorflow():
    try:
        import tensorflow as tf
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return tf, None


def get_windows(data, max_windows):
    if "normalized_windows" in data.files:
        windows = data["normalized_windows"]
    elif "normalized_2d" in data.files:
        windows = data["normalized_2d"][None, ...]
    else:
        return None
    if max_windows > 0:
        windows = windows[:max_windows]
    return windows.astype("float32")


if __name__ == "__main__":
    raise SystemExit(main())
