import argparse
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.motionagformer_buffer import MotionAGFormerWindowBuilder
from pose_feedback.body.motionagformer_runner import MotionAGFormerRunner


def parse_args():
    parser = argparse.ArgumentParser(description="Run optional MotionAGFormer 3D smoke inference.")
    parser.add_argument("--input-npz", default="assets/smoke/vedio_1_motionagformer_input_debug.npz")
    parser.add_argument("--repo-dir", default="external/MotionAGFormer")
    parser.add_argument("--config", default="external/MotionAGFormer/configs/h36m/MotionAGFormer-base.yaml")
    parser.add_argument(
        "--checkpoint",
        default="external/MotionAGFormer/checkpoint/motionagformer-b-h36m.pth.tr",
    )
    parser.add_argument("--mode", choices=("full", "lookahead3", "lookahead5"), default="lookahead3")
    parser.add_argument("--max-windows", type=int, default=16)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-npz", default="assets/smoke/vedio_1_motionagformer_3d_debug.npz")
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input_npz)
    if not input_path.exists():
        print({"input_exists": False, "input_npz": str(input_path)})
        return 0
    data = np.load(input_path, allow_pickle=True)
    windows_key = windows_key_for_mode(args.mode)
    frames_key = frames_key_for_mode(args.mode)
    if windows_key not in data.files:
        print({"input_npz": str(input_path), "mode": args.mode, "reason": f"missing {windows_key}"})
        return 0
    checkpoint = Path(args.checkpoint) if args.checkpoint else None
    if checkpoint is None or not checkpoint.exists():
        print(
            {
                "inference_ran": False,
                "reason": "missing_checkpoint",
                "expected_checkpoint": str(checkpoint) if checkpoint else "pass --checkpoint path",
                "instructions": (
                    "Download the official MotionAGFormer H3.6M checkpoint matching --config "
                    "from external/MotionAGFormer README and place it at the expected path."
                ),
            },
        )
        return 0

    windows = np.asarray(data[windows_key], dtype="float32")
    count = min(len(windows), args.max_windows)
    try:
        runner = MotionAGFormerRunner(
            repo_dir=args.repo_dir,
            config_path=args.config,
            checkpoint_path=str(checkpoint),
            device=args.device,
            window_size=windows.shape[1],
        )
    except (ImportError, FileNotFoundError) as exc:
        print({"inference_ran": False, "reason": f"{type(exc).__name__}: {exc}"})
        return 0

    preds = []
    for window in windows[:count]:
        preds.append(runner.predict_3d(window))
    pred_3d = np.stack(preds).astype("float32")
    frame_indices = data[frames_key][:count] if frames_key in data.files else np.arange(count)
    fps = float(np.asarray(data["fps"])[0]) if "fps" in data.files else 30.0
    builder = MotionAGFormerWindowBuilder(window_size=windows.shape[1])
    latency_frames = latency_for_mode(builder, args.mode)
    output = Path(args.output_npz)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        pred_3d=pred_3d,
        mode=np.asarray([args.mode]),
        frame_indices=frame_indices,
        latency_frames=np.asarray([latency_frames], dtype="int32"),
        latency_sec=np.asarray([latency_frames / fps], dtype="float32"),
    )
    print(
        {
            "inference_ran": True,
            "mode": args.mode,
            "input_shape": tuple(windows[:count].shape),
            "output_shape": tuple(pred_3d.shape),
            "output_npz": str(output),
            "latency_frames": latency_frames,
            "latency_sec": latency_frames / fps,
        },
    )
    return 0


def windows_key_for_mode(mode):
    return "full_centered_windows" if mode == "full" else f"{mode}_windows"


def frames_key_for_mode(mode):
    return "full_centered_frame_indices" if mode == "full" else f"{mode}_frame_indices"


def latency_for_mode(builder, mode):
    if mode == "full":
        return builder.latency_frames("full")
    return builder.latency_frames("lookahead", lookahead=int(mode.replace("lookahead", "")))


if __name__ == "__main__":
    raise SystemExit(main())
