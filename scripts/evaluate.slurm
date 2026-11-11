#!/usr/bin/env bash
#SBATCH --job-name=ucmp-urban-nav
#SBATCH --partition=staff
#SBATCH --gres=gpu:staff:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=02:00:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
ROOT="${SLURM_SUBMIT_DIR:?Submit from week3_assignment}"
PROTOCOL="${1:?Pass the frozen evaluation JSON path}"
cd "$ROOT"
export OMP_NUM_THREADS=4
export TERM=xterm-256color
# Slurm owns CUDA_VISIBLE_DEVICES. Do not overwrite it.
"$ROOT/envs/python311/bin/python3" scripts/preflight.py --config "$PROTOCOL"
"$ROOT/envs/python311/bin/python3" scripts/evaluate.py --config "$PROTOCOL" --split test
