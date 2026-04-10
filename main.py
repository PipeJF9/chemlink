import os
import sys
from cli.dynamics_menu import run_dynamics_menu

def main():
    while True:
        # Limpiar consola (opcional, puedes comentarlo si prefieres ver el historial)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("--- CHEMLINK ---")
        print("1) Dinámica Molecular")
        print("2) Salir")
        
        choice = input("\n➤ Opción: ")

        if choice == "1":
            run_dynamics_menu()
        elif choice == "2":
            print("Saliendo...")
            break
        else:
            input("(!) Opción no válida. Enter para continuar...")

if __name__ == "__main__":
    main()