#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-/nfs/chemlink/chemlink}"
RUN_ID="${RUN_ID:-run_$(date +%Y%m%d_%H%M%S)}"
RUN_DIR="${RUN_DIR:-/nfs/chemlink/runs/${RUN_ID}}"

INPUT_RECEPTORS_DIR="${INPUT_RECEPTORS_DIR:-/nfs/chemlink/data/input/receptors}"
INPUT_LIGANDS_DIR="${INPUT_LIGANDS_DIR:-/nfs/chemlink/data/input/ligands}"
OUTPUT_DIR="${OUTPUT_DIR:-${RUN_DIR}/output}"
LOG_DIR="${LOG_DIR:-${RUN_DIR}/logs}"

MGLTOOLS_PATH="${MGLTOOLS_PATH:-/opt/mgltools}"
FPOCKET_PATH="${FPOCKET_PATH:-/usr/bin/fpocket}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

PREP_ARRAY_RANGE="${PREP_ARRAY_RANGE:-0-5}"
RECEPTOR_WORKERS="${RECEPTOR_WORKERS:-4}"
LIGAND_WORKERS="${LIGAND_WORKERS:-8}"
ACTIVE_SITE_WORKERS="${ACTIVE_SITE_WORKERS:-4}"

BATCH_SIZE="${BATCH_SIZE:-200}"
MAX_GPU_CONCURRENCY="${MAX_GPU_CONCURRENCY:-6}"
DOCKING_WORKERS="${DOCKING_WORKERS:-1}"
AUTOGRID_EXECUTABLE="${AUTOGRID_EXECUTABLE:-/usr/local/bin/autogrid4}"
AUTODOCK_GPU_EXECUTABLE="${AUTODOCK_GPU_EXECUTABLE:-/usr/local/bin/autodock-gpu}"
CONTAINER_IMAGE="${CONTAINER_IMAGE:-}"
CONTAINER_RUNTIME="${CONTAINER_RUNTIME:-docker}"
CONTAINER_MOUNT_ROOT="${CONTAINER_MOUNT_ROOT:-/nfs/chemlink}"

mkdir -p "${RUN_DIR}" "${OUTPUT_DIR}" "${LOG_DIR}"
cd "${REPO_DIR}"

