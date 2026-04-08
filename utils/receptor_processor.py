"""Receptor processing utilities for cleanup and PDBQT conversion."""

import os
import subprocess
from typing import Dict, Optional

try:
    from openbabel import openbabel as ob
except ImportError:
    import openbabel as ob

from ..storage.file_manager import create_out_file, find_compound_name
from .logger import setup_logger

logger = setup_logger(__name__)


class ReceptorProcessor:
    """Handle receptor cleanup and conversion to PDBQT."""

    PROTEIN_RESIDUES = {
        "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY",
        "HIS", "ILE", "LEU", "LYS", "MET", "PHE", "PRO", "SER",
        "THR", "TRP", "TYR", "VAL",
        "HID", "HIE", "HIP", "HSE", "HSD", "HSP",
        "CYX", "CYM",
        "ACE", "NME",
    }

    DEFAULT_MGLTOOLS_PATH = "/opt/mgltools"

    def __init__(
        self,
        mgltools_path: Optional[str] = None,
        remove_water: bool = True,
        remove_ligands: bool = True,
        remove_ions: bool = True,
        keep_clean_pdb: bool = True,
    ):
        self.mol = ob.OBMol()
        self.remove_water = remove_water
        self.remove_ligands = remove_ligands
        self.remove_ions = remove_ions
        self.keep_clean_pdb = keep_clean_pdb

        self.mgltools_path = mgltools_path or self.DEFAULT_MGLTOOLS_PATH
        self.mgltools_python = os.path.join(self.mgltools_path, "bin", "pythonsh")
        self.prepare_receptor_script = os.path.join(
            self.mgltools_path,
            "MGLToolsPckgs",
            "AutoDockTools",
            "Utilities24",
            "prepare_receptor4.py",
        )

    def _validate_mgltools(self) -> None:
        if not os.path.isfile(self.mgltools_python):
            raise FileNotFoundError(f"MGLTools Python not found: {self.mgltools_python}")
        if not os.path.isfile(self.prepare_receptor_script):
            raise FileNotFoundError(
                f"prepare_receptor4.py not found: {self.prepare_receptor_script}"
            )

    def _get_mgltools_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env["MGL_ROOT"] = self.mgltools_path
        env["PYTHONPATH"] = os.path.join(self.mgltools_path, "MGLToolsPckgs") + ":" + env.get("PYTHONPATH", "")
        env["LD_LIBRARY_PATH"] = os.path.join(self.mgltools_path, "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
        return env

    def _read_receptor(self, receptor_file: str) -> None:
        if not os.path.exists(receptor_file):
            abs_path = os.path.abspath(receptor_file)
            cwd = os.getcwd()

            error_msg = f"Receptor file not found: {receptor_file}\n"
            error_msg += f"  Absolute path attempted: {abs_path}\n"
            error_msg += f"  Current working directory: {cwd}\n"

            basename = os.path.basename(receptor_file)
            possible_paths = [
                f"data/input/receptors/{basename}",
                f"./data/input/receptors/{basename}",
                f"../data/input/receptors/{basename}",
            ]

            for possible in possible_paths:
                if os.path.exists(possible):
                    error_msg += f"  File found at: {possible}\n"
                    error_msg += "  Use this path instead!\n"
                    break

            raise RuntimeError(error_msg.strip())

        if not os.access(receptor_file, os.R_OK):
            raise RuntimeError(
                f"Cannot read receptor file (permission denied): {receptor_file}\n"
                f"  Try: chmod +r {receptor_file}"
            )

        self.mol = ob.OBMol()
        conv = ob.OBConversion()
        conv.SetInFormat("pdb")

        logger.info(f"Reading receptor: {receptor_file}")

        if not conv.ReadFile(self.mol, receptor_file):
            file_size = os.path.getsize(receptor_file)
            error_msg = f"OpenBabel failed to read receptor: {receptor_file}\n"
            error_msg += "  File exists: Yes\n"
            error_msg += f"  File size: {file_size} bytes\n"
            error_msg += f"  File readable: {os.access(receptor_file, os.R_OK)}\n"

            try:
                with open(receptor_file, "r") as handle:
                    first_line = handle.readline().strip()
                    error_msg += f"  First line: {first_line[:50]}...\n"
            except Exception as exc:
                error_msg += f"  Cannot read file content: {exc}\n"

            error_msg += "  This may indicate a corrupted or malformed PDB file"
            raise RuntimeError(error_msg.strip())

        num_atoms = self.mol.NumAtoms()
        if num_atoms == 0:
            raise RuntimeError(
                f"Read 0 atoms from {receptor_file}. File may be empty or corrupted."
            )

        logger.info(f"Successfully read {num_atoms:,} atoms from {receptor_file}")

    def _get_residue_summary(self) -> Dict[str, int]:
        residues: Dict[str, int] = {}
        for atom in ob.OBMolAtomIter(self.mol):
            res = atom.GetResidue()
            if res:
                name = res.GetName().strip().upper()
                residues[name] = residues.get(name, 0) + 1
        return residues

    def _identify_atoms_to_remove(self):
        atoms_to_remove = []
        removed_info = {"water": 0, "ligand": 0, "ion": 0, "other": 0}

        for atom in ob.OBMolAtomIter(self.mol):
            res = atom.GetResidue()

            if not res:
                atoms_to_remove.append(atom.GetIdx())
                removed_info["other"] += 1
                continue

            name = res.GetName().strip().upper()
            if name in self.PROTEIN_RESIDUES:
                continue

            if name in {"HOH", "WAT", "H2O", "DOD"}:
                if self.remove_water:
                    atoms_to_remove.append(atom.GetIdx())
                    removed_info["water"] += 1
                continue

            if name in {"NA", "CL", "MG", "CA", "ZN", "FE", "K", "MN", "CU"}:
                if self.remove_ions:
                    atoms_to_remove.append(atom.GetIdx())
                    removed_info["ion"] += 1
                continue

            if self.remove_ligands:
                atoms_to_remove.append(atom.GetIdx())
                removed_info["ligand"] += 1

        return atoms_to_remove, removed_info

    def _remove_non_protein(self) -> Dict[str, int]:
        atoms_to_remove, info = self._identify_atoms_to_remove()

        for idx in sorted(atoms_to_remove, reverse=True):
            atom = self.mol.GetAtom(idx)
            if atom:
                self.mol.DeleteAtom(atom)

        self.mol.PerceiveBondOrders()

        logger.info(
            f"Removed: {info['water']} water, {info['ligand']} ligand, "
            f"{info['ion']} ion, {info['other']} other atoms"
        )
        logger.info(f"Remaining atoms: {self.mol.NumAtoms()}")
        return info

    def _save_clean_receptor(self, output_file: str) -> None:
        conv = ob.OBConversion()
        conv.SetOutFormat("pdb")

        if not conv.WriteFile(self.mol, output_file):
            raise RuntimeError(f"Failed to write receptor: {output_file}")

    def _run_prepare_receptor(self, input_pdb: str, output_pdbqt: str) -> None:
        self._validate_mgltools()

        cmd = [
            self.mgltools_python,
            self.prepare_receptor_script,
            "-r", input_pdb,
            "-o", output_pdbqt,
            "-A", "hydrogens",
            "-U", "nphs_lps_waters_nonstdres",
        ]

        logger.info(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self._get_mgltools_env(),
                check=True,
                timeout=300,
            )
            logger.info(f"MGLTools success: {result.stdout}")
        except subprocess.CalledProcessError as exc:
            logger.error(f"MGLTools failed: {exc}\nSTDERR: {exc.stderr}")
            raise RuntimeError(
                f"prepare_receptor4.py failed with code {exc.returncode}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("MGLTools timed out after 300s")

        if not os.path.isfile(output_pdbqt) or os.path.getsize(output_pdbqt) == 0:
            raise RuntimeError(f"Output PDBQT empty or missing: {output_pdbqt}")

        logger.info(f"Generated PDBQT: {output_pdbqt}")

    def prepare_receptor(self, receptor_file: str, output_path: str) -> str:
        """Run receptor cleanup + MGLTools conversion and return output PDBQT path."""
        base = find_compound_name(receptor_file)
        safe_base = base.replace(" ", "_").replace(",", "_")

        clean_pdb = create_out_file(
            f"{output_path}/clean_receptors",
            f"{safe_base}_clean.pdb",
        )

        self._read_receptor(receptor_file)
        residues = self._get_residue_summary()
        logger.info(f"Residues found: {residues}")

        self._remove_non_protein()
        self._save_clean_receptor(clean_pdb)
        logger.info(f"Saved cleaned receptor to {clean_pdb}")

        out_pdbqt = create_out_file(
            f"{output_path}/prepared_receptors_pdbqt",
            f"{safe_base}_clean.pdbqt",
        )
        self._run_prepare_receptor(clean_pdb, out_pdbqt)

        if not self.keep_clean_pdb and os.path.exists(clean_pdb):
            os.remove(clean_pdb)
            logger.debug(f"Removed intermediate: {clean_pdb}")

        return out_pdbqt
