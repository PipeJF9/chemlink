#!/bin/bash
#SBATCH --job-name=chemlink_ligand_prep
#SBATCH --output=logs/ligand_prep_%A_%a.out
#SBATCH --error=logs/ligand_prep_%A_%a.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --array=0-5

set -euo pipefail

INPUT_DIR="${INPUT_DIR:-data/input/ligands}"
OUTPUT_DIR="${OUTPUT_DIR:-data/input}"
PYTHON_BIN="${PYTHON_BIN:-python}"
N_WORKERS="${N_WORKERS:-${SLURM_CPUS_PER_TASK:-1}}"

mkdir -p logs

echo "[$(date)] Host: $(hostname)"
echo "[$(date)] Array task: ${SLURM_ARRAY_TASK_ID}/${SLURM_ARRAY_TASK_COUNT}"
echo "[$(date)] Input: ${INPUT_DIR}"
echo "[$(date)] Output: ${OUTPUT_DIR}"
echo "[$(date)] Local workers: ${N_WORKERS}"

srun "${PYTHON_BIN}" pipelines/docking/steps/ligand_preparation.py \
  "${INPUT_DIR}" \
  "${OUTPUT_DIR}" \
  "${N_WORKERS}"

echo "[$(date)] Task completed"
