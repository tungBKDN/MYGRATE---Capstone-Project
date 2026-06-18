import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

# ==============================================================================
# CONFIGURATION: Specify the codebases you want to migrate in this array.
# Example: CODEBASES_TO_TEST = ["mongobee", "rome", "cantor"]
# If empty, all codebases found in freshbrew_dir/ (freshbrew_data) will be run.
# ==============================================================================``
CODEBASES_TO_TEST = [
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\kafka-spout",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\log4j2-elasticsearch",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\netty-zmtp",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\quilt",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\rhizobia_J",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\spark-jobs-rest-client",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\spring-batch-rest",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\spring-boot-rest-example",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\spring-context-support",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\spring-rest-exception-handler",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\sql-to-mongo-db-query-converter",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\suffixtree",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\token-bucket",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\unidecode",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\unix4j",
    # r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\velocity-spring-boot-project"
    r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\charts4j"
]

# Color styling helper
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"

def main():
    parser = argparse.ArgumentParser(description="MYGRATE Batch Execution Runner")
    parser.add_argument("--clean", action="store_true", default=False, help="Wipe and copy fresh codebase from freshbrew_data (default: False)")
    parser.add_argument("--target-java", type=str, default="17", help="Target Java version (default: 17)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    freshbrew_dir = project_root / "freshbrew_data"
    working_dir = project_root / "working"

    if not freshbrew_dir.exists():
        print(f"{RED}[ERROR] freshbrew_data directory does not exist. Please run clone_mini_dataset.ps1 first.{RESET}")
        sys.exit(1)

    # Resolve codebases to test
    if CODEBASES_TO_TEST:
        codebases = list(CODEBASES_TO_TEST)
        print(f"{CYAN}Running batch migration on configured array list: {codebases}{RESET}")
    else:
        # Defaults to all subdirectories in freshbrew_data/
        codebases = sorted([d.name for d in freshbrew_dir.iterdir() if d.is_dir()])
        print(f"{CYAN}Array list is empty. Found {len(codebases)} codebases in freshbrew_data/.{RESET}")

    working_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    total = len(codebases)

    for i, name in enumerate(codebases):
        # 1. Pacing check: pause every 5 completed migrations
        if completed > 0 and completed % 5 == 0:
            print(f"\n{YELLOW}{BOLD}=== PAUSE: Processed {completed} codebases ==={RESET}")
            try:
                user_choice = input(f"{YELLOW}Continue migrating the next codebases? (Y/n): {RESET}").strip().lower()
                if user_choice in ("n", "no"):
                    print(f"{CYAN}Batch execution aborted by user.{RESET}")
                    break
            except KeyboardInterrupt:
                print(f"\n{RED}Batch execution aborted.{RESET}")
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
            print(f"{RED}[SKIP] Source codebase '{name}' does not exist.{RESET}")
            continue

        print(f"\n{CYAN}{BOLD}[{i+1}/{total}] Preparing codebase: {name}{RESET}")

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
            "--target-java", args.target_java,
            "--approve"
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

        completed += 1

    print(f"\n{GREEN}{BOLD}=== Batch Execution Done: {completed}/{total} repos processed ==={RESET}")

if __name__ == "__main__":
    main()
