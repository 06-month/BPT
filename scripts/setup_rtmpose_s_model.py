import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "rtmpose"

CONFIG = {
    "filename": "rtmpose-s_8xb256-420e_coco-256x192.py",
    "checkpoint": "rtmpose-s_coco.pth",
    "mim_config": "rtmpose-s_8xb256-420e_coco-256x192",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Prepare RTMPose-s COCO 256x192 config/checkpoint.",
    )
    parser.add_argument(
        "--skip-mim-download",
        action="store_true",
        help="Only locate/copy installed config; do not invoke mim download.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    config_source = find_installed_config(CONFIG["filename"])
    config_output = MODEL_DIR / CONFIG["filename"]
    checkpoint_output = MODEL_DIR / CONFIG["checkpoint"]

    if config_source is None:
        print("config_status=missing")
        print("No installed RTMPose-s COCO config was found under this Python environment.")
    else:
        write_config(config_source, config_output)
        print("config_status=found")
        print(f"config_source={config_source}")
        print(f"config_output={config_output}")

    checkpoint = checkpoint_output if checkpoint_output.exists() else None
    if checkpoint is None and not args.skip_mim_download:
        checkpoint = try_mim_download()

    if checkpoint is None:
        print("checkpoint_status=missing")
        print("manual_download_required=true")
        print("Use the official MMPose model zoo / RTMPose docs for:")
        print(f"  config: {CONFIG['mim_config']}")
        print(f"Place the matching checkpoint at: {checkpoint_output}")
    else:
        if checkpoint.resolve() != checkpoint_output.resolve():
            shutil.copy2(checkpoint, checkpoint_output)
        print("checkpoint_status=found")
        print(f"checkpoint_output={checkpoint_output}")

    print(f"expected_config={config_output}")
    print(f"expected_checkpoint={checkpoint_output}")
    print("visualize_command:")
    print(
        "conda run -n bpt-ai python scripts/visualize_rtmpose_full_body.py "
        f"--pose-config {config_output} "
        f"--pose-checkpoint {checkpoint_output} "
        "--image assets/smoke/pushup.jpg "
        "--output assets/smoke/pushup_rtmpose_s_full_body_overlay.jpg "
        "--device cpu --marker-scale 0.6"
    )
    return 0


def find_installed_config(filename):
    for root in config_search_roots():
        matches = sorted(root.rglob(filename))
        if matches:
            return matches[0]
    return None


def config_search_roots():
    roots = []
    try:
        import mmpose
    except Exception as exc:
        print(f"mmpose_status=unavailable reason={exc!r}")
    else:
        package_root = Path(mmpose.__file__).resolve().parent
        roots.extend(
            [
                package_root,
                package_root / ".mim" / "configs",
                package_root.parent / "mmpose" / ".mim" / "configs",
            ],
        )
    roots.extend([Path(sys.prefix), ROOT])
    deduped = []
    seen = set()
    for root in roots:
        root = root.resolve()
        if root in seen or not root.exists():
            continue
        seen.add(root)
        deduped.append(root)
    return deduped


def write_config(source, target):
    try:
        from mmengine.config import Config
    except Exception:
        shutil.copy2(source, target)
        print("config_copy_mode=raw_copy")
        print("warning=mmengine unavailable; copied config may depend on relative _base_ files")
        return
    cfg = Config.fromfile(source)
    cfg.dump(target)
    print("config_copy_mode=expanded_mmengine_config")


def try_mim_download():
    if shutil.which("mim") is None:
        print("mim_status=missing")
        return None
    command = [
        "mim",
        "download",
        "mmpose",
        "--config",
        CONFIG["mim_config"],
        "--dest",
        str(MODEL_DIR),
    ]
    print("mim_status=available")
    print(f"mim_command={' '.join(command)}")
    before = {path.resolve() for path in MODEL_DIR.glob("*.pth")}
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception as exc:
        print(f"mim_download_status=failed reason={exc!r}")
        return None
    if completed.stdout.strip():
        print("mim_stdout:")
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print("mim_stderr:")
        print(completed.stderr.strip())
    print(f"mim_returncode={completed.returncode}")
    if completed.returncode != 0:
        return None

    exact = MODEL_DIR / CONFIG["checkpoint"]
    if exact.exists():
        return exact
    new_pths = [
        path for path in MODEL_DIR.glob("*.pth")
        if path.resolve() not in before
    ]
    if new_pths:
        return sorted(new_pths, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    s_pths = sorted(
        MODEL_DIR.glob("rtmpose-s*.pth"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return s_pths[0] if s_pths else None


if __name__ == "__main__":
    raise SystemExit(main())