mapfile -t ligand_candidates < <(find "${INPUT_LIGANDS_DIR}" -maxdepth 1 -type f \( -name "*.sdf" -o -name "*.mol2" -o -name "*.pdb" -o -name "*.mol" -o -name "*.pdbqt" \) | sort)
ligand_count=${#ligand_candidates[@]}
if [[ "${ligand_count}" -eq 0 ]]; then
  echo "[ERROR] No ligands found in ${INPUT_LIGANDS_DIR}" >&2
  exit 1
fi
if [[ "${BATCH_SIZE}" -le 0 ]]; then
  echo "[ERROR] BATCH_SIZE must be > 0" >&2
  exit 1
fi

total_batches=$(( (ligand_count + BATCH_SIZE - 1) / BATCH_SIZE ))
array_expr="0-$((total_batches - 1))%${MAX_GPU_CONCURRENCY}"

echo "Run ID: ${RUN_ID}"
echo "Run dir: ${RUN_DIR}"
echo "Ligands detected: ${ligand_count}"
echo "Batch size: ${BATCH_SIZE}"
echo "Total docking batches: ${total_batches}"
echo "Docking array: ${array_expr}"

jid_receptor=$(INPUT_DIR="${INPUT_RECEPTORS_DIR}" \
  REPO_DIR="${REPO_DIR}" \
  OUTPUT_DIR="${OUTPUT_DIR}" \
  MGLTOOLS_PATH="${MGLTOOLS_PATH}" \
  PYTHON_BIN="${PYTHON_BIN}" \
  N_WORKERS="${RECEPTOR_WORKERS}" \
  CONTAINER_IMAGE="${CONTAINER_IMAGE}" \
  CONTAINER_RUNTIME="${CONTAINER_RUNTIME}" \
  CONTAINER_MOUNT_ROOT="${CONTAINER_MOUNT_ROOT}" \
  sbatch --parsable --array="${PREP_ARRAY_RANGE}" hpc/slurm/receptor_preparation_array.slurm)

jid_ligand=$(INPUT_DIR="${INPUT_LIGANDS_DIR}" \
  REPO_DIR="${REPO_DIR}" \
  OUTPUT_DIR="${OUTPUT_DIR}" \
  PYTHON_BIN="${PYTHON_BIN}" \
  N_WORKERS="${LIGAND_WORKERS}" \
  CONTAINER_IMAGE="${CONTAINER_IMAGE}" \
  CONTAINER_RUNTIME="${CONTAINER_RUNTIME}" \
  CONTAINER_MOUNT_ROOT="${CONTAINER_MOUNT_ROOT}" \
  sbatch --parsable --array="${PREP_ARRAY_RANGE}" hpc/slurm/ligand_preparation_array.slurm)

jid_active=$(REPO_DIR="${REPO_DIR}" \
  OUTPUT_DIR="${OUTPUT_DIR}" \
  MGLTOOLS_PATH="${MGLTOOLS_PATH}" \
  FPOCKET_PATH="${FPOCKET_PATH}" \
  ACTIVE_SITE_WORKERS="${ACTIVE_SITE_WORKERS}" \
  PYTHON_BIN="${PYTHON_BIN}" \
  CONTAINER_IMAGE="${CONTAINER_IMAGE}" \
  CONTAINER_RUNTIME="${CONTAINER_RUNTIME}" \
  CONTAINER_MOUNT_ROOT="${CONTAINER_MOUNT_ROOT}" \
  sbatch --parsable \
  --dependency="afterok:${jid_receptor}:${jid_ligand}" \
  --output="${LOG_DIR}/active_site_%j.out" \
  --error="${LOG_DIR}/active_site_%j.err" \
  hpc/slurm/active_site.slurm)

jid_batch=$(RUN_DIR="${RUN_DIR}" \
  PREPARED_LIGANDS_DIR="${OUTPUT_DIR}/prepared_ligands_pdbqt" \
  BATCH_SIZE="${BATCH_SIZE}" \
  sbatch --parsable \
  --dependency="afterok:${jid_ligand}" \
  --output="${LOG_DIR}/batch_ligands_%j.out" \
  --error="${LOG_DIR}/batch_ligands_%j.err" \
  hpc/slurm/prepare_ligand_batches.slurm)

jid_docking=$(REPO_DIR="${REPO_DIR}" \
  RUN_DIR="${RUN_DIR}" \
  PYTHON_BIN="${PYTHON_BIN}" \
  WORKERS="${DOCKING_WORKERS}" \
  PREPARED_RECEPTORS_DIR="${OUTPUT_DIR}/prepared_receptors_pdbqt" \
  AUTOGRID_EXECUTABLE="${AUTOGRID_EXECUTABLE}" \
  AUTODOCK_GPU_EXECUTABLE="${AUTODOCK_GPU_EXECUTABLE}" \
  CONTAINER_IMAGE="${CONTAINER_IMAGE}" \
  CONTAINER_RUNTIME="${CONTAINER_RUNTIME}" \
  CONTAINER_MOUNT_ROOT="${CONTAINER_MOUNT_ROOT}" \
  sbatch --parsable \
  --dependency="afterok:${jid_active}:${jid_batch}" \
  --array="${array_expr}" \
  --output="${LOG_DIR}/docking_%A_%a.out" \
  --error="${LOG_DIR}/docking_%A_%a.err" \
  hpc/slurm/docking_array.slurm)

jid_merge=$(RUN_DIR="${RUN_DIR}" \
  sbatch --parsable \
  --dependency="afterok:${jid_docking}" \
  --output="${LOG_DIR}/merge_%j.out" \
  --error="${LOG_DIR}/merge_%j.err" \
  hpc/slurm/merge_docking_results.slurm)

jid_analysis=$(REPO_DIR="${REPO_DIR}" \
  ANALYSIS_OUTPUT_DIR="${RUN_DIR}/merged_output" \
  PYTHON_BIN="${PYTHON_BIN}" \
  CONTAINER_IMAGE="${CONTAINER_IMAGE}" \
  CONTAINER_RUNTIME="${CONTAINER_RUNTIME}" \
  CONTAINER_MOUNT_ROOT="${CONTAINER_MOUNT_ROOT}" \
  sbatch --parsable \
  --dependency="afterok:${jid_merge}" \
  --output="${LOG_DIR}/analysis_%j.out" \
  --error="${LOG_DIR}/analysis_%j.err" \
  hpc/slurm/analysis.slurm)

echo
echo "Submitted jobs:"
echo "  receptor prep : ${jid_receptor}"
echo "  ligand prep   : ${jid_ligand}"
echo "  active site   : ${jid_active}"
echo "  make batches  : ${jid_batch}"
echo "  docking array : ${jid_docking}"
echo "  merge results : ${jid_merge}"
echo "  analysis      : ${jid_analysis}"
echo
echo "Monitor with: squeue -u $USER"
echo "Logs in: ${LOG_DIR}"
