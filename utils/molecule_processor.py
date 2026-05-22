"""Molecular processing utilities using RDKit and OpenBabel."""

import os
import traceback
from typing import Tuple, List, Optional
from rdkit import Chem
from rdkit.Chem import AllChem
from openbabel import openbabel as ob

from ..storage.file_manager import find_extension, find_compound_name, create_out_file
from ..adapters.autodocktools.autodocktools_adapter import prepare_ligand_mgltools
from .logger import setup_logger

logger = setup_logger(__name__)


class MoleculeProcessor:
    """Handles molecular structure processing and format conversion."""
    
    def __init__(self, num_conformers: int = 10, random_seed: int = 42):
        """Initialize processor with conformer generation parameters.
        
        Args:
            num_conformers: Number of conformers to generate
            random_seed: Random seed for reproducibility
        """
        self.num_conformers = num_conformers
        self.random_seed = random_seed
    
    def read_molecule(self, filepath: str) -> Optional[Chem.Mol]:
        """Read molecule from file using RDKit.
        
        Args:
            filepath: Path to molecule file
            
        Returns:
            RDKit molecule object or None if read fails
        """
        ext = find_extension(filepath).lower()
        
        try:
            if ext == ".sdf":
                suppl = Chem.SDMolSupplier(filepath, removeHs=False)
                mol = suppl[0] if suppl and len(suppl) > 0 else None
            elif ext == ".mol2":
                mol = Chem.MolFromMol2File(filepath, removeHs=False)
            elif ext == ".mol":
                mol = Chem.MolFromMolFile(filepath, removeHs=False)
            elif ext == ".pdb":
                mol = Chem.MolFromPDBFile(filepath, removeHs=False)
            else:
                raise ValueError(f"Unsupported format: {ext}")
            
            return mol
        except Exception as e:
            logger.error(f"Failed to read molecule from {filepath}: {e}")
            return None
    
    def add_hydrogens(self, mol: Chem.Mol) -> Chem.Mol:
        """Add hydrogens to molecule.
        
        Args:
            mol: RDKit molecule
            
        Returns:
            Molecule with hydrogens added
        """
        return Chem.AddHs(mol)
    
    def generate_conformers(self, mol: Chem.Mol) -> List[int]:
        """Generate 3D conformers using ETKDG.
        
        Args:
            mol: RDKit molecule
            
        Returns:
            List of conformer IDs
            
        Raises:
            RuntimeError: If conformer generation fails
        """
        params = AllChem.ETKDGv3()
        params.numThreads = 1
        params.pruneRmsThresh = 0.5
        params.randomSeed = self.random_seed
        
        conf_ids = AllChem.EmbedMultipleConfs(
            mol,
            numConfs=self.num_conformers,
            params=params
        )
        
        if len(conf_ids) == 0:
            raise RuntimeError("Conformer embedding failed")
        
        return list(conf_ids)
    
    def optimize_conformers(self, mol: Chem.Mol, conf_ids: List[int]) -> Tuple[int, List[str]]:
        """Optimize conformers with MMFF and return best conformer ID.
        
        Args:
            mol: RDKit molecule with conformers
            conf_ids: List of conformer IDs to optimize
            
        Returns:
            Tuple of (best_conformer_id, warnings)
        """
        warnings = []
        
        if not AllChem.MMFFHasAllMoleculeParams(mol):
            warnings.append("MMFF parameters missing, skipping optimization")
            return conf_ids[0], warnings
        
        results = AllChem.MMFFOptimizeMoleculeConfs(mol, numThreads=1)
        
        valid_ids = []
        valid_energies = []
        
        for cid, (status, energy) in zip(conf_ids, results):
            if status == 0:  # Converged
                valid_ids.append(cid)
                valid_energies.append(energy)
        
        if valid_ids:
            best_idx = valid_energies.index(min(valid_energies))
            return valid_ids[best_idx], warnings
        else:
            warnings.append("No conformers converged in MMFF optimization")
            return conf_ids[0], warnings
    
    def extract_best_conformer(self, mol: Chem.Mol, conf_id: int) -> Chem.Mol:
        """Create new molecule with only the best conformer.
        
        Args:
            mol: Original molecule with multiple conformers
            conf_id: ID of the conformer to extract
            
        Returns:
            New molecule with single conformer
        """
        best_mol = Chem.Mol(mol)
        best_conf = mol.GetConformer(conf_id)
        
        best_mol.RemoveAllConformers()
        best_mol.AddConformer(best_conf, assignId=True)
        
        return best_mol
    
    def save_as_mol2(self, mol: Chem.Mol, output_path: str) -> str:
        """Save molecule as MOL2 format (via SDF temporary file).
        
        Args:
            mol: RDKit molecule
            output_path: Path for output MOL2 file
            
        Returns:
            Path to saved MOL2 file
            
        Raises:
            RuntimeError: If conversion fails
        """
        # Save as SDF first
        temp_sdf = output_path.replace(".mol2", ".sdf")
        writer = Chem.SDWriter(temp_sdf)
        writer.write(mol)
        writer.close()
        
        # Convert SDF to MOL2 with OpenBabel
        conv = ob.OBConversion()
        conv.SetInFormat("sdf")
        conv.SetOutFormat("mol2")
        
        obmol = ob.OBMol()
        if not conv.ReadFile(obmol, temp_sdf):
            raise RuntimeError("OpenBabel failed reading SDF")
        
        if not conv.WriteFile(obmol, output_path):
            raise RuntimeError("OpenBabel failed writing MOL2")
        
        # Clean up temporary file
        os.remove(temp_sdf)
        
        return output_path

    @staticmethod
    def _pdbqt_hydrogen_count(pdbqt_path: str) -> int:
        """Count explicit hydrogen atoms in a PDBQT file."""
        h_count = 0
        with open(pdbqt_path, "r") as handle:
            for line in handle:
                if line.startswith(("ATOM", "HETATM")):
                    atom_type = line[77:].strip() if len(line) >= 78 else ""
                    parts = line.split()
                    fallback_type = parts[-1] if parts else ""
                    token = atom_type or fallback_type
                    if token.upper().startswith("H"):
                        h_count += 1
        return h_count

    @staticmethod
    def _write_rigid_pdbqt_with_explicit_h(obmol: ob.OBMol, output_path: str) -> None:
        """Write a rigid PDBQT keeping explicit hydrogens for tiny ligands (e.g. CH4)."""
        charge_model = ob.OBChargeModel.FindType("gasteiger")
        if charge_model is not None:
            charge_model.ComputeCharges(obmol)

        with open(output_path, "w") as handle:
            handle.write("REMARK  Name = LIG\n")
            handle.write("REMARK  0 active torsions:\n")
            handle.write("REMARK  status: ('A' for Active; 'I' for Inactive)\n")
            handle.write("REMARK                            x       y       z     vdW  Elec       q    Type\n")
            handle.write("REMARK                         _______ _______ _______ _____ _____    ______ ____\n")
            handle.write("ROOT\n")

            atom_index = 1
            h_index = 1
            c_index = 1
            for atom in ob.OBMolAtomIter(obmol):
                element = atom.GetType().strip().capitalize() or atom.GetAtomicNum()
                symbol = atom.GetType().strip()[:2].strip()
                if not symbol:
                    symbol = atom.GetResidue().GetAtomID(atom).strip() if atom.GetResidue() else "X"
                symbol = symbol.capitalize()

                if atom.GetAtomicNum() == 1:
                    atom_name = f"H{h_index}"
                    atom_type = "H"
                    h_index += 1
                elif atom.GetAtomicNum() == 6:
                    atom_name = f"C{c_index}"
                    atom_type = "C"
                    c_index += 1
                else:
                    atom_name = f"{symbol}{atom_index}"
                    atom_type = symbol

                line = (
                    f"ATOM  {atom_index:5d} {atom_name:<4s} LIG A   1"
                    f"    {atom.GetX():8.3f}{atom.GetY():8.3f}{atom.GetZ():8.3f}"
                    f"  0.00  0.00  {atom.GetPartialCharge():8.3f} {atom_type:<2s}\n"
                )
                handle.write(line)
                atom_index += 1

            handle.write("ENDROOT\n")
            handle.write("TORSDOF 0\n")
    
    def convert_to_pdbqt(self, mol2_path: str, output_path: str, 
                         use_mgltools_fallback: bool = True) -> Tuple[str, List[str]]:
        """Convert MOL2 to PDBQT format.
        
        Args:
            mol2_path: Path to input MOL2 file
            output_path: Path for output PDBQT file
            use_mgltools_fallback: Use MGLTools if OpenBabel fails
            
        Returns:
            Tuple of (output_path, warnings)
        """
        warnings = []
        
        try:
            # Try OpenBabel first
            conv = ob.OBConversion()
            conv.SetInFormat("mol2")
            conv.SetOutFormat("pdbqt")
            
            obmol = ob.OBMol()
            if not conv.ReadFile(obmol, mol2_path):
                raise RuntimeError("OpenBabel failed reading MOL2")

            # Ensure explicit hydrogens are present before PDBQT export.
            # This prevents tiny molecules (e.g. CH4) from losing H atoms.
            obmol.AddHydrogens()
            input_h_count = sum(1 for atom in ob.OBMolAtomIter(obmol) if atom.GetAtomicNum() == 1)
            input_heavy_count = sum(1 for atom in ob.OBMolAtomIter(obmol) if atom.GetAtomicNum() > 1)
            
            if not conv.WriteFile(obmol, output_path):
                raise RuntimeError("OpenBabel failed writing PDBQT")

            output_h_count = self._pdbqt_hydrogen_count(output_path)
            # Note: OpenBabel's PDBQT writer removes non-polar H atoms (united-atom model),
            # which is the standard for AutoDock. Not rewriting with explicit H.
            #if input_h_count > 0 and output_h_count == 0 and input_heavy_count == 1:
            #    warnings.append(
            #        "PDBQT united-atom conversion removed non-polar hydrogens; "
            #        "rewriting rigid PDBQT with explicit H atoms for tiny ligand."
            #    )
            #    self._write_rigid_pdbqt_with_explicit_h(obmol, output_path)
            
            return output_path, warnings
            
        except Exception as e:
            if use_mgltools_fallback:
                warnings.append(f"OpenBabel PDBQT conversion failed, using MGLTools fallback: {str(e)}")
                logger.warning(warnings[-1])
                
                output_dir = os.path.dirname(output_path)
                prepare_ligand_mgltools(
                    mol2_path,
                    output_dir,
                    output_file=output_path,
                    keep_nonpolar_hydrogens=True,
                )
                
                return output_path, warnings
            else:
                raise


