# ChemLink Architecture

## Project Structure

```
chemlink/
├── adapters/           # External tool wrappers
│   ├── autodocktools/  # MGLTools PDBQT conversion
│   ├── autodock_gpu/   # AutoDock-GPU runner
│   └── fpocket/        # Pocket detection
│
├── pipelines/          # High-level workflows
│   └── docking/
│       ├── steps/      # Individual pipeline steps
│       │   ├── ligand_preparation.py
│       │   ├── receptor_preparation.py
│       │   ├── active_site_detection.py
│       │   ├── docking_execution.py
│       │   └── docking_analysis.py
│       └── docking_pipeline.py  # Orchestrates all steps
│
├── storage/            # File operations
│   ├── file_manager.py      # File utilities
│   ├── dataset_manager.py   # Dataset handling
│   └── nas_storage.py       # NAS integration
│
├── utils/              # Shared utilities
│   ├── logger.py            # Logging setup
│   ├── validator.py         # Input validation
│   └── molecule_processor.py # Chemical processing
│
├── workflows/          # Job orchestration
│   ├── workflow_manager.py
│   ├── pipeline_executor.py
│   └── job_orchestator.py
│
├── hpc/                # HPC integration
│   ├── slurm/
│   └── cluster/
│
└── cli/                # Command-line interface
    └── main.py
```

## Design Principles

### 1. **Separation of Concerns**
Each module has a single, clear responsibility:
- **adapters**: Wrap external tools (AutoDock, fpocket, etc.)
- **storage**: Handle file I/O operations
- **utils**: Provide reusable utilities
- **pipelines**: Orchestrate complex workflows

### 2. **Modularity**
Components are loosely coupled and can be:
- Tested independently
- Reused across different pipelines
- Replaced without affecting others

### 3. **Clean Dependencies**
```
pipelines → adapters + storage + utils
adapters → storage + utils
storage → (minimal dependencies)
utils → (minimal dependencies)
```

## Example: Ligand Preparation

### Old Monolithic Approach
```python
# Everything in one 400+ line file
class LigandPreparation:
    def prepare(self):
        # File operations mixed in
        # Chemical logic mixed in
        # Logging configured here
        # Format conversion here
        # ...400 lines later
```

### New Modular Approach

#### 1. **File Operations** (`storage/file_manager.py`)
```python
from chemlink.storage.file_manager import (
    create_folder,
    list_files_in_directory,
    split_multi_molecule_sdf
)
```

#### 2. **Chemical Processing** (`utils/molecule_processor.py`)
```python
from chemlink.utils.molecule_processor import process_ligand

# Pure chemical logic - testable in isolation
result = process_ligand(input_file, output_dir)
```

#### 3. **External Tools** (`adapters/autodocktools/`)
```python
from chemlink.adapters.autodocktools import prepare_ligand_mgltools

# Wraps MGLTools complexity
pdbqt_file = prepare_ligand_mgltools(mol2_file, output_dir)
```

#### 4. **Orchestration** (`pipelines/docking/steps/ligand_preparation.py`)
```python
class LigandPreparation:
    """Clean orchestration - delegates to specialized modules"""
    
    def prepare(self, n_workers=None):
        files = self._collect_ligand_files()  # storage
        results = process_ligand(files)        # utils
        self._write_reports(results)           # storage + logging
```

## Benefits

1. **Testability**: Each module can be tested independently
2. **Reusability**: `molecule_processor.py` can be used by other pipelines
3. **Maintainability**: Bug fixes are localized to specific modules
4. **Clarity**: Each file has a clear, focused purpose
5. **Scalability**: Easy to add new adapters or pipeline steps

## 🔧 Usage Example

```python
from chemlink.pipelines.docking.steps import LigandPreparation

# Simple, clean API
prep = LigandPreparation(input_dir, output_dir)
stats = prep.prepare(n_workers=4)

print(f"Success: {stats['successful']}")
print(f"Failed: {stats['failed']}")
```

## Adding New Components

### New Adapter
```python
# chemlink/adapters/newtool/newtool_adapter.py
class NewToolAdapter:
    def run(self, input_file):
        # Wrap external tool
        pass
```

### New Pipeline Step
```python
# chemlink/pipelines/docking/steps/new_step.py
from chemlink.storage.file_manager import create_folder
from chemlink.utils.logger import setup_logger

class NewStep:
    def execute(self):
        # Use existing utilities
        pass
```

## Philosophy

> "A module should do one thing, and do it well."

Each component in ChemLink follows this principle, making the codebase:
- Easy to understand
- Simple to test
- Pleasant to maintain
- Natural to extend
