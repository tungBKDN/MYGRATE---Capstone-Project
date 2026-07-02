import os
import sys
import shutil
import subprocess
import re
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Color styling helpers for a premium look
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BRIGHT_BLUE = "\033[94m"
BLUE = "\033[34m"
DIM = "\033[2m"

BANNER = f"""{BRIGHT_BLUE}{BOLD}
███╗   ███╗██╗   ██╗ ██████╗ ██████╗  █████╗ ████████╗███████╗
████╗ ████║╚██╗ ██╔╝██╔════╝ ██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
██╔████╔██║ ╚████╔╝ ██║  ███╗██████╔╝███████║   ██║   █████╗  
██║╚██╔╝██║  ╚██╔╝  ██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  
██║ ╚═╝ ██║   ██║   ╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗
╚═╝     ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝  (TungBKDN)
{RESET}{CYAN}                 ~ Automated Java Migration Wizard ~{RESET}
"""

def print_header(title: str):
    width = 62
    print(f"\n{BRIGHT_BLUE}{BOLD}┌" + "─" * (width - 2) + "┐")
    print(f"│ {title.center(width - 4)} │")
    print(f"└" + "─" * (width - 2) + "┘" + RESET)

def get_input(prompt: str, default: str = "") -> str:
    suffix = f" {DIM}(Default: {default}){RESET}" if default else ""
    try:
        user_val = input(f" {CYAN}➜{RESET} {BOLD}{prompt}{RESET}{suffix}: ").strip()
        return user_val if user_val else default
    except KeyboardInterrupt:
        print(f"\n\n {RED}✖ Migration aborted by user.{RESET}\n")
        sys.exit(0)

IN_REPORT = False
IN_THOUGHT = False
IN_BLOCKED = False
IN_EXPLANATION = False

