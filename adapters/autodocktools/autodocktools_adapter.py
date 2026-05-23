"""Adapter for AutoDockTools (MGLTools) commands."""

import os
import subprocess
from typing import Optional, Tuple, Dict
from pathlib import Path


class AutoDockToolsAdapter:
    """Wrapper for AutoDockTools/MGLTools commands."""
    
    def __init__(self, mgltools_path: Optional[str] = None):
        """Initialize adapter.
        
        Args:
            mgltools_path: Path to MGLTools installation (auto-detected if None)
        """
        self.mgltools_path = mgltools_path or self._find_mgltools()

    def _pythonsh_path(self) -> str:
        if not self.mgltools_path:
            raise RuntimeError("MGLTools not found. Please install or specify path.")
        return os.path.join(self.mgltools_path, "bin", "pythonsh")

    def _utilities_script(self, script_name: str) -> str:
        if not self.mgltools_path:
            raise RuntimeError("MGLTools not found. Please install or specify path.")
        return os.path.join(
            self.mgltools_path,
            "MGLToolsPckgs",
            "AutoDockTools",
            "Utilities24",
            script_name,
        )

    def _build_env(self) -> Dict[str, str]:
        if not self.mgltools_path:
            raise RuntimeError("MGLTools not found. Please install or specify path.")

        env = os.environ.copy()
        env["MGLTOOLS_HOME"] = self.mgltools_path
        env["MGL_ROOT"] = self.mgltools_path
        env["PYTHONPATH"] = os.path.join(
            self.mgltools_path, "MGLToolsPckgs"
        ) + ":" + env.get("PYTHONPATH", "")
        env["PATH"] = os.path.join(self.mgltools_path, "bin") + ":" + env.get("PATH", "")
        env["LD_LIBRARY_PATH"] = os.path.join(
            self.mgltools_path, "lib"
        ) + ":" + env.get("LD_LIBRARY_PATH", "")
        return env

    def validate_prepare_gpf(self) -> None:
        """Validate prepare_gpf4.py dependencies."""
        pythonsh = self._pythonsh_path()
        prepare_script = self._utilities_script("prepare_gpf4.py")

        if not os.path.isfile(pythonsh):
            raise FileNotFoundError(f"MGLTools pythonsh not found: {pythonsh}")
        if not os.path.isfile(prepare_script):
            raise FileNotFoundError(f"prepare_gpf4.py not found at {prepare_script}")
    
    def _find_mgltools(self) -> Optional[str]:
        """Try to find MGLTools installation automatically."""
        # 1. Explicit env var (highest priority)
        env_path = os.environ.get("MGLTOOLS_PATH")
        if env_path and os.path.exists(env_path):
            return env_path

        # 2. Build candidate list: fixed paths + conda env locations
        candidates = [
            "/opt/mgltools",
            "/usr/local/mgltools",
            "/nfs/chemlink/miniconda/envs/mgl_legacy",
            os.path.expanduser("~/mgltools"),
        ]

        # Add mgl_legacy env under every conda base we can find
        conda_bases = [
            os.environ.get("CONDA_PREFIX", ""),
            os.path.expanduser("~/miniforge3"),
            os.path.expanduser("~/miniconda3"),
            os.path.expanduser("~/miniconda"),
            os.path.expanduser("~/anaconda3"),
            "/opt/miniforge3",
            "/opt/miniconda3",
            "/opt/miniconda",
            "/opt/conda",
        ]
        for base in conda_bases:
            if base:
                candidates.append(os.path.join(base, "envs", "mgl_legacy"))

        for path in candidates:
            if path and os.path.isfile(os.path.join(path, "bin", "pythonsh")):
                return path

        return None
    
    def prepare_ligand(
        self,
        input_file: str,
        output_dir: str,
        output_file: Optional[str] = None,
        keep_nonpolar_hydrogens: bool = True,
    ) -> str:
        """Convert ligand to PDBQT format using MGLTools.
        
        Args:
            input_file: Path to input molecule file (MOL2, PDB, etc.)
            output_dir: Directory to save PDBQT output
            output_file: Optional explicit output PDBQT path
            keep_nonpolar_hydrogens: If True, do not remove non-polar hydrogens
            
        Returns:
            Path to output PDBQT file
            
        Raises:
            RuntimeError: If MGLTools is not found or conversion fails
        """
        if not self.mgltools_path:
            raise RuntimeError("MGLTools not found. Please install or specify path.")
        
        pythonsh = self._pythonsh_path()
        prepare_script = self._utilities_script("prepare_ligand4.py")
        
        if not os.path.exists(prepare_script):
            raise RuntimeError(f"prepare_ligand4.py not found at {prepare_script}")
        
        ligand_name = Path(input_file).stem
        resolved_output_file = output_file or os.path.join(output_dir, f"{ligand_name}.pdbqt")
        
        cmd = [
            pythonsh,
            prepare_script,
            "-l", os.path.abspath(input_file),
            "-o", os.path.abspath(resolved_output_file),
            "-A", "hydrogens",
        ]

        # Historically, MGLTools scripts remove non-polar hydrogens via -U nphs_lps.
        # Keep hydrogens by default because tiny molecules (e.g. CH4) can become hydrogen-less.
        if keep_nonpolar_hydrogens:
            cmd.extend(["-U", "lps"])
        else:
            cmd.extend(["-U", "nphs_lps"])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return resolved_output_file
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
        
        pythonsh = self._pythonsh_path()
        prepare_script = self._utilities_script("prepare_receptor4.py")
        
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

    def prepare_gpf(
        self,
        receptor_file: str,
        ligand_file: str,
        output_gpf: str,
        center: Tuple[float, float, float],
        npts: Tuple[int, int, int],
        ligand_types: str = "HD,A,C,OA,NA,N,SA,S,Cl,F,Br,I,P,H",
    ) -> str:
        """Generate GPF file using prepare_gpf4.py."""
        self.validate_prepare_gpf()
        pythonsh = self._pythonsh_path()
        prepare_script = self._utilities_script("prepare_gpf4.py")

        receptor_file = os.path.abspath(receptor_file)
        ligand_file = os.path.abspath(ligand_file)
        output_gpf = os.path.abspath(output_gpf)
        center_str = f"{center[0]:.3f},{center[1]:.3f},{center[2]:.3f}"
        npts_str = f"{npts[0]},{npts[1]},{npts[2]}"

        cmd = [
            pythonsh,
            prepare_script,
            "-l",
            ligand_file,
            "-r",
            receptor_file,
            "-o",
            output_gpf,
            "-p",
            f"ligand_types={ligand_types}",
            "-p",
            f"npts={npts_str}",
            "-p",
            f"gridcenter={center_str}",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(output_gpf),
            env=self._build_env(),
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"prepare_gpf4.py failed for {Path(receptor_file).stem}: {result.stderr.strip()}"
            )

        if not os.path.isfile(output_gpf) or os.path.getsize(output_gpf) == 0:
            raise RuntimeError(f"GPF output missing or empty: {output_gpf}")

        return output_gpf


# Convenience function for backward compatibility
def prepare_ligand_mgltools(
    input_file: str,
    output_dir: str,
    output_file: Optional[str] = None,
    keep_nonpolar_hydrogens: bool = True,
) -> str:
    """Prepare ligand using MGLTools (convenience function).
    
    Args:
        input_file: Path to input molecule
        output_dir: Output directory
        output_file: Optional explicit output PDBQT path
        keep_nonpolar_hydrogens: If True, do not remove non-polar hydrogens
        
    Returns:
        Path to output PDBQT file
    """
    adapter = AutoDockToolsAdapter()
    return adapter.prepare_ligand(
        input_file,
        output_dir,
        output_file=output_file,
        keep_nonpolar_hydrogens=keep_nonpolar_hydrogens,
    )
