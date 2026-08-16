from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPLIFT_REPO = ROOT / "external" / "uplift-upsample-3dhpe"
README = UPLIFT_REPO / "README.md"
CONFIG = UPLIFT_REPO / "config" / "h36m_351.json"
WEIGHTS = UPLIFT_REPO / "models" / "h36m_351.h5"
INPUT_NPZ = ROOT / "assets" / "smoke" / "vedio_1_uplift_input_debug.npz"
DOCKER_IMAGE = "bpt-uplift:tf24"


def main():
    status = {
        "repo_exists": UPLIFT_REPO.exists(),
        "readme_exists": README.exists(),
        "config_exists": CONFIG.exists(),
        "weights_exists": WEIGHTS.exists(),
        "uplift_input_npz_exists": INPUT_NPZ.exists(),
        "tensorflow_available": tensorflow_available(),
        "docker_image_expected_name": DOCKER_IMAGE,
    }
    status["ready_for_tensorflow_inference"] = (
        status["repo_exists"]
        and status["readme_exists"]
        and status["config_exists"]
        and status["weights_exists"]
        and status["uplift_input_npz_exists"]
        and status["tensorflow_available"]
    )
    status["ready_for_docker_inference"] = (
        status["repo_exists"]
        and status["readme_exists"]
        and status["config_exists"]
        and status["weights_exists"]
        and status["uplift_input_npz_exists"]
    )
    print(status)
    if not status["weights_exists"]:
        print(f"expected_weights_path={relative_path(WEIGHTS)}")
        print(
            "instruction=place the official Uplift-Upsample pretrained "
            "h36m_351.h5 weight there."
        )
    return 0


def tensorflow_available():
    try:
        import tensorflow  # noqa: F401
    except Exception:
        return False
    return True


def relative_path(path):
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
