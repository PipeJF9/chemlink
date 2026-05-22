# ChemLink CLI Commands

This file documents all current CLI commands and options for `chemlink`.

## 1) Main Help

```bash
chemlink --help
```

Top-level commands:
- `docking` (recommended, intuitive subcommands)
- `receptor-preparation`
- `ligand-preparation`
- `active-site`
- `docking-execution`
- `docking-analysis`
- `docking-pipeline` (legacy flat command)

## 2) Recommended Commands (`docking ...`)

### 2.1 Preparation only

```bash
chemlink docking prepare [receptor_input_dir] [ligand_input_dir] [output_dir] \
  [--mgltools-path PATH] [--fpocket-path PATH] \
  [--manual-center X Y Z] [--manual-npts NX NY NZ] \
  [--receptor-workers N] [--ligand-workers N] [--active-site-workers N]
```

Alias:
- `chemlink docking prep ...`

Defaults:
- `receptor_input_dir`: `data/input/receptors`
- `ligand_input_dir`: `data/input/ligands`
- `output_dir`: `data/output`

### 2.2 Full pipeline (prepare + run + analysis)

```bash
chemlink docking full [receptor_input_dir] [ligand_input_dir] [output_dir] \
  [--mgltools-path PATH] [--fpocket-path PATH] \
  [--manual-center X Y Z] [--manual-npts NX NY NZ] \
  [--receptor-workers N] [--ligand-workers N] [--active-site-workers N] \
  [--docking-workers N] [--autogrid-executable PATH_OR_NAME] [--autodock-gpu-executable PATH]
```

Defaults:
- `receptor_input_dir`: `data/input/receptors`
- `ligand_input_dir`: `data/input/ligands`
- `output_dir`: `data/output`
- `--docking-workers`: `1`

### 2.3 Run docking only (with prepared inputs)

```bash
chemlink docking run [prepared_receptors_dir] [prepared_ligands_dir] [output_dir] \
  [--workers N] [--autogrid-executable PATH_OR_NAME] [--autodock-gpu-executable PATH]
```

Defaults:
- `prepared_receptors_dir`: `data/output/prepared_receptors_pdbqt`
- `prepared_ligands_dir`: `data/output/prepared_ligands_pdbqt`
- `output_dir`: `data/output`
- `--workers`: `1`

### 2.4 Analyze only

```bash
chemlink docking analyze output_dir
```

Alias:
- `chemlink docking analysis output_dir`

## 3) Legacy Commands (still available)

### 3.1 Receptor preparation

```bash
chemlink receptor-preparation input_dir output_dir \
  [--mgltools-path PATH] [--workers N]
```

### 3.2 Ligand preparation

```bash
chemlink ligand-preparation input_dir output_dir [--workers N]
```

### 3.3 Active site detection

```bash
chemlink active-site receptor_dir ligand_dir output_dir \
  [--mgltools-path PATH] [--fpocket-path PATH] [--workers N] \
  [--manual-center X Y Z] [--manual-npts NX NY NZ]
```

### 3.4 Docking execution

```bash
chemlink docking-execution prepared_receptors_dir prepared_ligands_dir output_dir \
  [--autogrid-executable PATH_OR_NAME] [--autodock-gpu-executable PATH] [--workers N]
```

### 3.5 Docking analysis

```bash
chemlink docking-analysis output_dir
```

### 3.6 Legacy flat pipeline

```bash
chemlink docking-pipeline [receptor_input_dir] [ligand_input_dir] [output_dir] \
  [--mgltools-path PATH] [--fpocket-path PATH] \
  [--manual-center X Y Z] [--manual-npts NX NY NZ] \
  [--receptor-workers N] [--ligand-workers N] [--active-site-workers N] \
  [--docking-workers N] [--autogrid-executable PATH_OR_NAME] [--autodock-gpu-executable PATH] \
  [--full]
```

Defaults:
- `receptor_input_dir`: `data/input/receptors`
- `ligand_input_dir`: `data/input/ligands`
- `output_dir`: `data/output`
- `--docking-workers`: `1`

## 4) Practical Examples

### Small local run with defaults

```bash
chemlink docking full
```

### Full run with manual box

```bash
chemlink docking full \
  --manual-center 20 -16 -22 \
  --manual-npts 60 60 60
```

### Full run with explicit tool paths

```bash
chemlink docking full \
  --mgltools-path /opt/mgltools \
  --autogrid-executable /usr/local/bin/autogrid4 \
  --autodock-gpu-executable /usr/local/bin/autodock-gpu
```

### Run only docking on pre-prepared data

```bash
chemlink docking run \
  data/output/prepared_receptors_pdbqt \
  data/output/prepared_ligands_pdbqt \
  data/output \
  --workers 1
```

### Analyze only

```bash
chemlink docking analyze data/output
```

## 5) Notes

- Manual mode requires both flags together:
  - `--manual-center X Y Z`
  - `--manual-npts NX NY NZ`
- For many AutoDock-GPU setups, `--docking-workers 1` is a good default.
- Use command-level help for details:

```bash
chemlink docking --help
chemlink docking full --help
chemlink docking run --help
chemlink active-site --help
```
