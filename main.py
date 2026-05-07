import os
import sys
from cli.dynamics_cli import run_cli

def main():
    try:
        run_cli()
    except Exception as e:
        print(f"\n[X] Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()