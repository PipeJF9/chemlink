#!/bin/bash
#SBATCH --job-name=chemlink_active_site
#SBATCH --output=logs/active_site_%j.out
#SBATCH --error=logs/active_site_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=04:00:00

set -euo pipefail

# --- Lmod ---
source /usr/share/lmod/lmod/init/bash
export MODULEPATH=/nfs/chemlink/modules:$MODULEPATH
module load chemlink/1.0

# --- Rutas ---
REPO_DIR="${REPO_DIR:-/nfs/chemlink/chemlink}"
OUTPUT_DIR="${OUTPUT_DIR:-/nfs/chemlink/runs/test_run/output}"
MGLTOOLS_PATH="${MGLTOOLS_PATH:-/nfs/chemlink/miniconda/envs/mgl_legacy}"
FPOCKET_PATH="${FPOCKET_PATH:-/nfs/chemlink/software/fpocket-4.2.3/bin/fpocket}"
ACTIVE_SITE_WORKERS="${ACTIVE_SITE_WORKERS:-${SLURM_CPUS_PER_TASK:-1}}"
PYTHON_BIN="${PYTHON_BIN:-/nfs/chemlink/miniconda/envs/bio/bin/python}"

mkdir -p logs

RECEPTOR_DIR="${OUTPUT_DIR}/prepared_receptors_pdbqt"
LIGAND_DIR="${OUTPUT_DIR}/prepared_ligands_pdbqt"

cd "${REPO_DIR}"
export PYTHONPATH="/nfs/chemlink:${PYTHONPATH:-}"

"${PYTHON_BIN}" -m chemlink.cli.main active-site \
  "${RECEPTOR_DIR}" \
  "${LIGAND_DIR}" \
  "${OUTPUT_DIR}" \
  --mgltools-path "${MGLTOOLS_PATH}" \
  --fpocket-path "${FPOCKET_PATH}" \
  --workers "${ACTIVE_SITE_WORKERS}"

echo "[$(date)] Active-site completed"
