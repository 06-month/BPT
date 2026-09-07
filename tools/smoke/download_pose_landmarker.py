"""Download the official MediaPipe Pose Landmarker (lite) .task model.

This is a small helper for the qualitative MediaPipe Pose VIDEO-mode smoke
test (`tools/smoke/mediapipe_pose_video_smoke.py`). It only fetches the
official Google AI Edge model asset and writes it to:

    assets/mediapipe/pose_landmarker_lite.task

If the download fails (no network, URL changed, etc.) it prints clear manual
download instructions and exits non-zero instead of leaving a corrupt file.
"""

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "assets/mediapipe"

# Official MediaPipe / Google AI Edge Pose Landmarker model assets.
# Source: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
_BASE = "https://storage.googleapis.com/mediapipe-models/pose_landmarker"
VARIANTS = {
    "lite": f"{_BASE}/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
    "full": f"{_BASE}/pose_landmarker_full/float16/latest/pose_landmarker_full.task",
    "heavy": f"{_BASE}/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
}
DEFAULT_OUT = ASSET_DIR / "pose_landmarker_lite.task"


def _manual_instructions(out_path, url):
    return f"""
Could not download the Pose Landmarker model automatically.

Manual download:
  1. Download {out_path.name} from the official MediaPipe Pose
     Landmarker model page:
       https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker#models
     (direct asset URL: {url})
  2. Place it at:
       {out_path}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variant",
        choices=sorted(VARIANTS),
        default="lite",
        help="model variant: lite (fastest), full, or heavy (most accurate)",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="override model asset URL (defaults to the --variant URL)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="output .task path (defaults to assets/mediapipe/pose_landmarker_<variant>.task)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-download even if the file already exists",
    )
    args = parser.parse_args()

    args.url = args.url or VARIANTS[args.variant]
    if args.out is None:
        args.out = str(ASSET_DIR / f"pose_landmarker_{args.variant}.task")

    out_path = Path(args.out)
    if out_path.exists() and not args.force:
        print(f"Pose Landmarker model already present: {out_path}")
        print("Pass --force to re-download.")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".part")

    print(f"Downloading Pose Landmarker model:\n  {args.url}\n-> {out_path}")
    try:
        urllib.request.urlretrieve(args.url, tmp_path)  # noqa: S310
    except Exception as exc:  # noqa: BLE001 - intentionally broad for clear UX
        tmp_path.unlink(missing_ok=True)
        print(f"\nDownload failed: {exc!r}")
        print(_manual_instructions(out_path, args.url))
        return 1

    size = tmp_path.stat().st_size
    if size < 1024:
        tmp_path.unlink(missing_ok=True)
        print(f"\nDownloaded file is suspiciously small ({size} bytes).")
        print(_manual_instructions(out_path, args.url))
        return 1

    tmp_path.replace(out_path)
    print(f"Done. Wrote {size} bytes to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
