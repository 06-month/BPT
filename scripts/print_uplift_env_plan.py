def main():
    print("Recommended Uplift-Upsample TensorFlow environment plan")
    print("")
    print("Warnings:")
    print("- Do not install TensorFlow 2.4.3 into bpt-ai.")
    print("- bpt-ai contains working RTMPose/MMPose/MMCV dependencies.")
    print("")
    print("Option A: local conda environment, if compatible")
    print("conda create -n bpt-uplift python=3.8 -y")
    print("conda activate bpt-uplift")
    print("python -m pip install --upgrade pip setuptools wheel")
    print(
        "python -m pip install tensorflow==2.4.3 "
        "tensorflow-addons==0.13.0 protobuf==3.20.1 einops==0.3.2 numpy"
    )
    print("")
    print("Option B: Linux/Docker/server fallback")
    print("- Recommended if TensorFlow 2.4.3 is unavailable on Apple Silicon/macOS.")
    print("- Use Linux x86_64 Python 3.8.")
    print("- Install the same repo requirements there:")
    print("  python -m pip install -r external/uplift-upsample-3dhpe/requirements.txt")
    print("- Copy these files/directories:")
    print("  external/uplift-upsample-3dhpe/")
    print("  assets/smoke/vedio_1_uplift_input_debug.npz")
    print("")
    print("After setup, run:")
    print(
        "python scripts/run_uplift_inference_from_npz.py "
        "--input-npz assets/smoke/vedio_1_uplift_input_debug.npz "
        "--repo-dir external/uplift-upsample-3dhpe "
        "--config external/uplift-upsample-3dhpe/config/h36m_351.json "
        "--weights external/uplift-upsample-3dhpe/models/h36m_351.h5"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
