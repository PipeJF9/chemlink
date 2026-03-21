#!/bin/bash
#SBATCH --job-name=chemlink_receptor_prep
#SBATCH --output=logs/receptor_prep_%A_%a.out
#SBATCH --error=logs/receptor_prep_%A_%a.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=04:00:00
#SBATCH --array=0-5

set -euo pipefail

INPUT_DIR="${INPUT_DIR:-data/input/receptors}"
OUTPUT_DIR="${OUTPUT_DIR:-data/input}"
MGLTOOLS_PATH="${MGLTOOLS_PATH:-/opt/mgltools}"
PYTHON_BIN="${PYTHON_BIN:-python}"
N_WORKERS="${N_WORKERS:-${SLURM_CPUS_PER_TASK:-1}}"

mkdir -p logs

echo "[$(date)] Host: $(hostname)"
echo "[$(date)] Array task: ${SLURM_ARRAY_TASK_ID}/${SLURM_ARRAY_TASK_COUNT}"
echo "[$(date)] Input: ${INPUT_DIR}"
echo "[$(date)] Output: ${OUTPUT_DIR}"
echo "[$(date)] Local workers: ${N_WORKERS}"

srun "${PYTHON_BIN}" pipelines/docking/steps/receptor_preparation.py \
  "${INPUT_DIR}" \
  "${OUTPUT_DIR}" \
  "${MGLTOOLS_PATH}" \
  "${N_WORKERS}"

echo "[$(date)] Task completed"
