"""Adapter for AutoDockTools (MGLTools) commands."""

import os
import subprocess
from typing import Optional
from pathlib import Path


class AutoDockToolsAdapter:
    """Wrapper for AutoDockTools/MGLTools commands."""
    
    def __init__(self, mgltools_path: Optional[str] = None):
        """Initialize adapter.
        
        Args:
            mgltools_path: Path to MGLTools installation (auto-detected if None)
        """
        self.mgltools_path = mgltools_path or self._find_mgltools()
    
    def _find_mgltools(self) -> Optional[str]:
        """Try to find MGLTools installation automatically."""
        common_paths = [
            "/opt/mgltools",
            "/usr/local/mgltools",
            os.path.expanduser("~/mgltools"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def prepare_ligand(self, input_file: str, output_dir: str) -> str:
        """Convert ligand to PDBQT format using MGLTools.
        
        Args:
            input_file: Path to input molecule file (MOL2, PDB, etc.)
            output_dir: Directory to save PDBQT output
            
        Returns:
            Path to output PDBQT file
            
        Raises:
            RuntimeError: If MGLTools is not found or conversion fails
        """
        if not self.mgltools_path:
            raise RuntimeError("MGLTools not found. Please install or specify path.")
        
        pythonsh = os.path.join(self.mgltools_path, "bin", "pythonsh")
        prepare_script = os.path.join(
            self.mgltools_path,
            "MGLToolsPckgs",
            "AutoDockTools",
            "Utilities24",
            "prepare_ligand4.py"
        )
        
        if not os.path.exists(prepare_script):
            raise RuntimeError(f"prepare_ligand4.py not found at {prepare_script}")
        
        ligand_name = Path(input_file).stem
        output_file = os.path.join(output_dir, f"{ligand_name}.pdbqt")
        
        cmd = [
            pythonsh,
            prepare_script,
            "-l", input_file,
            "-o", output_file,
            "-A", "hydrogens",
            "-U", "nphs_lps"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return output_file
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"MGLTools ligand preparation failed: {e.stderr}"
            ) from e
    
    def prepare_receptor(self, input_file: str, output_dir: str) -> str:
        """Convert receptor to PDBQT format using MGLTools.
        
        Args:
            input_file: Path to input receptor file (PDB)
            output_dir: Directory to save PDBQT output
            
        Returns:
            Path to output PDBQT file
            
        Raises:
            RuntimeError: If MGLTools is not found or conversion fails
        """
        if not self.mgltools_path:
            raise RuntimeError("MGLTools not found. Please install or specify path.")
        
        pythonsh = os.path.join(self.mgltools_path, "bin", "pythonsh")
        prepare_script = os.path.join(
            self.mgltools_path,
            "MGLToolsPckgs",
            "AutoDockTools",
            "Utilities24",
            "prepare_receptor4.py"
        )
        
        if not os.path.exists(prepare_script):
            raise RuntimeError(f"prepare_receptor4.py not found at {prepare_script}")
        
        receptor_name = Path(input_file).stem
        output_file = os.path.join(output_dir, f"{receptor_name}.pdbqt")
        
        cmd = [
            pythonsh,
            prepare_script,
            "-r", input_file,
            "-o", output_file,
            "-A", "hydrogens",
            "-U", "nphs_lps"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return output_file
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"MGLTools receptor preparation failed: {e.stderr}"
            ) from e


# Convenience function for backward compatibility
def prepare_ligand_mgltools(input_file: str, output_dir: str) -> str:
    """Prepare ligand using MGLTools (convenience function).
    
    Args:
        input_file: Path to input molecule
        output_dir: Output directory
        
    Returns:
        Path to output PDBQT file
    """
    adapter = AutoDockToolsAdapter()
    return adapter.prepare_ligand(input_file, output_dir)