def process_ligand(ligand_file: str, output_path: str) -> Tuple[str, bool, Optional[dict], List[str]]:
    """Process a single ligand file: prepare, optimize, and convert formats.
    
    This is a standalone function suitable for multiprocessing.
    
    Args:
        ligand_file: Path to input ligand file
        output_path: Base output directory
        
    Returns:
        Tuple of (ligand_name, success, error_details, warnings)
    """
    ligand_name = find_compound_name(ligand_file)
    warnings = []
    
    try:
        processor = MoleculeProcessor()
        
        # Read molecule
        mol = processor.read_molecule(ligand_file)
        if mol is None:
            raise RuntimeError("Failed to read molecule")
        
        # Add hydrogens
        mol = processor.add_hydrogens(mol)
        
        # Generate conformers
        conf_ids = processor.generate_conformers(mol)
        
        # Optimize and get best conformer
        best_conf_id, opt_warnings = processor.optimize_conformers(mol, conf_ids)
        warnings.extend(opt_warnings)
        
        # Extract best conformer
        mol = processor.extract_best_conformer(mol, best_conf_id)
        
        # Save as MOL2
        mol2_output = create_out_file(
            f'{output_path}/prepared_ligands',
            f'{ligand_name}_prepared_opt.mol2'
        )
        processor.save_as_mol2(mol, mol2_output)
        
        # Convert to PDBQT
        pdbqt_output = create_out_file(
            f'{output_path}/prepared_ligands_pdbqt',
            f'{ligand_name}.pdbqt'
        )
        _, conv_warnings = processor.convert_to_pdbqt(mol2_output, pdbqt_output)
        warnings.extend(conv_warnings)
        
        return (ligand_name, True, None, warnings)
        
    except Exception as e:
        error_details = {
            'ligand': ligand_name,
            'file': ligand_file,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'warnings': warnings
        }
        logger.error(f"{ligand_name}: Failed to prepare - {str(e)}")
        return (ligand_name, False, error_details, warnings)
