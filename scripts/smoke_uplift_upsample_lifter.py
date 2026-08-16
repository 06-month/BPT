import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external" / "uplift-upsample-3dhpe"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(EXTERNAL) not in sys.path:
    sys.path.insert(0, str(EXTERNAL))

from pose_feedback.body.uplift_upsample_adapter import make_stride_mask


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke-test Uplift-Upsample lifter loading.")
    parser.add_argument("--config", default="external/uplift-upsample-3dhpe/config/h36m_351.json")
    parser.add_argument("--weights", default="external/uplift-upsample-3dhpe/models/h36m_351.h5")
    return parser.parse_args()


def main():
    args = parse_args()
    config_path = Path(args.config)
    weights_path = Path(args.weights)
    print(f"tensorflow_available={tensorflow_available()}")
    print(f"config_path={config_path}")
    print(f"weights_path={weights_path}")
    if not config_path.exists():
        print("model_loaded=False")
        print(f"missing_config={config_path}")
        return 0
    config_data = json.loads(config_path.read_text(encoding="utf-8"))
    seq_len = int(config_data["SEQUENCE_LENGTH"])
    num_keypoints = int(config_data["NUM_KEYPOINTS"])
    input_shape = (1, seq_len, num_keypoints, 2)
    print(f"input_shape={input_shape}")
    print(f"stride_mask_shape={(1, seq_len)}")
    if not weights_path.exists():
        print("model_loaded=False")
        print(f"missing_weights={weights_path}")
        return 0
    try:
        import numpy as np
        import tensorflow as tf
        from common.net.uplift_upsample_transformer_config import UpliftUpsampleConfig
        from common.net.uplift_upsample_transformer_constructor import build_uplift_upsample_transformer
        from common.utils import weight_io
    except Exception as exc:
        print("model_loaded=False")
        print(f"tensorflow_import_error={type(exc).__name__}: {exc}")
        return 0

    config = UpliftUpsampleConfig(str(config_path))
    config.BATCH_SIZE = 1
    model = build_uplift_upsample_transformer(config)
    weight_io.load_weights_with_callback(model, filepath=str(weights_path), skip_mismatch=False, verbose=False)
    synthetic = np.zeros(input_shape, dtype="float32")
    mask = make_stride_mask(seq_len, config.MASK_STRIDE)[None, :]
    model_input = [synthetic, tf.convert_to_tensor(mask)] if model.has_strided_input else synthetic
    output = model(model_input, training=False)
    full_output, central_output = output
    central_np = central_output.numpy()
    print("model_loaded=True")
    print(f"output_full_shape={None if full_output is None else tuple(full_output.shape)}")
    print(f"output_central_shape={tuple(central_np.shape)}")
    print(f"output_min={float(np.min(central_np))}")
    print(f"output_max={float(np.max(central_np))}")
    print(f"first_frame_root_joint={central_np[0, int(config.ROOT_KEYTPOINT)].tolist()}")
    return 0


def tensorflow_available():
    try:
        import tensorflow  # noqa: F401
    except Exception:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
