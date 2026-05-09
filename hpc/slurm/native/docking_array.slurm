#!/bin/bash
#SBATCH --job-name=chemlink_docking_array
#SBATCH --output=logs/docking_%A_%a.out
#SBATCH --error=logs/docking_%A_%a.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=24:00:00

set -euo pipefail

# --- Lmod ---
source /usr/share/lmod/lmod/init/bash
export MODULEPATH=/nfs/chemlink/modules:$MODULEPATH
module load chemlink/1.0

# --- Rutas ---
REPO_DIR="${REPO_DIR:-/nfs/chemlink/chemlink}"
RUN_DIR="${RUN_DIR:-/nfs/chemlink/runs/test_run}"
PYTHON_BIN="${PYTHON_BIN:-/nfs/chemlink/miniconda/envs/bio/bin/python}"
WORKERS="${WORKERS:-1}"
AUTOGRID_EXECUTABLE="${AUTOGRID_EXECUTABLE:-/nfs/chemlink/software/autogrid4/bin/autogrid4}"
AUTODOCK_GPU_EXECUTABLE="${AUTODOCK_GPU_EXECUTABLE:-/nfs/chemlink/software/autodock-gpu/bin/autodock-gpu}"

PREPARED_RECEPTORS_DIR="${PREPARED_RECEPTORS_DIR:-${RUN_DIR}/output/prepared_receptors_pdbqt}"
BATCH_ROOT="${RUN_DIR}/ligand_batches"
TASK_OUT_ROOT="${RUN_DIR}/docking_tasks"

BATCH_DIR="${BATCH_ROOT}/batch_${SLURM_ARRAY_TASK_ID}"
TASK_OUT_DIR="${TASK_OUT_ROOT}/task_${SLURM_ARRAY_TASK_ID}"

mkdir -p logs "${TASK_OUT_DIR}"

if [[ ! -d "${BATCH_DIR}" ]]; then
  echo "[$(date)] No batch assigned for task ${SLURM_ARRAY_TASK_ID}; skipping"
  exit 0
fi

if ! find "${BATCH_DIR}" -maxdepth 1 \( -type f -o -type l \) -name "*.pdbqt" | grep -q .; then
  echo "[$(date)] Empty batch dir ${BATCH_DIR}; skipping"
  exit 0
fi

echo "[$(date)] Host: $(hostname)"
echo "[$(date)] Task: ${SLURM_ARRAY_TASK_ID}"
echo "[$(date)] Batch: ${BATCH_DIR}"
echo "[$(date)] Receptors: ${PREPARED_RECEPTORS_DIR}"
echo "[$(date)] Output: ${TASK_OUT_DIR}"

cd "${REPO_DIR}"
export PYTHONPATH="/nfs/chemlink:${PYTHONPATH:-}"

"${PYTHON_BIN}" -m chemlink.cli.main docking run \
  "${PREPARED_RECEPTORS_DIR}" \
  "${BATCH_DIR}" \
  "${TASK_OUT_DIR}" \
  --autogrid-executable "${AUTOGRID_EXECUTABLE}" \
  --autodock-gpu-executable "${AUTODOCK_GPU_EXECUTABLE}" \
  --workers "${WORKERS}"

echo "[$(date)] Docking task ${SLURM_ARRAY_TASK_ID} completed"
