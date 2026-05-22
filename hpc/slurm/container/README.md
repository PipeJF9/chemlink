# SLURM execution for preparation steps

This project supports receptor list sharding using SLURM array variables.
Each array task automatically processes a subset of inputs for both ligand and receptor preparation.

## 1) Submit on 6 tasks (typical for 6 PCs/nodes)

### Receptor preparation

```bash
sbatch hpc/slurm/receptor_preparation_array.slurm
```

### Ligand preparation

```bash
sbatch hpc/slurm/ligand_preparation_array.slurm
```

Both scripts use:
- `#SBATCH --array=0-5` (6 tasks)
- automatic sharding from `SLURM_ARRAY_TASK_ID` and `SLURM_ARRAY_TASK_COUNT`
- local multiprocessing via `N_WORKERS` (defaults to `SLURM_CPUS_PER_TASK`)

## 2) Override default paths

### Receptor preparation

```bash
INPUT_DIR=/path/to/receptors \
OUTPUT_DIR=/path/to/output \
MGLTOOLS_PATH=/opt/mgltools \
N_WORKERS=4 \
PYTHON_BIN=python3 \
sbatch hpc/slurm/receptor_preparation_array.slurm
```

### Ligand preparation

```bash
INPUT_DIR=/path/to/ligands \
OUTPUT_DIR=/path/to/output \
N_WORKERS=8 \
PYTHON_BIN=python3 \
sbatch hpc/slurm/ligand_preparation_array.slurm
```

## 3) Monitor

```bash
squeue -u "$USER"
sacct -j <jobid> --format=JobID,State,Elapsed,NodeList
```

Logs are written to `logs/receptor_prep_<jobid>_<arrayid>.out` and `.err`.

## Notes

- Receptor preparation is CPU/IO bound (OpenBabel + MGLTools), not GPU bound.
- Ligand preparation is CPU bound and usually benefits from higher `N_WORKERS` than receptors.
- Keep software stack consistent across nodes (Python, OpenBabel, MGLTools).
- You can test locally without SLURM by running the Python step directly.
