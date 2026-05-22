"""File management utilities for ChemLink project."""

import os
import glob
from pathlib import Path
from typing import List


def create_folder(path: str) -> None:
    """Create a folder if it doesn't exist.
    
    Args:
        path: Folder path to create
    """
    os.makedirs(path, exist_ok=True)


def find_extension(filepath: str) -> str:
    """Extract file extension from filepath.
    
    Args:
        filepath: Path to file
        
    Returns:
        File extension including the dot (e.g., '.sdf')
    """
    return Path(filepath).suffix


def find_compound_name(filepath: str) -> str:
    """Extract compound/molecule name from filepath (without extension).
    
    Args:
        filepath: Path to file
        
    Returns:
        Filename without extension
    """
    return Path(filepath).stem


def create_out_file(output_dir: str, filename: str) -> str:
    """Create output directory if needed and return full output path.
    
    Args:
        output_dir: Directory where file should be created
        filename: Name of the output file
        
    Returns:
        Full path to output file
    """
    create_folder(output_dir)
    return os.path.join(output_dir, filename)


def list_files_in_directory(directory: str, patterns: List[str]) -> List[str]:
    """List all files matching the given patterns in a directory.
    
    Args:
        directory: Directory to search in
        patterns: List of glob patterns (e.g., ['*.sdf', '*.mol2'])
        
    Returns:
        List of absolute file paths
    """
    # Convert to absolute path to handle relative paths correctly
    abs_directory = os.path.abspath(directory)
    
    if not os.path.isdir(abs_directory):
        return []
    
    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(abs_directory, pattern)))
    return sorted(files)


def verify_only_file(filepath: str) -> bool:
    """Verify if SDF file contains only one molecule.
    
    Args:
        filepath: Path to SDF file
        
    Returns:
        True if file contains only one molecule, False otherwise
    """
    if not filepath.lower().endswith('.sdf'):
        return True
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        molecule_count = content.count('$$$$')
        return molecule_count <= 1
    except Exception:
        return True


def split_multi_molecule_sdf(filepath: str, output_dir: str) -> List[str]:
    """Split multi-molecule SDF file into individual files.
    
    Args:
        filepath: Path to multi-molecule SDF file
        output_dir: Directory to save individual molecule files
        
    Returns:
        List of paths to individual molecule files
    """
    output_files = []
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        molecules = content.split('$$$$')
        molecules = [m.strip() for m in molecules if m.strip()]
        
        for i, mol in enumerate(molecules, 1):
            if not mol.endswith('\n'):
                mol += '\n'
            mol_content = mol + '$$$$\n'
            
            # Use first line as name, fallback to index
            first_line = mol.splitlines()[0].strip()
            safe_name = first_line.replace(' ', '_').replace('/', '_') or f"molecule_{i}"
            
            out_file = create_out_file(output_dir, f"mol_{safe_name}.sdf")
            
            with open(out_file, 'w') as f:
                f.write(mol_content)
            
            output_files.append(out_file)
                
        return output_files
        
    except Exception as e:
        raise RuntimeError(f"Error splitting {filepath}: {str(e)}")
