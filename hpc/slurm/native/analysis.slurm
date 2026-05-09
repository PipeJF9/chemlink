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

# --- Lmod ---
source /usr/share/lmod/lmod/init/bash
export MODULEPATH=/nfs/chemlink/modules:$MODULEPATH
module load chemlink/1.0

# --- Rutas ---
REPO_DIR="${REPO_DIR:-/nfs/chemlink/chemlink}"
ANALYSIS_OUTPUT_DIR="${ANALYSIS_OUTPUT_DIR:-/nfs/chemlink/runs/test_run/merged_output}"
PYTHON_BIN="${PYTHON_BIN:-/nfs/chemlink/miniconda/envs/bio/bin/python}"

mkdir -p logs
cd "${REPO_DIR}"
export PYTHONPATH="/nfs/chemlink:${PYTHONPATH:-}"

"${PYTHON_BIN}" -m chemlink.cli.main docking analyze "${ANALYSIS_OUTPUT_DIR}"

echo "[$(date)] Analysis completed"
