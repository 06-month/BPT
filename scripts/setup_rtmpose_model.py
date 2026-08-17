import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "rtmpose"

CONFIG_CANDIDATES = [
    {
        "kind": "coco",
        "filename": "rtmpose-m_8xb256-420e_coco-256x192.py",
        "checkpoint": "rtmpose-m_coco.pth",
        "mim_config": "rtmpose-m_8xb256-420e_coco-256x192",
    },
    {
        "kind": "aic-coco",
        "filename": "rtmpose-m_8xb256-420e_aic-coco-256x192.py",
        "checkpoint": "rtmpose-m_aic-coco.pth",
        "mim_config": "rtmpose-m_8xb256-420e_aic-coco-256x192",
    },
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Locate or prepare RTMPose-m COCO 256x192 model files.",
    )
    parser.add_argument(
        "--skip-mim-download",
        action="store_true",
        help="Do not invoke mim download; only locate/copy installed configs.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    config_choice = find_installed_config()
    copied_config = None
    if config_choice is None:
        print("config_status=missing")
        print("No installed RTMPose-m COCO/AIC-COCO config was found under this Python environment.")
    else:
        candidate, source = config_choice
        copied_config = MODEL_DIR / candidate["filename"]
        write_config(source, copied_config)
        print(f"config_status=found")
        print(f"config_kind={candidate['kind']}")
        print(f"config_source={source}")
        print(f"config_output={copied_config}")

    exact_expected_config = MODEL_DIR / CONFIG_CANDIDATES[0]["filename"]
    exact_expected_checkpoint = MODEL_DIR / CONFIG_CANDIDATES[0]["checkpoint"]
    print(f"expected_coco_config={exact_expected_config}")
    print(f"expected_coco_checkpoint={exact_expected_checkpoint}")

    if config_choice is not None and config_choice[0]["kind"] != "coco":
        print("exact_coco_config_unavailable=true")
        print(f"using_matching_config={copied_config}")

    checkpoint = find_existing_checkpoint(config_choice)
    if checkpoint is None and not args.skip_mim_download and config_choice is not None:
        checkpoint = try_mim_download(config_choice[0])

    if checkpoint is None:
        print("checkpoint_status=missing")
        print_manual_download_instructions(config_choice)
    else:
        target = checkpoint_target_for(config_choice)
        if checkpoint.resolve() != target.resolve():
            shutil.copy2(checkpoint, target)
            checkpoint = target
        print("checkpoint_status=found")
        print(f"checkpoint_output={checkpoint}")

    print_visualize_command(config_choice, copied_config, checkpoint)
    return 0


def find_installed_config():
    roots = config_search_roots()
    for candidate in CONFIG_CANDIDATES:
        for root in roots:
            matches = sorted(root.rglob(candidate["filename"]))
            if matches:
                return candidate, matches[0]
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


def find_existing_checkpoint(config_choice):
    if config_choice is None:
        candidates = [item["checkpoint"] for item in CONFIG_CANDIDATES]
    else:
        candidates = [config_choice[0]["checkpoint"]]
    for filename in candidates:
        path = MODEL_DIR / filename
        if path.exists():
            return path
    pths = sorted(MODEL_DIR.glob("*.pth"))
    return pths[0] if pths else None


def try_mim_download(candidate):
    if shutil.which("mim") is None:
        print("mim_status=missing")
        return None
    command = [
        "mim",
        "download",
        "mmpose",
        "--config",
        candidate["mim_config"],
        "--dest",
        str(MODEL_DIR),
    ]
    print(f"mim_status=available")
    print(f"mim_command={' '.join(command)}")
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
    pths = sorted(MODEL_DIR.glob("*.pth"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pths[0] if pths else None


def checkpoint_target_for(config_choice):
    if config_choice is None:
        return MODEL_DIR / CONFIG_CANDIDATES[0]["checkpoint"]
    return MODEL_DIR / config_choice[0]["checkpoint"]


def print_manual_download_instructions(config_choice):
    if config_choice is None:
        config_name = CONFIG_CANDIDATES[0]["mim_config"]
        checkpoint_name = CONFIG_CANDIDATES[0]["checkpoint"]
    else:
        config_name = config_choice[0]["mim_config"]
        checkpoint_name = config_choice[0]["checkpoint"]
    print("manual_download_required=true")
    print("Use the official MMPose model zoo / RTMPose docs for the checkpoint matching:")
    print(f"  config: {config_name}")
    print(f"Place the downloaded checkpoint at: {MODEL_DIR / checkpoint_name}")
    print("Do not use an arbitrary checkpoint with a mismatched config.")


def print_visualize_command(config_choice, config_path, checkpoint_path):
    if config_choice is None:
        config_path = MODEL_DIR / CONFIG_CANDIDATES[0]["filename"]
        checkpoint_path = MODEL_DIR / CONFIG_CANDIDATES[0]["checkpoint"]
    else:
        if config_path is None:
            config_path = MODEL_DIR / config_choice[0]["filename"]
        if checkpoint_path is None:
            checkpoint_path = MODEL_DIR / config_choice[0]["checkpoint"]
    print("visualize_command:")
    print(
        "conda run -n bpt-ai python scripts/visualize_rtmpose_full_body.py "
        f"--pose-config {config_path} "
        f"--pose-checkpoint {checkpoint_path} "
        "--image assets/smoke/pushup.jpg "
        "--output assets/smoke/rtmpose_full_body_overlay.jpg"
    )


if __name__ == "__main__":
    raise SystemExit(main())
