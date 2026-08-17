import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL = ROOT / "external" / "uplift-upsample-3dhpe"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(EXTERNAL) not in sys.path:
    sys.path.insert(0, str(EXTERNAL))

from pose_feedback.body.uplift_upsample_adapter import make_stride_mask
from pose_feedback.geometry.angles_3d import elbow_flexion_3d, knee_flexion_3d


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke RTMPose JSONL through Uplift-Upsample 3D lifter.")
    parser.add_argument("--input-jsonl", default="assets/smoke/vedio_1_rtmpose_2d_keypoints.jsonl")
    parser.add_argument("--input-npz", default="assets/smoke/vedio_1_uplift_input_debug.npz")
    parser.add_argument("--config", default="external/uplift-upsample-3dhpe/config/h36m_351.json")
    parser.add_argument("--weights", default="external/uplift-upsample-3dhpe/models/h36m_351.h5")
    parser.add_argument("--max-windows", type=int, default=2)
    return parser.parse_args()


def main():
    args = parse_args()
    if not Path(args.input_jsonl).exists():
        print("rtmpose_jsonl_missing=true")
        run_script(["scripts/export_rtmpose_2d_sequence.py", "--output-jsonl", args.input_jsonl])
    if not Path(args.input_npz).exists():
        print("uplift_npz_missing=true")
        run_script(["scripts/prepare_uplift_input_from_rtmpose_jsonl.py", "--input-jsonl", args.input_jsonl, "--output-npz", args.input_npz])
    if not Path(args.input_npz).exists():
        print({"inference_ran": False, "reason": "missing NPZ input"})
        return 0
    missing = []
    if not Path(args.config).exists():
        missing.append("config")
    if not Path(args.weights).exists():
        missing.append("weights")
    if missing:
        print(
            {
                "inference_ran": False,
                "reason": "missing " + " and ".join(missing),
                "config": args.config,
                "weights": args.weights,
            },
        )
        return 0
    try:
        import tensorflow as tf
        from common.net.uplift_upsample_transformer_config import UpliftUpsampleConfig
        from common.net.uplift_upsample_transformer_constructor import build_uplift_upsample_transformer
        from common.utils import weight_io
    except Exception as exc:
        print({"inference_ran": False, "reason": f"tensorflow unavailable: {type(exc).__name__}: {exc}"})
        return 0

    data = np.load(args.input_npz)
    windows = data["normalized_windows"][: args.max_windows].astype("float32")
    config = UpliftUpsampleConfig(args.config)
    config.BATCH_SIZE = max(1, int(windows.shape[0]))
    model = build_uplift_upsample_transformer(config)
    weight_io.load_weights_with_callback(model, filepath=args.weights, skip_mismatch=False, verbose=False)
    stride_mask = make_stride_mask(config.SEQUENCE_LENGTH, config.MASK_STRIDE)
    masks = np.tile(stride_mask[None, :], (windows.shape[0], 1))
    model_input = [windows, tf.convert_to_tensor(masks)] if model.has_strided_input else windows
    full_output, central_output = model(model_input, training=False)
    central = central_output.numpy()
    sample = central[0]
    print(
        {
            "inference_ran": True,
            "input_shape": tuple(windows.shape),
            "output_full_shape": None if full_output is None else tuple(full_output.shape),
            "output_shape": tuple(central.shape),
            "output_min": float(np.min(central)),
            "output_max": float(np.max(central)),
            "joint_order": "Uplift H36M17 custom: rank,rknee,rhip,lhip,lknee,lank,pelv,neck,torso,head,htop,rwri,relb,rsho,lsho,lelb,lwri",
            "right_elbow_angle_sample": elbow_flexion_3d(sample[13], sample[12], sample[11]),
            "left_elbow_angle_sample": elbow_flexion_3d(sample[14], sample[15], sample[16]),
            "right_knee_angle_sample": knee_flexion_3d(sample[2], sample[1], sample[0]),
            "left_knee_angle_sample": knee_flexion_3d(sample[3], sample[4], sample[5]),
        },
    )
    return 0


def run_script(args):
    subprocess.run([sys.executable] + args, cwd=str(ROOT), check=False)


if __name__ == "__main__":
    raise SystemExit(main())
