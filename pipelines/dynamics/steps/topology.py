import subprocess
import os
from pdbfixer import PDBFixer
from openmm.app import PDBFile

class TopologyStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        self.pdb_input_abs = os.path.abspath(self.config["pdb_input"])
        self.output_gro = "processed.gro" 

    def _repair_pdb(self, input_pdb, output_pdb_path):
        print(f"[*] Iniciando reparación de estructura con PDBFixer...")
        try:
            fixer = PDBFixer(filename=input_pdb)
            fixer.findMissingResidues()
            fixer.findMissingAtoms()
            fixer.addMissingAtoms()
            fixer.addMissingHydrogens(7.0)
            
            # Guardamos usando la ruta absoluta proporcionada
            with open(output_pdb_path, 'w') as f:
                PDBFile.writeFile(fixer.topology, fixer.positions, f)
            
            print(f"[✓] Estructura reparada confirmada en: {output_pdb_path}")
            return True
        except Exception as e:
            print(f"[X] Falló la reparación: {e}")
            return False

    def run(self):
        print(f"[*] Paso 1: Generando topología del sistema...")
        sim_type = self.config.get("sim_type")
        work_dir = self.config["work_dir"]

        # Definimos el nombre del archivo de salida de la reparación
        work_dir_abs = os.path.abspath(work_dir)
        repaired_filename = "complex_repaired.pdb"
        repaired_pdb_abs = os.path.join(work_dir_abs, repaired_filename)

        if sim_type in ["3", "4", "5", "6"]:
            command_cmd = [
                self.gmx_bin, "pdb2gmx",
                "-f", self.pdb_input_abs,
                "-o", self.output_gro,
                "-ff", "amber99sb-ildn", 
                "-water", "tip3p",
                "-ignh",
                "-chainsep", "id"
            ]
        else:
            command_cmd = [
                self.gmx_bin, "pdb2gmx",
                "-f", self.pdb_input_abs,
                "-o", self.output_gro,
                "-ff", "amber03", 
                "-water", "tip3p",
                "-ignh"
            ]

        try:
            # Intento 1: Ejecución normal
            subprocess.run(command_cmd, check=True, capture_output=True, text=True, cwd=work_dir)
            print(f"[✓] Topología generada exitosamente.")

        except subprocess.CalledProcessError as e:
            if "not found in the input file" in e.stderr or "atom" in e.stderr:
                print("[!] Detectados átomos faltantes. Intentando reparación automática...")
                
                # Pasamos la ruta absoluta a la función de reparación
                if self._repair_pdb(self.pdb_input_abs, repaired_pdb_abs):
                    
                    command_cmd[command_cmd.index("-f") + 1] = repaired_filename
                    
                    try:
                        subprocess.run(command_cmd, check=True, capture_output=True, text=True, cwd=work_dir)
                        print(f"[✓] Topología generada tras reparación.")
                    except subprocess.CalledProcessError as e2:
                        print(f"[X] Error persistente tras reparación:\n{e2.stderr}")
                        raise e2
            else:
                print(f"[X] Error en pdb2gmx:\n{e.stderr}")
                raise e