#!/usr/bin/env bash
# Asset-independent CrowdNav route; no network, GPU or MetaUrban installation.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_ROOT="${1:?Usage: bash scripts/setup_crowd_offline.sh /absolute/path/to/mac_artifacts}"
python3 "$PROJECT_ROOT/scripts/verify_artifacts.py" "$ARTIFACT_ROOT"
test -d "$PROJECT_ROOT/third_party/CrowdNav/crowd_sim"
test -f "$PROJECT_ROOT/cache/fallback_wheels/pyrvo2-0.0.0-cp311-cp311-linux_x86_64.whl"
mkdir -p "$PROJECT_ROOT/envs" "$PROJECT_ROOT/cache/pip"
if [ ! -x "$PROJECT_ROOT/envs/python311/bin/python3" ]; then
  mkdir "$PROJECT_ROOT/envs/python311"
  tar -xzf "$ARTIFACT_ROOT/downloads/cpython-3.11.14-linux-x86_64.tar.gz" --strip-components=1 -C "$PROJECT_ROOT/envs/python311"
fi
PY="$PROJECT_ROOT/envs/python311/bin/python3"
export PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_CACHE_DIR="$PROJECT_ROOT/cache/pip"
"$PY" -m pip install --no-index --find-links "$ARTIFACT_ROOT/wheelhouse" -r "$PROJECT_ROOT/requirements/crowd-linux-py311.txt"
"$PY" -m pip install --no-index --no-deps "$PROJECT_ROOT/cache/fallback_wheels/pyrvo2-0.0.0-cp311-cp311-linux_x86_64.whl"
"$PY" -m pip check
PYTHONPATH="$PROJECT_ROOT/src" "$PY" -c 'from urban_service.crowd_experiment import load_backend; load_backend(); print("CROWDNAV_OFFLINE_READY")'
