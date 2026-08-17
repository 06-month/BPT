"""Standalone MediaPipe Tasks HandLandmarker VIDEO-mode diagnostic.

This script intentionally does NOT import RTMPose, MotionAGFormer, the project
visualization code, or the OpenCV video writer. It isolates whether MediaPipe
Tasks VIDEO mode works at all on this machine, independent of the pipeline.

It exercises, in order:
  1. construct HandLandmarker in IMAGE mode
  2. construct HandLandmarker in VIDEO mode
  3. one VIDEO-mode detect_for_video call with timestamp 0
  4. two VIDEO-mode detect_for_video calls on the same runner (ts 0 then 33)
  5. construct two VIDEO-mode HandLandmarker instances sequentially
  6. construct two VIDEO-mode instances simultaneously and run one call on each

For every step it prints PASS / FAIL with the exact exception repr and a short
stack trace on failure. CPU delegate is forced and MEDIAPIPE_DISABLE_GPU=1 is
set before importing mediapipe, matching the project runner.
"""

import argparse
import os
import traceback
from pathlib import Path

os.environ.setdefault("MEDIAPIPE_DISABLE_GPU", "1")
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bpt_mpl_cache")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TASK = ROOT / "assets/mediapipe/hand_landmarker.task"


def _delegate(python, name):
    table = {
        "cpu": getattr(python.BaseOptions.Delegate, "CPU", None),
        "gpu": getattr(python.BaseOptions.Delegate, "GPU", None),
    }
    return table.get(name)


def _make_options(python, vision, task_path, running_mode, delegate_name):
    delegate = _delegate(python, delegate_name)
    base_kwargs = {"model_asset_path": str(task_path)}
    if delegate is not None:
        base_kwargs["delegate"] = delegate
    mode = vision.RunningMode.VIDEO if running_mode == "video" else vision.RunningMode.IMAGE
    return vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(**base_kwargs),
        running_mode=mode,
        num_hands=1,
        min_hand_detection_confidence=0.3,
        min_hand_presence_confidence=0.3,
        min_tracking_confidence=0.3,
    )


def _dummy_mp_image(mp, size=256):
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    # A faint gradient so the image is not perfectly flat.
    rgb[:, :, 0] = np.linspace(0, 64, size, dtype=np.uint8)[None, :]
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


def _report(results, name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}"
    if detail:
        line += f" :: {detail}"
    print(line)
    results.append({"name": name, "ok": bool(ok), "detail": detail})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", default=str(DEFAULT_TASK))
    parser.add_argument("--delegate", choices=("cpu", "gpu"), default="cpu")
    args = parser.parse_args()

    task_path = Path(args.task)
    results = []
    print(f"task: {task_path}")
    print(f"task_exists: {task_path.exists()}")
    print(f"MEDIAPIPE_DISABLE_GPU={os.environ.get('MEDIAPIPE_DISABLE_GPU')}")
    print(f"requested delegate: {args.delegate}")

    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
    except Exception as exc:  # pragma: no cover - import failure path
        print(f"[FAIL] import_mediapipe :: {exc!r}")
        traceback.print_exc()
        return 1
    print(f"mediapipe version: {mp.__version__}")
    print(f"Delegate.CPU available: {hasattr(python.BaseOptions.Delegate, 'CPU')}")
    print(f"Delegate.GPU available: {hasattr(python.BaseOptions.Delegate, 'GPU')}")

    if not task_path.exists():
        print("[FAIL] task_model_missing :: cannot continue without .task file")
        return 1

    # Step 1: IMAGE-mode construction
    image_landmarker = None
    try:
        opts = _make_options(python, vision, task_path, "image", args.delegate)
        image_landmarker = vision.HandLandmarker.create_from_options(opts)
        _report(results, "construct_image_mode", True)
    except Exception as exc:
        _report(results, "construct_image_mode", False, repr(exc))
        traceback.print_exc()

    if image_landmarker is not None:
        try:
            image_landmarker.detect(_dummy_mp_image(mp))
            _report(results, "image_mode_detect", True)
        except Exception as exc:
            _report(results, "image_mode_detect", False, repr(exc))
            traceback.print_exc()
        finally:
            image_landmarker.close()

    # Step 2: VIDEO-mode construction
    video_landmarker = None
    try:
        opts = _make_options(python, vision, task_path, "video", args.delegate)
        video_landmarker = vision.HandLandmarker.create_from_options(opts)
        _report(results, "construct_video_mode", True)
    except Exception as exc:
        _report(results, "construct_video_mode", False, repr(exc))
        traceback.print_exc()

    # Step 3 & 4: one then two detect_for_video calls on the same runner
    if video_landmarker is not None:
        try:
            video_landmarker.detect_for_video(_dummy_mp_image(mp), 0)
            _report(results, "video_detect_for_video_ts0", True)
        except Exception as exc:
            _report(results, "video_detect_for_video_ts0", False, repr(exc))
            traceback.print_exc()
        try:
            video_landmarker.detect_for_video(_dummy_mp_image(mp), 33)
            _report(results, "video_detect_for_video_ts0_then_ts33", True)
        except Exception as exc:
            _report(results, "video_detect_for_video_ts0_then_ts33", False, repr(exc))
            traceback.print_exc()
        finally:
            video_landmarker.close()

    # Step 5: two VIDEO-mode instances constructed sequentially
    try:
        opts_a = _make_options(python, vision, task_path, "video", args.delegate)
        first = vision.HandLandmarker.create_from_options(opts_a)
        first.close()
        opts_b = _make_options(python, vision, task_path, "video", args.delegate)
        second = vision.HandLandmarker.create_from_options(opts_b)
        second.close()
        _report(results, "two_video_instances_sequential", True)
    except Exception as exc:
        _report(results, "two_video_instances_sequential", False, repr(exc))
        traceback.print_exc()

    # Step 6: two VIDEO-mode instances alive simultaneously, one call on each
    left = None
    right = None
    try:
        left = vision.HandLandmarker.create_from_options(
            _make_options(python, vision, task_path, "video", args.delegate),
        )
        right = vision.HandLandmarker.create_from_options(
            _make_options(python, vision, task_path, "video", args.delegate),
        )
        left.detect_for_video(_dummy_mp_image(mp), 0)
        right.detect_for_video(_dummy_mp_image(mp), 0)
        # advance each independent stream
        left.detect_for_video(_dummy_mp_image(mp), 33)
        right.detect_for_video(_dummy_mp_image(mp), 33)
        _report(results, "two_video_instances_simultaneous_each_call", True)
    except Exception as exc:
        _report(results, "two_video_instances_simultaneous_each_call", False, repr(exc))
        traceback.print_exc()
    finally:
        for runner in (left, right):
            if runner is not None:
                runner.close()

    passed = sum(1 for r in results if r["ok"])
    print(f"\nSUMMARY: {passed}/{len(results)} checks passed")
    for r in results:
        print(f"  {'PASS' if r['ok'] else 'FAIL'}  {r['name']}")
    return 0 if passed == len(results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
