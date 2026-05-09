#!/bin/bash
#SBATCH --job-name=chemlink_analysis
#SBATCH --output=logs/analysis_%j.out
#SBATCH --error=logs/analysis_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=01:00:00

set -euo pipefail

REPO_DIR="${REPO_DIR:-/nfs/chemlink/chemlink}"
ANALYSIS_OUTPUT_DIR="${ANALYSIS_OUTPUT_DIR:-/nfs/chemlink/runs/test_run/merged_output}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
CONTAINER_IMAGE="${CONTAINER_IMAGE:-}"
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"
CONTAINER_MOUNT_ROOT="${CONTAINER_MOUNT_ROOT:-/nfs/chemlink}"

mkdir -p logs
cd "${REPO_DIR}"

if [[ -n "${CONTAINER_IMAGE}" ]]; then
  if [[ "${CONTAINER_RUNTIME}" == "apptainer" || "${CONTAINER_RUNTIME}" == "singularity" ]]; then
    "${CONTAINER_RUNTIME}" exec \
      --bind "${CONTAINER_MOUNT_ROOT}:${CONTAINER_MOUNT_ROOT}" \
      "${CONTAINER_IMAGE}" \
      "${PYTHON_BIN}" cli/main.py docking analyze "${ANALYSIS_OUTPUT_DIR}"
  else
    "${CONTAINER_RUNTIME}" run --rm \
      --user "$(id -u):$(id -g)" \
      -v "${CONTAINER_MOUNT_ROOT}:${CONTAINER_MOUNT_ROOT}" \
      -w "${REPO_DIR}" \
      "${CONTAINER_IMAGE}" \
      "${PYTHON_BIN}" cli/main.py docking analyze "${ANALYSIS_OUTPUT_DIR}"
  fi
else
  "${PYTHON_BIN}" cli/main.py docking analyze "${ANALYSIS_OUTPUT_DIR}"
fi

echo "[$(date)] Analysis completed"
