import os
import sys
from cli.dynamics_cli import run_cli
from cli.dynamics_menu import run_dynamics_menu

def main():
    try:
        run_cli()
    except Exception as e:
        print(f"\n[X] Error crítico en la ejecución: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()