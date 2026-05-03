import os

class ComplexBuilderStep:
    def __init__(self, config):
        self.config = config
        self.prot_path = os.path.abspath(self.config["pdb_protein"])
        self.partner_path = os.path.abspath(self.config["pdb_partner"])
        self.output_path = os.path.abspath(self.config["pdb_input"])

    def run(self):
        print("\n[*] Construyendo complejo (Proteína + Compañero)...")
        
        if not os.path.exists(self.config["work_dir"]):
            os.makedirs(self.config["work_dir"])

        try:
            with open(self.output_path, 'w') as f_out:
                # 1. Leer y escribir proteína FORZANDO la Cadena 'A'
                with open(self.prot_path, 'r') as f_prot:
                    for line in f_prot:
                        if line.startswith(("ATOM", "HETATM")):
                            # Reemplaza el espacio en la posición 21 con 'A'
                            line_mod = line[:21] + 'A' + line[22:]
                            f_out.write(line_mod)
                        elif line.startswith(("TER", "ANISOU")):
                            f_out.write(line)
                
                f_out.write("TER\n")
                
                # 2. Leer y escribir compañero FORZANDO la Cadena 'B'
                with open(self.partner_path, 'r') as f_partner:
                    for line in f_partner:
                        if line.startswith(("ATOM", "HETATM")):
                            # Reemplaza el espacio en la posición 21 con 'B'
                            line_mod = line[:21] + 'B' + line[22:]
                            f_out.write(line_mod)
                        elif line.startswith(("TER", "ANISOU")):
                            f_out.write(line)
                
                f_out.write("END\n")

            print(f"[✓] Complejo creado en: {self.output_path}")
            
        except Exception as e:
            print(f"[X] Error al crear el complejo: {e}")
            raise e