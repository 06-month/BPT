#!/usr/bin/env bash
set -euo pipefail

docker run --rm --platform linux/amd64 \
  -v "$(pwd)":/workspace \
  bpt-uplift:tf24 \
  python scripts/run_uplift_inference_from_npz.py \
    --input-npz assets/smoke/vedio_1_uplift_input_debug.npz \
    --repo-dir external/uplift-upsample-3dhpe \
    --config external/uplift-upsample-3dhpe/config/h36m_351.json \
    --weights external/uplift-upsample-3dhpe/models/h36m_351.h5 \
    --output-npz assets/smoke/vedio_1_uplift_3d_output_debug.npz \
    --max-windows 8
