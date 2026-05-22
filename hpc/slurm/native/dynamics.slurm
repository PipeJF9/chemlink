#!/bin/bash
#SBATCH --job-name=cl_dynamics
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH --time=72:00:00
#SBATCH --output=/tmp/cl_dynamics_%j.out
#SBATCH --error=/tmp/cl_dynamics_%j.err

set -euo pipefail

# --- Lmod ---
source /usr/share/lmod/lmod/init/bash
export MODULEPATH=/nfs/chemlink/modules:$MODULEPATH
module load chemlink/1.0

# --- Paths ---
REPO_DIR="${REPO_DIR:-/nfs/chemlink/chemlink}"
PYTHON_BIN="${PYTHON_BIN:-/nfs/chemlink/miniconda/envs/bio/bin/python}"
DYN_CONFIG_JSON="${DYN_CONFIG_JSON:-}"
DYN_WORK_DIR="${DYN_WORK_DIR:-}"
DYN_TIME_LIMIT="${DYN_TIME_LIMIT:-72:00:00}"

if [[ -z "${DYN_CONFIG_JSON}" ]]; then
  echo "[$(date)] Error: DYN_CONFIG_JSON is not set" >&2
  exit 1
fi

if [[ ! -f "${DYN_CONFIG_JSON}" ]]; then
  echo "[$(date)] Error: config file not found: ${DYN_CONFIG_JSON}" >&2
  exit 1
fi

echo "[$(date)] Host        : $(hostname)"
echo "[$(date)] Job ID      : ${SLURM_JOB_ID:-local}"
echo "[$(date)] Config      : ${DYN_CONFIG_JSON}"
echo "[$(date)] Work dir    : ${DYN_WORK_DIR}"
echo "[$(date)] Time limit  : ${DYN_TIME_LIMIT}"
echo "[$(date)] GPU info    :"
nvidia-smi --query-gpu=name,compute_cap --format=csv,noheader 2>/dev/null || echo "  (nvidia-smi not available)"

cd "${REPO_DIR}"
export PYTHONPATH="/nfs/chemlink:${PYTHONPATH:-}"

"${PYTHON_BIN}" -m hpc.slurm.runner.dynamics_runner "${DYN_CONFIG_JSON}"

echo "[$(date)] Dynamics job ${SLURM_JOB_ID:-local} completed"

# --- Copy logs to work dir ---
if [[ -n "${DYN_WORK_DIR}" && -d "${DYN_WORK_DIR}" ]]; then
  JOB_ID="${SLURM_JOB_ID:-local}"
  [[ -f "/tmp/cl_dynamics_${JOB_ID}.out" ]] && cp "/tmp/cl_dynamics_${JOB_ID}.out" "${DYN_WORK_DIR}/slurm_${JOB_ID}.out" || true
  [[ -f "/tmp/cl_dynamics_${JOB_ID}.err" ]] && cp "/tmp/cl_dynamics_${JOB_ID}.err" "${DYN_WORK_DIR}/slurm_${JOB_ID}.err" || true
fi
