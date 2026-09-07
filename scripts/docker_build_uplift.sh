#!/usr/bin/env bash
set -euo pipefail

docker build --platform linux/amd64 -f docker/uplift/Dockerfile -t bpt-uplift:tf24 .
