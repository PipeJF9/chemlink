"""Molecular processing utilities using RDKit and OpenBabel."""

import os
import traceback
from typing import Tuple, List, Optional
from rdkit import Chem
from rdkit.Chem import AllChem
from openbabel import openbabel as ob

from chemlink.storage.file_manager import find_extension, find_compound_name, create_out_file
from chemlink.adapters.autodocktools.autodocktools_adapter import prepare_ligand_mgltools
from chemlink.utils.logger import get_logger

logger = get_logger(__name__)


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
            
            if not conv.WriteFile(obmol, output_path):
                raise RuntimeError("OpenBabel failed writing PDBQT")
            
            return output_path, warnings
            
        except Exception as e:
            if use_mgltools_fallback:
                warnings.append(f"OpenBabel PDBQT conversion failed, using MGLTools fallback: {str(e)}")
                logger.warning(warnings[-1])
                
                output_dir = os.path.dirname(output_path)
                prepare_ligand_mgltools(mol2_path, output_dir)
                
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
