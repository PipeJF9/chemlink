#!/bin/bash
#SBATCH --job-name=chemlink_batch_ligands
#SBATCH --output=logs/batch_ligands_%j.out
#SBATCH --error=logs/batch_ligands_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:30:00

set -euo pipefail

# --- Lmod ---
source /usr/share/lmod/lmod/init/bash
export MODULEPATH=/nfs/chemlink/modules:$MODULEPATH
module load chemlink/1.0

# --- Rutas ---
RUN_DIR="${RUN_DIR:-/nfs/chemlink/runs/test_run}"
PREPARED_LIGANDS_DIR="${PREPARED_LIGANDS_DIR:-${RUN_DIR}/output/prepared_ligands_pdbqt}"
BATCH_SIZE="${BATCH_SIZE:-200}"

BATCH_ROOT="${RUN_DIR}/ligand_batches"
mkdir -p logs "${BATCH_ROOT}"
rm -rf "${BATCH_ROOT:?}"/*

if [[ ! -d "${PREPARED_LIGANDS_DIR}" ]]; then
  echo "[ERROR] Ligand directory not found: ${PREPARED_LIGANDS_DIR}" >&2
  exit 1
fi

mapfile -t ligands < <(find "${PREPARED_LIGANDS_DIR}" -maxdepth 1 -type f -name "*.pdbqt" | sort)
count=${#ligands[@]}
if [[ "${count}" -eq 0 ]]; then
  echo "[ERROR] No prepared ligands found in ${PREPARED_LIGANDS_DIR}" >&2
  exit 1
fi

if [[ "${BATCH_SIZE}" -le 0 ]]; then
  echo "[ERROR] BATCH_SIZE must be > 0" >&2
  exit 1
fi

batch_idx=0
item_idx=0
for ligand in "${ligands[@]}"; do
  if (( item_idx % BATCH_SIZE == 0 )); then
    batch_dir="${BATCH_ROOT}/batch_${batch_idx}"
    mkdir -p "${batch_dir}"
    batch_idx=$((batch_idx + 1))
  fi
  ln -sf "${ligand}" "${batch_dir}/$(basename "${ligand}")"
  item_idx=$((item_idx + 1))
done

batch_count="${batch_idx}"
echo "${batch_count}" > "${BATCH_ROOT}/batch_count.txt"

echo "[$(date)] Prepared ligands: ${count}"
echo "[$(date)] Batch size: ${BATCH_SIZE}"
echo "[$(date)] Batch count: ${batch_count}"