def format_log_line(line: str) -> tuple[str | None, bool]:
    """
    Parse a raw log line from src.main, filter out clutter, and return
    a beautiful styled representation.
    Returns: (formatted_string, is_prompt)
    """
    global IN_REPORT, IN_THOUGHT, IN_BLOCKED, IN_EXPLANATION

    line_str = line.strip()

    if IN_EXPLANATION:
        # Check if we hit a new step or command that signals the end of the explanation block
        if (line_str.startswith("-> [") and "Explanation:" not in line_str) or line_str.startswith("✦") or line_str.startswith("✖") or line_str.startswith("✔") or "Invoking:" in line_str or "Analyzing codebase state" in line_str or "Running node:" in line_str or "Entering Workflow Stage:" in line_str or "[MAVEN]" in line_str:
            IN_EXPLANATION = False
        else:
            # Format and return the explanation line (not collapsed, cyan)
            return f"    {CYAN}│{RESET}  {CYAN}{line.strip()}{RESET}", False

    if IN_THOUGHT:
        # Check if we hit a new step or command that signals the end of the thought block
        if (line_str.startswith("-> [") and "Thought:" not in line_str) or line_str.startswith("✦") or line_str.startswith("✖") or line_str.startswith("✔") or "Invoking:" in line_str or "Analyzing codebase state" in line_str or "Running node:" in line_str or "Entering Workflow Stage:" in line_str or "[MAVEN]" in line_str:
            IN_THOUGHT = False
        else:
            # Format and return the thought line indented with a vertical line and dim text
            return f"    \033[35m│\033[0m  \033[90m{line.strip()}\033[0m", False

    if IN_BLOCKED:
        if (line_str.startswith("-> [") and "BLOCKED" not in line_str) or line_str.startswith("✦") or line_str.startswith("✖") or line_str.startswith("✔") or "Analyzing codebase state" in line_str or "Running node:" in line_str or "Entering Workflow Stage:" in line_str or "[MAVEN]" in line_str:
            IN_BLOCKED = False
        else:
            # Format and return the details of the block indented with a red vertical line
            return f"    \033[31m│\033[0m  \033[91m{line.strip()}\033[0m", False

    # Detect Python traceback lines so they aren't hidden
    if (line.startswith("Traceback (most recent call last):") or 
        line.strip().startswith("File ") or 
        "Error:" in line or 
        "Exception:" in line or
        line.startswith("    ")):
        return f"{RED}{line.rstrip()}{RESET}", False

    line_str = line.strip()
    
    # Handle block parsing for reports
    if "TRANSLATOR MIGRATION REPORT" in line_str or "Migration Notes:" in line_str or "=== LLM" in line_str or "=== ❓ LLM" in line_str or "=== 🔄 LLM" in line_str or "=== 🔍 LLM" in line_str or "=== 💡 LLM" in line_str:
        IN_REPORT = True
        color = GREEN if "TRANSLATOR" in line_str else (YELLOW if "Migration Notes:" in line_str or "LLM" in line_str else CYAN)
        return f"\n{BOLD}{color}{line_str}{RESET}", False
    
    if "HUMAN INTERACTION REQUIRED" in line_str or "Enter your guidance" in line_str:
        return f"\033[35m{line.rstrip()}\033[0m", False
    
    if IN_REPORT and ("==================" in line_str or "======" in line_str):
        IN_REPORT = False
        return f"{BOLD}{GREEN if '======' in line_str else YELLOW}{line_str}{RESET}\n", False

    if IN_REPORT:
        if (line_str.startswith("┌──") or 
            "MIGRATION RUN SUMMARY" in line_str or 
            "State Result Summary:" in line_str or 
            "Entering Workflow Stage:" in line_str or 
            "[POST-RUN]" in line_str or 
            "Successfully completed" in line_str or
            "[EVAL]" in line_str or
            "[jdeprscan]" in line_str or
            "[AI RESPONSE]" in line_str or
            "HUMAN INTERACTION REQUIRED" in line_str or
            "---> Running node" in line_str):
            IN_REPORT = False
        else:
            return f"  {line.rstrip()}", False

    if not line_str:
        return None, False

    # Detect interactive prompt
    if line_str.endswith("MYGRATE>") or "MYGRATE>" in line_str:
        # Wrap prompt in bold magenta
        return f"\n{BOLD}{MAGENTA}MYGRATE>{RESET} ", True

    # Filter out common verbose noise
    noise_patterns = [
        "langchain", "ChatOllama", "ChatGroq", "OLLAMA_BASE_URL", 
        "OLLAMA_KEY", "Telemetry", "http_client", "solrsearch",
        "Downloading from", "Downloaded from", "http://", "https://",
        "GET /", "POST /", "xml.etree", "ElementTree"
    ]
    if any(pattern in line_str for pattern in noise_patterns):
        return None, False

    # Style Subagent Thought Lines
    # format: -> [AGENT] details
    agent_match = re.search(r"^->\s*\[([^\]]+)\]\s*(.*)$", line_str)
    if agent_match:
        agent_name = agent_match.group(1).upper()
        details = agent_match.group(2)

        if "Calling tool:" in details:
            tool_name = details.split("Calling tool:")[1].strip()
            # Truncate long tool arguments
            if "(" in tool_name:
                base, args = tool_name.split("(", 1)
                tool_name = f"{base}({args[:60]}...)" if len(args) > 60 else tool_name
            return f"  {CYAN}✦{RESET} {BOLD}[{agent_name}]{RESET} Invoking: {YELLOW}{tool_name}{RESET}", False
        
        elif "Thought:" in details:
            IN_THOUGHT = True
            return f"  {MAGENTA}💡{RESET} {BOLD}[{agent_name}]{RESET} {MAGENTA}Thinking/Planning...{RESET}", False

        elif "ReAct iteration" in details:
            iter_num = re.search(r"iteration\s*(\d+/\d+)", details)
            iter_str = f" ({iter_num.group(1)})" if iter_num else ""
            return f"  {BRIGHT_BLUE}➜{RESET} {BOLD}[{agent_name}]{RESET} Analyzing codebase state...{iter_str}", False
        
        elif "Verifying project" in details:
            return f"  {BRIGHT_BLUE}➜{RESET} {BOLD}[{agent_name}]{RESET} Running verification tests...", False
        
        elif "Final answer" in details or "Direct response" in details:
            if "BLOCKED" in details:
                IN_BLOCKED = True
                err_msg = details.split("BLOCKED:")[1].strip() if "BLOCKED:" in details else details
                return f"  {RED}✖{RESET} {BOLD}[{agent_name}]{RESET} {RED}Submission Blocked:{RESET} {err_msg}", False
            return f"  {GREEN}✔{RESET} {BOLD}[{agent_name}]{RESET} Submission verified successfully.", False
            
        return f"  {BLUE}ℹ{RESET} {BOLD}[{agent_name}]{RESET} {details}", False

    # Style Node Run Declarations
    if line_str.startswith("---> Running node:"):
        node_name = line_str.split("Running node:")[1].strip().upper()
        return f"\n {BOLD}{MAGENTA}▶{RESET} {BOLD}Entering Workflow Stage: {CYAN}{node_name}{RESET}", False

    # Style Explanation lines
    if "Explanation:" in line_str:
        IN_EXPLANATION = True
        agent_match = re.search(r"^->\s*\[([^\]]+)\]", line_str)
        agent_name = agent_match.group(1).upper() if agent_match else "AGENT"
        explanation_msg = line_str.split("Explanation:", 1)[1].strip()
        if agent_name == "TRANSLATOR":
            return f"\n  {GREEN}➜{RESET} {BOLD}[{agent_name}] Action:{RESET} {CYAN}{explanation_msg}{RESET}", True
        return f"\n {BOLD}{CYAN}💬 [{agent_name}] Message to User:{RESET} {CYAN}{explanation_msg}{RESET}", True

    # Style baseline / evaluation metrics
    if "[EVAL]" in line_str:
        eval_msg = line_str.split("[EVAL]")[1].strip()
        return f" {BOLD}{GREEN}✦ [EVALUATION]{RESET} {eval_msg}", False

    # Style Maven compilation tools
    if "[MavenRunner]" in line_str:
        runner_msg = line_str.split("[MavenRunner]")[1].strip()
        return f" {BOLD}{BLUE}✦ [MAVEN]{RESET} {runner_msg}", False

    # Style diagnostic scan steps
    if "[jdeprscan]" in line_str:
        scan_msg = line_str.split("[jdeprscan]")[1].strip()
        # Avoid printing JDK path discovery lists to keep console clean
        if "JDK 8:" in scan_msg or "JDK 17:" in scan_msg:
            return f" {DIM}✦ [DIAGNOSTIC] {scan_msg}{RESET}", False
        return f" {BOLD}{YELLOW}✦ [DIAGNOSTIC]{RESET} {scan_msg}", False

    # Build / Compilation outputs
    if "[ERROR]" in line_str:
        # Highlight actual source file errors, filter out generic wrapper error logs
        if ".java:" in line_str or "pom.xml" in line_str:
            return f"  {RED}✖ {line_str}{RESET}", False
        return None, False

    if "COMPILATION ERROR" in line_str:
        return f"  {RED}✖ {BOLD}Compilation Failed:{RESET}", False

    # Final summary box styling
    if line_str.startswith("┌──") or line_str.startswith("│") or line_str.startswith("└──") or line_str.startswith("├──"):
        return f" {line_str}", False
    
    if "MIGRATION RUN SUMMARY" in line_str or "State Result Summary:" in line_str:
        return f" {BOLD}{line_str}{RESET}", False

    # Preserve markdown/reports outputs printed by final summaries
    if line_str.startswith("Project Type:") or line_str.startswith("Dependencies Found:") or line_str.startswith("Pipeline Status:") or line_str.startswith("Solutions Found:"):
        return f"  {line_str}", False
        
    if line_str.startswith("Selected Solution") or line_str.startswith("Best Solution") or line_str.startswith("Why Selected"):
        return f"  {BOLD}{GREEN}{line_str}{RESET}", False

    if "[AI RESPONSE]" in line_str:
        return f"\n{BOLD}{GREEN}=== {line_str} ==={RESET}", False

    return None, False

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="MYGRATE - Automated Java Migration Wizard")
    parser.add_argument("--path", type=str, help="Target project path or batch folder")
    parser.add_argument("--target-java", type=str, help="Target Java version (default: 17)")
    parser.add_argument("--approve", action="store_true", default=None, help="Run in auto-approve mode")
    parser.add_argument("--use-workspace", type=str, choices=["y", "n"], help="Copy projects to working directory (y/n)")
    parser.add_argument("--clean", type=str, choices=["y", "n"], help="Wipe existing working copies (y/n)")
    parser.add_argument("--all", action="store_true", default=None, help="Run on all subprojects in batch folder")
    args = parser.parse_args()

    print(BANNER)
    print_header("WELCOME TO THE MYGRATE MIGRATION SUITE")

    project_root = Path(__file__).resolve().parent
    default_freshbrew = project_root / "freshbrew_data"
    default_working = project_root / "working"

    # 1. Ask for target path or use args.path
    if args.path:
        target_path = Path(args.path).resolve()
        if not target_path.exists():
            print(f" {RED}✖ Error: Path '{args.path}' does not exist.{RESET}\n")
            sys.exit(1)
    else:
        while True:
            target_input = get_input("Enter target project path or batch folder", str(default_freshbrew))
            target_path = Path(target_input).resolve()
            if not target_path.exists():
                print(f" {RED}✖ Error: Path '{target_input}' does not exist. Please enter a valid path.{RESET}\n")
                continue
            break

    # 2. Ask for target Java version or use args.target_java
    if args.target_java:
        target_java = args.target_java
    else:
        target_java = get_input("Enter target Java version", "17")

    # 3. Ask for auto-approve mode or use args.approve
    if args.approve is not None:
        approve_mode = args.approve
    else:
        approve_input = get_input("Run in auto-approve mode (non-interactive runs)? (y/n)", "n").lower()
        approve_mode = approve_input in ("y", "yes")

    # 4. Check if single project or batch folder
    is_single = (target_path / "pom.xml").exists()
    
    codebases = []
    if is_single:
        print(f"\n {GREEN}✔ Detected a single Maven project at: {target_path}{RESET}")
        codebases.append(target_path)
    else:
        subdirs = sorted([d for d in target_path.iterdir() if d.is_dir()])
        valid_subdirs = [d for d in subdirs if (d / "pom.xml").exists()]
        if valid_subdirs:
            print(f"\n {GREEN}✔ Detected batch folder with {len(valid_subdirs)} Maven subprojects in {target_path}{RESET}")
            if args.all is not None:
                run_all = "y" if args.all else "n"
            else:
                run_all = get_input(f"Do you want to run on ALL {len(valid_subdirs)} subprojects? (y/n)", "y").lower()
            if run_all in ("y", "yes"):
                codebases = valid_subdirs
            else:
                print(f"\n {BOLD}Available subprojects:{RESET}")
                for idx, sd in enumerate(valid_subdirs):
                    print(f"   [{idx + 1}] {sd.name}")
                selection = get_input("Enter the number(s) to migrate (e.g. 1 or 1,2,3)", "1")
                try:
                    indices = [int(i.strip()) - 1 for i in selection.split(",")]
                    codebases = [valid_subdirs[i] for i in indices if 0 <= i < len(valid_subdirs)]
                except Exception:
                    print(f" {RED}⚠ Invalid selection. Defaulting to first subproject.{RESET}")
                    codebases = [valid_subdirs[0]]
        else:
            print(f"\n {RED}✖ No direct pom.xml or subprojects with pom.xml found in '{target_path}'.{RESET}\n")
            sys.exit(1)

    # 5. Clean / Incremental workspace copying
    use_workspace = False
    clean_mode = False
    if not is_single or (target_path.parent == default_freshbrew):
        if args.use_workspace is not None:
            use_workspace = args.use_workspace in ("y", "yes")
        else:
            use_workspace_input = get_input("Copy projects to working directory to avoid modifying originals? (y/n)", "y").lower()
            use_workspace = use_workspace_input in ("y", "yes")
            
        if use_workspace:
            if args.clean is not None:
                clean_mode = args.clean in ("y", "yes")
            else:
                clean_input = get_input("Wipe existing working copies (clean run)? (y/n)", "n").lower()
                clean_mode = clean_input in ("y", "yes")

    print_header("MYGRATE EXECUTION POOL INITIALIZED")
    print(f"  {BOLD}Target JDK{RESET}: {YELLOW}{target_java}{RESET}")
    print(f"  {BOLD}Auto Mode{RESET}:  {YELLOW}{approve_mode}{RESET}")
    print(f"  {BOLD}Workspace{RESET}:  {YELLOW}{use_workspace}{RESET}")
    print(f"  {BOLD}Codebases{RESET}:  {CYAN}" + ", ".join([cb.name for cb in codebases]) + f"{RESET}")
    print(f"{BRIGHT_BLUE}{'═' * 62}{RESET}\n")

    completed = 0
    total = len(codebases)

    for i, source_path in enumerate(codebases):
        # Pause every 5 codebases for user feedback if in batch mode
        if completed > 0 and completed % 5 == 0:
            print_header(f"PAUSE: PROCESSED {completed} PROJECTS")
            user_choice = get_input("Continue migrating the next projects? (y/n)", "y").lower()
            if user_choice not in ("y", "yes"):
                print(f"\n {CYAN}ℹ Execution pool stopped by user.{RESET}\n")
                break

        folder_name = source_path.name
        if use_workspace:
            # Read and sanitize OLLAMA_MODEL name
            model_name = os.getenv("OLLAMA_MODEL", "default").replace(":", "_").replace("/", "_")
            model_working = default_working / model_name
            model_working.mkdir(parents=True, exist_ok=True)
            target_run_path = model_working / folder_name
            if target_run_path.exists():
                overwrite = "y"
                if not approve_mode:
                    overwrite = get_input(f" {YELLOW}⚠ Directory '{target_run_path.name}' already exists in working directory. Overwrite/wipe it?{RESET} (y/n)", "y").lower()
                
                if overwrite in ("y", "yes"):
                    import stat
                    def remove_readonly(func, p, excinfo):
                        try:
                            os.chmod(p, stat.S_IWRITE)
                            func(p)
                        except Exception:
                            pass
                    try:
                        shutil.rmtree(target_run_path, onexc=remove_readonly)
                    except TypeError:
                        shutil.rmtree(target_run_path, onerror=remove_readonly)
                    except Exception:
                        pass
                    
                    try:
                        shutil.copytree(source_path, target_run_path, ignore=shutil.ignore_patterns("target", ".git"), dirs_exist_ok=True)
                    except Exception as e:
                        print(f" {RED}⚠ Warning: Copy failed: {e}. Attempting to run with existing directory.{RESET}")
            else:
                shutil.copytree(source_path, target_run_path, ignore=shutil.ignore_patterns("target", ".git"))
        else:
            target_run_path = source_path

        print_header(f"RUNNING MIGRATION [{i+1}/{total}]: {folder_name.upper()}")

        python_exe = sys.executable
        for venv_name in [".venv", "venv"]:
            venv_py = project_root / venv_name / "Scripts" / "python.exe"
            if venv_py.exists():
                python_exe = str(venv_py)
                break

        cmd = [
            python_exe,
            "-u",
            "-m", "src.main",
            "--path", str(target_run_path.absolute()),
            "--target-java", target_java
        ]
        if approve_mode:
            cmd.append("--approve")

        # Start subprocess with full stdin/stdout mapping
        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                bufsize=1,
                shell=False
            )

            import queue
            import threading
            import time

            io_queue = queue.Queue()

            def stream_reader(pipe, q):
                try:
                    for char in iter(lambda: pipe.read(1), ''):
                        q.put(char)
                except Exception:
                    pass
                finally:
                    q.put(None)

            reader_thread = threading.Thread(
                target=stream_reader,
                args=(process.stdout, io_queue),
                daemon=True
            )
            reader_thread.start()

            buffer = ""

            while True:
                char = io_queue.get()
                if char is None:
                    break

                buffer += char
                
                # Check for line completion
                if buffer.endswith("\n"):
                    formatted, _ = format_log_line(buffer)
                    if formatted:
                        print(formatted)
                    buffer = ""
                # Check for interactive human input prompt (ending with MYGRATE> )
                elif buffer.endswith("MYGRATE> "):
                    formatted, is_prompt = format_log_line(buffer)
                    if is_prompt:
                        print(formatted, end="", flush=True)
                        buffer = ""
                        try:
                            user_input = input().strip()
                        except KeyboardInterrupt:
                            process.terminate()
                            print(f"\n\n {RED}✖ Process aborted by user.{RESET}\n")
                            sys.exit(0)
                        process.stdin.write(user_input + "\n")
                        process.stdin.flush()

            process.wait()
            if process.returncode == 0:
                print(f"\n {GREEN}✔ Successfully completed migration for {folder_name}.{RESET}")
            else:
                print(f"\n {RED}✖ Migration process exited with code {process.returncode} for {folder_name}.{RESET}")
        except KeyboardInterrupt:
            print(f"\n\n {RED}✖ Process interrupted by user.{RESET}\n")
            sys.exit(0)
        except Exception as e:
            print(f" {RED}✖ Error: Subprocess execution failed: {e}{RESET}")

        completed += 1

    print_header(f"FINISHED: {completed}/{total} PROJECTS PROCESSED")

if __name__ == "__main__":
    main()
