#!/bin/bash
#SBATCH --job-name=chemlink_merge_docking
#SBATCH --output=logs/merge_docking_%j.out
#SBATCH --error=logs/merge_docking_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=01:00:00

set -euo pipefail

RUN_DIR="${RUN_DIR:-/nfs/chemlink/runs/test_run}"
TASK_OUT_ROOT="${RUN_DIR}/docking_tasks"
MERGED_OUTPUT_DIR="${RUN_DIR}/merged_output"
BASE_OUTPUT_DIR="${RUN_DIR}/output"

mkdir -p logs
mkdir -p "${MERGED_OUTPUT_DIR}/docking_results"

if [[ -d "${BASE_OUTPUT_DIR}/prepared_receptors_pdbqt" ]]; then
  mkdir -p "${MERGED_OUTPUT_DIR}/prepared_receptors_pdbqt"
  cp -a "${BASE_OUTPUT_DIR}/prepared_receptors_pdbqt/." "${MERGED_OUTPUT_DIR}/prepared_receptors_pdbqt/"
fi

if [[ -d "${BASE_OUTPUT_DIR}/prepared_ligands_pdbqt" ]]; then
  mkdir -p "${MERGED_OUTPUT_DIR}/prepared_ligands_pdbqt"
  cp -a "${BASE_OUTPUT_DIR}/prepared_ligands_pdbqt/." "${MERGED_OUTPUT_DIR}/prepared_ligands_pdbqt/"
fi

shopt -s nullglob
for task_dir in "${TASK_OUT_ROOT}"/task_*; do
  result_dir="${task_dir}/docking_results"
  if [[ ! -d "${result_dir}" ]]; then
    continue
  fi

  for protein_dir in "${result_dir}"/*; do
    [[ -d "${protein_dir}" ]] || continue
    protein_name="$(basename "${protein_dir}")"
    target_dir="${MERGED_OUTPUT_DIR}/docking_results/${protein_name}"
    mkdir -p "${target_dir}"
    cp -a "${protein_dir}/." "${target_dir}/"
  done
done
shopt -u nullglob

echo "[$(date)] Merged docking results into ${MERGED_OUTPUT_DIR}/docking_results"
