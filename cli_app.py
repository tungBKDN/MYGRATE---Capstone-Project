import os
import sys
import shutil
import subprocess
from pathlib import Path

# Color styling helpers
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BRIGHT_BLUE = "\033[94m"
BLUE = "\033[34m"

BANNER = f"""{BRIGHT_BLUE}{BOLD}
███╗   ███╗██╗   ██╗ ██████╗ ██████╗  █████╗ ████████╗███████╗
████╗ ████║╚██╗ ██╔╝██╔════╝ ██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
██╔████╔██║ ╚████╔╝ ██║  ███╗██████╔╝███████║   ██║   █████╗  
██║╚██╔╝██║  ╚██╔╝  ██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  
██║ ╚═╝ ██║   ██║   ╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗
╚═╝     ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝  (Tran Thanh Tung)
{RESET}{CYAN}                 ~ Automated Java Migration Wizard ~{RESET}
"""

def get_input(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        user_val = input(f"{prompt}{suffix}: ").strip()
        return user_val if user_val else default
    except KeyboardInterrupt:
        print(f"\n{RED}Aborted by user.{RESET}")
        sys.exit(0)

def main():
    print(BANNER)
    print(f"{YELLOW}{BOLD}Welcome to the MYGRATE Interactive CLI App!{RESET}\n")

    project_root = Path(__file__).resolve().parent
    default_freshbrew = project_root / "freshbrew_data"
    default_working = project_root / "working"

    # 1. Ask for target path
    while True:
        target_input = get_input(f"{CYAN}Enter target project path or batch folder{RESET}", str(default_freshbrew))
        target_path = Path(target_input).resolve()
        if not target_path.exists():
            print(f"{RED}Error: Path '{target_input}' does not exist. Please enter a valid path.{RESET}")
            continue
        break

    # 2. Ask for target Java version
    target_java = get_input(f"{CYAN}Enter target Java version{RESET}", "17")

    # 3. Ask for auto-approve mode
    approve_input = get_input(f"{CYAN}Run in auto-approve mode (non-interactive runs)? (y/n){RESET}", "y").lower()
    approve_mode = approve_input in ("y", "yes")

    # 4. Determine if single project or batch folder
    # We check if there's a pom.xml directly in target_path
    is_single = (target_path / "pom.xml").exists()
    
    codebases = []
    if is_single:
        print(f"\n{GREEN}Detected a single Maven project at: {target_path}{RESET}")
        codebases.append(target_path)
    else:
        # Check subdirectories
        subdirs = sorted([d for d in target_path.iterdir() if d.is_dir()])
        valid_subdirs = [d for d in subdirs if (d / "pom.xml").exists()]
        if valid_subdirs:
            print(f"\n{GREEN}Detected batch folder with {len(valid_subdirs)} Maven subprojects in {target_path}{RESET}")
            run_all = get_input(f"{CYAN}Do you want to run on ALL {len(valid_subdirs)} subprojects? (y/n){RESET}", "y").lower()
            if run_all in ("y", "yes"):
                codebases = valid_subdirs
            else:
                print(f"\nAvailable subprojects:")
                for idx, sd in enumerate(valid_subdirs):
                    print(f"  [{idx + 1}] {sd.name}")
                selection = get_input(f"{CYAN}Enter the number(s) to migrate (e.g. 1 or 1,2,3){RESET}", "1")
                try:
                    indices = [int(i.strip()) - 1 for i in selection.split(",")]
                    codebases = [valid_subdirs[i] for i in indices if 0 <= i < len(valid_subdirs)]
                except Exception:
                    print(f"{RED}Invalid selection. Defaulting to first subproject.{RESET}")
                    codebases = [valid_subdirs[0]]
        else:
            print(f"\n{RED}No direct pom.xml or subprojects with pom.xml found in '{target_path}'.{RESET}")
            sys.exit(1)

    # 5. Clean / Incremental workspace copying (Only if we copy from freshbrew_data or run batch)
    use_workspace = False
    clean_mode = False
    if not is_single or (target_path.parent == default_freshbrew):
        use_workspace_input = get_input(f"{CYAN}Copy projects to working directory ({default_working.name}/) to avoid modifying originals? (y/n){RESET}", "y").lower()
        use_workspace = use_workspace_input in ("y", "yes")
        if use_workspace:
            clean_input = get_input(f"{CYAN}Wipe existing working copies (clean run)? (y/n){RESET}", "n").lower()
            clean_mode = clean_input in ("y", "yes")

    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{GREEN}⚡ Starting MYGRATE execution pool:{RESET}")
    print(f"  Target JDK: {YELLOW}{target_java}{RESET}")
    print(f"  Auto Mode:  {YELLOW}{approve_mode}{RESET}")
    print(f"  Workspace:  {YELLOW}{use_workspace}{RESET}")
    print(f"  Projects to migrate:")
    for cb in codebases:
        print(f"    - {cb.name}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

    completed = 0
    total = len(codebases)

    for i, source_path in enumerate(codebases):
        # Pause every 5 codebases for user feedback if in batch mode
        if completed > 0 and completed % 5 == 0:
            print(f"\n{YELLOW}{BOLD}=== PAUSE: Processed {completed} projects ==={RESET}")
            user_choice = get_input(f"{YELLOW}Continue migrating the next projects? (y/n){RESET}", "y").lower()
            if user_choice not in ("y", "yes"):
                print(f"{CYAN}Execution pool aborted by user.{RESET}")
                break

        folder_name = source_path.name
        if use_workspace:
            default_working.mkdir(parents=True, exist_ok=True)
            target_run_path = default_working / folder_name
            if clean_mode:
                if target_run_path.exists():
                    print(f"  -> Cleaning existing working copy at {target_run_path}...")
                    shutil.rmtree(target_run_path)
                print(f"  -> Copying fresh copy to {target_run_path}...")
                shutil.copytree(source_path, target_run_path)
            else:
                if not target_run_path.exists():
                    print(f"  -> Copying fresh copy to {target_run_path}...")
                    shutil.copytree(source_path, target_run_path)
                else:
                    print(f"  -> {GREEN}Using existing copy at {target_run_path} (Incremental Mode){RESET}")
        else:
            target_run_path = source_path

        print(f"\n{CYAN}{BOLD}[{i+1}/{total}] Running migration on: {folder_name}{RESET}")

        cmd = [
            sys.executable,
            "-m", "src.main",
            "--path", str(target_run_path.absolute()),
            "--target-java", target_java
        ]
        if approve_mode:
            cmd.append("--approve")

        print(f"  -> Running: {' '.join(cmd)}")
        try:
            res = subprocess.run(cmd, cwd=str(project_root), shell=False)
            if res.returncode == 0:
                print(f"{GREEN}Successfully completed migration for {folder_name}.{RESET}")
            else:
                print(f"{RED}Migration process exited with code {res.returncode} for {folder_name}.{RESET}")
        except KeyboardInterrupt:
            print(f"\n{RED}Process interrupted by user.{RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"{RED}[ERROR] Subprocess run failed: {e}{RESET}")

        completed += 1

    print(f"\n{GREEN}{BOLD}=== Done: {completed}/{total} projects processed ==={RESET}")

if __name__ == "__main__":
    main()
