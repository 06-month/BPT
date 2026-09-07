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
        "filename": "rtmpose-x_8xb256-420e_coco-256x192.py",
        "checkpoint": "rtmpose-x_coco.pth",
        "mim_config": "rtmpose-x_8xb256-420e_coco-256x192",
    },
    {
        "kind": "body8-halpe26",
        "filename": "rtmpose-x_8xb256-700e_body8-halpe26-384x288.py",
        "checkpoint": "rtmpose-x_body8-halpe26.pth",
        "mim_config": "rtmpose-x_8xb256-700e_body8-halpe26-384x288",
    },
]


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare an official RTMPose-x config/checkpoint.")
    parser.add_argument("--skip-mim-download", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    choice = find_installed_config()
    if choice is None:
        print("config_status=missing")
        candidate = CONFIG_CANDIDATES[0]
        config_output = MODEL_DIR / candidate["filename"]
    else:
        candidate, source = choice
        config_output = MODEL_DIR / candidate["filename"]
        write_config(source, config_output)
        print("config_status=found")
        print(f"config_kind={candidate['kind']}")
        print(f"config_source={source}")
        print(f"config_output={config_output}")
        if candidate["kind"] != "coco":
            print("warning=No official RTMPose-x COCO17 config was found locally; using official body8/Halpe26 config.")

    checkpoint_output = MODEL_DIR / candidate["checkpoint"]
    checkpoint = checkpoint_output if checkpoint_output.exists() else None
    if checkpoint is None and not args.skip_mim_download and choice is not None:
        checkpoint = try_mim_download(candidate)
    if checkpoint is None:
        print("checkpoint_status=missing")
        print("manual_download_required=true")
        print("Use the official MMPose model zoo / mim command:")
        print(f"  mim download mmpose --config {candidate['mim_config']} --dest {MODEL_DIR}")
        print(f"Place the matching checkpoint at: {checkpoint_output}")
    else:
        if checkpoint.resolve() != checkpoint_output.resolve():
            shutil.copy2(checkpoint, checkpoint_output)
        print("checkpoint_status=found")
        print(f"checkpoint_output={checkpoint_output}")

    print(f"expected_config={config_output}")
    print(f"expected_checkpoint={checkpoint_output}")
    return 0


def find_installed_config():
    for candidate in CONFIG_CANDIDATES:
        for root in config_search_roots():
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
        roots.extend([package_root, package_root / ".mim" / "configs"])
    roots.extend([Path(sys.prefix), ROOT])
    deduped = []
    seen = set()
    for root in roots:
        root = root.resolve()
        if root not in seen and root.exists():
            deduped.append(root)
            seen.add(root)
    return deduped


def write_config(source, target):
    try:
        from mmengine.config import Config
    except Exception:
        shutil.copy2(source, target)
        print("config_copy_mode=raw_copy")
        return
    cfg = Config.fromfile(source)
    cfg.dump(target)
    print("config_copy_mode=expanded_mmengine_config")


def try_mim_download(candidate):
    if shutil.which("mim") is None:
        print("mim_status=missing")
        return None
    command = ["mim", "download", "mmpose", "--config", candidate["mim_config"], "--dest", str(MODEL_DIR)]
    print("mim_status=available")
    print(f"mim_command={' '.join(command)}")
    before = {path.resolve() for path in MODEL_DIR.glob("*.pth")}
    completed = subprocess.run(command, cwd=str(ROOT), check=False, capture_output=True, text=True, timeout=300)
    if completed.stdout.strip():
        print("mim_stdout:")
        print(completed.stdout.strip())
    if completed.stderr.strip():
        print("mim_stderr:")
        print(completed.stderr.strip())
    print(f"mim_returncode={completed.returncode}")
    if completed.returncode != 0:
        return None
    exact = MODEL_DIR / candidate["checkpoint"]
    if exact.exists():
        return exact
    new_pths = [path for path in MODEL_DIR.glob("*.pth") if path.resolve() not in before]
    if new_pths:
        return sorted(new_pths, key=lambda path: path.stat().st_mtime, reverse=True)[0]
    matches = sorted(MODEL_DIR.glob("rtmpose-x*.pth"), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


if __name__ == "__main__":
    raise SystemExit(main())
