#!/usr/bin/env bash
# Linux only. No network access, no conda changes, no global package installation.
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_ROOT="${1:?Usage: bash scripts/setup_offline.sh /absolute/path/to/ucmp-week3-artifacts}"
case "$(uname -sm)" in "Linux x86_64") ;; *) echo 'ERROR: Linux x86_64 required' >&2; exit 2 ;; esac
test -f "$ARTIFACT_ROOT/downloads/cpython-3.11.14-linux-x86_64.tar.gz"
test -d "$ARTIFACT_ROOT/wheelhouse"
# Verify receipts before executing any imported binary.
python3 "$PROJECT_ROOT/scripts/verify_artifacts.py" "$ARTIFACT_ROOT"
mkdir -p "$PROJECT_ROOT/envs" "$PROJECT_ROOT/cache/pip"
if [ ! -x "$PROJECT_ROOT/envs/python311/bin/python3" ]; then
  mkdir "$PROJECT_ROOT/envs/python311"
  tar -xzf "$ARTIFACT_ROOT/downloads/cpython-3.11.14-linux-x86_64.tar.gz" --strip-components=1 -C "$PROJECT_ROOT/envs/python311"
fi
PY="$PROJECT_ROOT/envs/python311/bin/python3"
"$PY" -c 'import sys; assert sys.version_info[:3] == (3,11,14), sys.version'
export PIP_NO_INDEX=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_CACHE_DIR="$PROJECT_ROOT/cache/pip"
"$PY" -m pip install --no-index --find-links "$ARTIFACT_ROOT/wheelhouse" -r "$PROJECT_ROOT/requirements/runtime-linux-py311.txt"
"$PY" -m pip install --no-index --no-deps --no-build-isolation -e "$PROJECT_ROOT/third_party/metaurban"
"$PY" -m pip install --no-index --no-deps --no-build-isolation -e "$PROJECT_ROOT"
"$PY" -m pip check
"$PY" "$PROJECT_ROOT/scripts/prepare_orca_build.py"
cmake -S "$PROJECT_ROOT/third_party/metaurban/metaurban/orca_algo" -B "$PROJECT_ROOT/third_party/metaurban/metaurban/orca_algo/build" -DPYTHON_EXECUTABLE="$PY" -Dpybind11_DIR="$("$PY" -m pybind11 --cmakedir)" -DFULL_OUTPUT_FLAG=OFF -DFULL_LOG_FLAG=OFF -DMAPF_LOG_FLAG=OFF
cmake --build "$PROJECT_ROOT/third_party/metaurban/metaurban/orca_algo/build" --parallel 2
PYTHONPATH="$PROJECT_ROOT/third_party/metaurban/metaurban/orca_algo/build:$PROJECT_ROOT/src" "$PY" -c 'import bind, torch, stable_baselines3, panda3d; print("OFFLINE_IMPORTS_PASSED")'
echo 'OFFLINE_ENVIRONMENT_READY_SIMULATOR_GATE_PENDING'
