import os
import sys
from cli.dynamics_menu import run_dynamics_menu

def main():
    while True:
        # Limpiar consola
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()

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