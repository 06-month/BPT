import statistics
import sys
import time
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pose_feedback.body.motionagformer_runner import MotionAGFormerRunner


CONFIG_PATH = "external/MotionAGFormer/configs/h36m/MotionAGFormer-xsmall.yaml"
CHECKPOINT_PATH = "external/MotionAGFormer/checkpoint/motionagformer-xs-h36m.pth.tr"
INPUT_NPZ = "assets/smoke/motionagformer_xs_s_test/inputs/vedio_1_motionagformer_xs_input.npz"
OUTPUT_NPZ = "assets/smoke/motionagformer_xs_s_test/outputs/vedio_1_motionagformer_xs_lookahead5.npz"
WINDOW_KEY = "lookahead5_windows"
MAX_WINDOWS = 30


def main():
    input_path = ROOT / INPUT_NPZ
    output_path = ROOT / OUTPUT_NPZ
    data = np.load(input_path, allow_pickle=True)
    if WINDOW_KEY not in data.files:
        raise KeyError(f"{WINDOW_KEY} not found in {input_path}")

    windows = np.asarray(data[WINDOW_KEY], dtype="float32")
    smoke_windows = windows[:MAX_WINDOWS]
    if smoke_windows.shape[1:] != (27, 17, 3):
        raise ValueError(f"Expected windows with shape [N, 27, 17, 3], got {smoke_windows.shape}")

    print(f"input shape: {list(smoke_windows.shape)}")
    print(f"per-window input shape: {[1, *smoke_windows.shape[1:]]}")

    load_start = time.perf_counter()
    runner = MotionAGFormerRunner(
        repo_dir=str(ROOT / "external/MotionAGFormer"),
        config_path=str(ROOT / CONFIG_PATH),
        checkpoint_path=str(ROOT / CHECKPOINT_PATH),
        device="cpu",
        window_size=27,
    )
    load_ms = elapsed_ms(load_start)
    print(f"model load status: loaded ({runner.device_name}, {load_ms:.2f} ms)")

    outputs = []
    times = []
    for window in smoke_windows:
        start = time.perf_counter()
        pred = runner.predict_3d(window)
        times.append(elapsed_ms(start))
        outputs.append(pred)

    predictions = np.asarray(outputs, dtype="float32")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        predictions=predictions,
        input_windows=smoke_windows,
        source_input_npz=str(Path(INPUT_NPZ)),
        source_key=WINDOW_KEY,
        max_windows=np.asarray([MAX_WINDOWS], dtype=np.int32),
    )

    mean_ms = statistics.mean(times)
    median_ms = statistics.median(times)
    fps = 1000.0 / mean_ms if mean_ms > 0 else 0.0

    print(f"output shape: {list(predictions.shape)}")
    print(f"per-window output shape: {[1, *predictions.shape[1:]]}")
    print(f"output min / max / mean: {predictions.min():.8f} / {predictions.max():.8f} / {predictions.mean():.8f}")
    print(f"mean ms/frame: {mean_ms:.4f}")
    print(f"median ms/frame: {median_ms:.4f}")
    print(f"FPS: {fps:.4f}")
    print(f"saved: {output_path.relative_to(ROOT)}")
    return 0


def elapsed_ms(start):
    return (time.perf_counter() - start) * 1000.0


if __name__ == "__main__":
    raise SystemExit(main())
