import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

# Color styling helper
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"

def main():
    parser = argparse.ArgumentParser(description="MYGRATE Single Run Tool")
    parser.add_argument("--clean", action="store_true", default=False, help="Wipe and copy fresh codebase from freshbrew_data (default: False)")
    parser.add_argument("--target-java", type=str, default="17", help="Target Java version (default: 17)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    freshbrew_dir = project_root / "freshbrew_data"
    working_dir = project_root / "working"

    if not freshbrew_dir.exists():
        print(f"{RED}[ERROR] freshbrew_data directory does not exist. Please run clone_mini_dataset.ps1 first.{RESET}")
        sys.exit(1)

    # Prompt user to type in the codebase name or path
    try:
        name = input(f"{CYAN}Enter codebase name (e.g. jersey-jwt) or path to run: {RESET}").strip()
        if not name:
            print(f"{RED}[ERROR] No codebase entered.{RESET}")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{RED}Execution aborted by user.{RESET}")
        sys.exit(0)

    # Resolve folders safely: name could be an absolute path or relative path
    path_obj = Path(name)
    folder_name = path_obj.name

    # If 'name' is absolute, use it directly as the source path
    if path_obj.is_absolute():
        source_path = path_obj
    else:
        source_path = freshbrew_dir / name

    target_path = working_dir / folder_name

    if not source_path.exists():
        print(f"{RED}[ERROR] Source codebase '{name}' does not exist.{RESET}")
        sys.exit(1)

    print(f"\n{CYAN}{BOLD}Preparing codebase: {name}{RESET}")

    # Handle clean vs incremental mode
    if args.clean:
        if target_path.exists():
            print(f"  -> Cleaning existing working copy at {target_path}...")
            shutil.rmtree(target_path)
        print(f"  -> Copying fresh copy from {source_path} to {target_path}...")
        shutil.copytree(source_path, target_path)
    else:
        if not target_path.exists():
            print(f"  -> Target copy does not exist. Copying fresh copy from {source_path} to {target_path}...")
            shutil.copytree(source_path, target_path)
        else:
            print(f"  -> {GREEN}Using existing copy at {target_path} (Inspect/Incremental Mode){RESET}")

    # Run the MYGRATE pipeline via subprocess
    cmd = [
        sys.executable,
        "-m", "src.main",
        "--path", str(target_path.absolute()),
        "--target-java", args.target_java
    ]

    print(f"  -> Running: {' '.join(cmd)}")
    try:
        # We run in pass-through mode so user can see standard output live
        res = subprocess.run(cmd, cwd=str(project_root), shell=False)
        if res.returncode == 0:
            print(f"{GREEN}Successfully completed migration for {name}.{RESET}")
        else:
            print(f"{RED}Migration process exited with code {res.returncode} for {name}.{RESET}")
    except KeyboardInterrupt:
        print(f"\n{RED}Process interrupted by user.{RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{RED}[ERROR] Subprocess run failed: {e}{RESET}")

if __name__ == "__main__":
    main()
