import os
import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# ANSI Color codes for premium styling
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
BRIGHT_BLUE = "\033[94m"
BG_DARK = "\033[40m"

BANNER = f"""{BRIGHT_BLUE}{BOLD}
███╗   ███╗██╗   ██╗ ██████╗ ██████╗  █████╗ ████████╗███████╗
████╗ ████║╚██╗ ██╔╝██╔════╝ ██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
██╔████╔██║ ╚████╔╝ ██║  ███╗██████╔╝███████║   ██║   █████╗  
██║╚██╔╝██║  ╚██╔╝  ██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  
██║ ╚═╝ ██║   ██║   ╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗
╚═╝     ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
{RESET}{CYAN}                 ~ Automated Java Migration Wizard ~{RESET}
"""

def print_boxed_summary(project_path: str, target_java: str, step_count: int = 0):
    p_path = Path(project_path)
    codebase_name = p_path.name
    
    # Defaults
    compilation_success = False
    passed_tests = 0
    total_tests = 0
    line_coverage = 0.0
    covered_lines = 0
    missed_lines = 0
    baseline_coverage = 0.0
    
    # Try reading eval.json
    eval_file = Path.cwd() / "test" / "artifacts" / "eval.json"
    if eval_file.exists():
        try:
            with open(eval_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if codebase_name in data:
                    cb_data = data[codebase_name]
                    compilation_success = cb_data.get("compilation_success", False)
                    passed_tests = cb_data.get("passed_tests", 0)
                    total_tests = cb_data.get("total_tests", 0)
                    line_coverage = cb_data.get("line_coverage", 0.0)
                    covered_lines = cb_data.get("covered_lines", 0)
                    missed_lines = cb_data.get("missed_lines", 0)
                    baseline_coverage = cb_data.get("baseline_coverage", 0.0)
                    if cb_data.get("step_count"):
                        step_count = cb_data.get("step_count")
        except Exception:
            pass

    comp_status = f"{GREEN}{BOLD}SUCCESS{RESET}" if compilation_success else f"{RED}{BOLD}FAILED{RESET}"
    test_pct = (passed_tests / total_tests * 100.0) if total_tests > 0 else 0.0
    test_status = f"{passed_tests} / {total_tests} ({test_pct:.1f}%)"
    
    # Check Gate 3 status
    coverage_drop = baseline_coverage - line_coverage
    if baseline_coverage > 0:
        if coverage_drop <= 5.0:
            gate_3_status = f"{GREEN}{BOLD}PASS{RESET} (Drop: {coverage_drop:.1f}pp)"
        else:
            gate_3_status = f"{RED}{BOLD}FAIL{RESET} (Drop: {coverage_drop:.1f}pp > 5pp)"
    else:
        gate_3_status = f"{YELLOW}{BOLD}N/A{RESET}"
    
    print(f"\n{BLUE}{BOLD}┌────────────────────────────────────────────────────────┐{RESET}")
    print(f"{BLUE}│{RESET}               {BOLD}{MAGENTA}MIGRATION RUN SUMMARY{RESET}                    {BLUE}│{RESET}")
    print(f"{BLUE}├────────────────────────────────────────────────────────┤{RESET}")
    print(f"{BLUE}│{RESET}  {BOLD}CodebaseName{RESET}:      {CYAN}{codebase_name:<36}{RESET} {BLUE}│{RESET}")
    print(f"{BLUE}│{RESET}  {BOLD}Target Java{RESET}:       {CYAN}{target_java:<36}{RESET} {BLUE}│{RESET}")
    print(f"{BLUE}│{RESET}  {BOLD}Compilation{RESET}:       {comp_status:<45} {BLUE}│{RESET}")
    print(f"{BLUE}│{RESET}  {BOLD}Tests Passed{RESET}:      {test_status:<36}{RESET} {BLUE}│{RESET}")
    print(f"{BLUE}│{RESET}  {BOLD}Baseline Cov{RESET}:      {YELLOW}{baseline_coverage:.1f}%{RESET:<44} {BLUE}│{RESET}")
    print(f"{BLUE}│{RESET}  {BOLD}Final Coverage{RESET}:    {YELLOW}{line_coverage:.1f}%{RESET:<44} {BLUE}│{RESET}")
    print(f"{BLUE}│{RESET}  {BOLD}Gate 3 (Drop){RESET}:     {gate_3_status:<45} {BLUE}│{RESET}")
    print(f"{BLUE}│{RESET}  {BOLD}Agent Step Count{RESET}:  {CYAN}{step_count:<36}{RESET} {BLUE}│{RESET}")
    print(f"{BLUE}└────────────────────────────────────────────────────────┘{RESET}\n")


def _print_final_summary(final_state: dict):
    from langchain_core.messages import AIMessage
    
    messages = final_state.get("messages", [])
    if messages:
        for msg in reversed(messages):
            if getattr(msg, "type", "") == "ai" or isinstance(msg, AIMessage):
                print(f"\n{GREEN}{BOLD}[AI RESPONSE]{RESET}\n{msg.content}\n")
                break

    print(f"{BLUE}{'=' * 50}{RESET}")
    print(f"{BOLD}{CYAN}State Result Summary:{RESET}")
    print(f"  Project Type: {YELLOW}{final_state.get('project_type', 'unknown')}{RESET}")
    print(f"  Dependencies Found: {YELLOW}{len(final_state.get('dependencies', []))}{RESET}")

    upgrade_report = final_state.get("upgrade_report") or {}
    reader_review = final_state.get("reader_review") or {}

    if upgrade_report:
        print(f"  Pipeline Status: {upgrade_report.get('status', 'n/a')}")
        print(f"  Solver Method: {upgrade_report.get('solver_method', 'n/a')}")
        solutions = upgrade_report.get("solutions", [])
        print(f"  Solutions Found: {len(solutions)}")
        smoke = upgrade_report.get("smoke_test_results", [])
        if smoke:
            passed = sum(1 for s in smoke if s.get("result", {}).get("status") == "PASS")
            print(f"  Smoke Tests: {passed}/{len(smoke)} passed")

    if reader_review:
        print("  ReaderAgent Final Review: ok")
        markdown_report = reader_review.get("markdown_report")
        if markdown_report:
            print()
            print(markdown_report)
            print()
        selected_index = reader_review.get("selected_solution_index")
        if selected_index:
            print(f"  Selected Solution: #{selected_index}")
        selected = reader_review.get("selected_solution", {})
        if selected:
            print(f"  Best Solution: {selected}")
        why = reader_review.get("why_selected")
        if why:
            print(f"  Why Selected: {why}")

    last_result = final_state.get("last_subagent_result", "")
    if last_result and not upgrade_report and not reader_review:
        try:
            parsed = json.loads(last_result)
            if isinstance(parsed, dict):
                print(f"  Pipeline Status: {parsed.get('status', 'n/a')}")
                print(f"  Solver Method: {parsed.get('solver_method', 'n/a')}")
                solutions = parsed.get("solutions", [])
                if solutions:
                    print(f"  Solutions Found: {len(solutions)}")
                    best = solutions[0] if solutions else {}
                    if isinstance(best, dict):
                        print(f"  Best Solution: {best}")
                smoke = parsed.get("smoke_test_results", [])
                if smoke:
                    passed = sum(1 for s in smoke if s.get("result", {}).get("status") == "PASS")
                    print(f"  Smoke Tests: {passed}/{len(smoke)} passed")
        except Exception:
            pass
    print(f"{BLUE}{'=' * 50}{RESET}")


def main():
    """
    Entry point to run the Mygrate LangGraph workflow via CLI with interactive wizard.
    """
    load_dotenv()
    print(BANNER)

    parser = argparse.ArgumentParser(description="Mygrate Multi-Agent Workflow")
    parser.add_argument("--path", type=str, required=False, help="Path to the project directory")
    parser.add_argument("--target-java", type=str, default="17", help="Target Java version (e.g. 17, 21)")
    parser.add_argument("--approve", action="store_true", help="Simulate human approval (skip interrupts)")
    args = parser.parse_args()

    project_path = args.path
    target_java = args.target_java

    # Interactive Wizard Mode if --path is not provided
    if not project_path:
        print(f"{YELLOW}{BOLD}Welcome to the MYGRATE Interactive Setup Wizard!{RESET}\n")
        try:
            # Get path
            while True:
                path_input = input(f"{CYAN}Enter target project path:{RESET} ").strip()
                if not path_input:
                    print(f"{RED}Error: Path cannot be empty.{RESET}")
                    continue
                resolved_path = Path(path_input)
                if not resolved_path.exists():
                    print(f"{RED}Error: Path '{path_input}' does not exist. Please enter a valid directory.{RESET}")
                    continue
                project_path = str(resolved_path.absolute())
                break

            # Get target Java version
            java_input = input(f"{CYAN}Enter target Java version [Default 17]:{RESET} ").strip()
            if java_input:
                target_java = java_input

            # Skip interrupts option
            approve_input = input(f"{CYAN}Run in auto-approve mode (non-interactive run)? [y/N]:{RESET} ").strip().lower()
            if approve_input in ("y", "yes"):
                args.approve = True

        except KeyboardInterrupt:
            print(f"\n{RED}Wizard aborted.{RESET}")
            sys.exit(1)

    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BOLD}{GREEN}⚡ Starting MYGRATE workflow for project:{RESET} {CYAN}{project_path}{RESET}")
    print(f"{BOLD}{GREEN}🎯 Target Java version:{RESET} {YELLOW}{target_java}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

    # Resolve log path and initialize Tee logging
    project_root_path = Path(project_path).resolve()
    log_dir = project_root_path / "test" / "artifacts"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "cli_output.log"

    class Tee:
        def __init__(self, log_path: Path, stream):
            log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_file = open(log_path, "a", encoding="utf-8")
            self.stream = stream

        def write(self, data):
            self.stream.write(data)
            self.log_file.write(data)
            self.log_file.flush()

        def flush(self):
            self.stream.flush()
            self.log_file.flush()

        def isatty(self):
            return hasattr(self.stream, "isatty") and self.stream.isatty()

        def close(self):
            if not self.log_file.closed:
                self.log_file.close()


    import sys
    tee_stdout = Tee(log_path, sys.stdout)
    tee_stderr = Tee(log_path, sys.stderr)
    sys.stdout = tee_stdout
    sys.stderr = tee_stderr

    try:
        print(f"-> {GREEN}[EVAL] Calculating baseline coverage for {project_path}...{RESET}")
        from src.tools.maven import MavenRunner
        baseline_runner = MavenRunner(target_java_version="")
        baseline_res = baseline_runner.coverage(Path(project_path), clean=True)
        baseline_coverage = baseline_res.line_coverage_pct if baseline_res.coverage_found else 0.0
        baseline_total_tests = baseline_res.total_tests
        baseline_passed_tests = baseline_res.passed_tests
        print(f"-> {GREEN}[EVAL] Baseline coverage: {baseline_coverage:.2f}% (Tests run: {baseline_total_tests}, Passed: {baseline_passed_tests}){RESET}")

        initial_state = {
            "project_path": project_path,
            "target_java_version": target_java,
            "project_type": None,
            "messages": [],
            "completed_tasks_summary": [],
            "dependencies": [],
            "upgrade_report": None,
            "candidate_solutions": None,
            "reader_review": None,
            "migration_tasks": [],
            "current_instruction": "",
            "last_subagent_result": "",
            "next_node": "supervisor",
            "baseline_coverage": baseline_coverage,
            "baseline_total_tests": baseline_total_tests,
            "baseline_passed_tests": baseline_passed_tests,
            "translator_completed": False,
        }

        if os.environ.get("LANGSMITH_API_KEY"):
            print(f"-> {GREEN}[TELEMETRY] LangSmith Tracing is ENABLED.{RESET}")
        else:
            print(f"-> {YELLOW}[TELEMETRY] LangSmith not configured.{RESET}")

        from src.workflow import build_app
        from langchain_core.messages import HumanMessage

        thread_id = "mygrate_cli_thread"
        config = {"configurable": {"thread_id": thread_id}}

        step_count = 0

        if args.approve:
            # Auto-approve: run end-to-end without interrupts
            initial_state["messages"].append(HumanMessage(content="Approve upgrade and proceed with migration."))
            run_app = build_app(interrupt=False)
            print(f"-> {GREEN}[WORKFLOW] Running pipeline automatically...{RESET}")
            final_state = run_app.invoke(initial_state, config=config)
            _print_final_summary(final_state)
            print_boxed_summary(project_path, target_java)
        else:
            # Human-in-the-loop mode
            run_app = build_app(interrupt=True)
            print(f"-> {GREEN}[WORKFLOW] Starting human-in-the-loop pipeline...{RESET}")
            run_app.invoke(initial_state, config=config)

            while True:
                state_val = run_app.get_state(config).values
                next_node = state_val.get("next_node", "end")

                if next_node == "end":
                    _print_final_summary(state_val)
                    print_boxed_summary(project_path, target_java)

                    try:
                        user_input = input(f"\n{BOLD}{MAGENTA}MYGRATE>{RESET} ").strip()
                    except KeyboardInterrupt:
                        print("\nAborted.")
                        break

                    if user_input.lower() in ("exit", "quit"):
                        print(f"{GREEN}Goodbye!{RESET}")
                        break

                    if not user_input:
                        continue

                    run_app.update_state(
                        config,
                        {
                            "messages": [HumanMessage(content=user_input)],
                            "next_node": "supervisor"
                        }
                    )
                    print(f"-> {GREEN}[WORKFLOW] Resuming workflow with user feedback...{RESET}")
                    run_app.invoke(None, config=config)
                    continue

                print(f"{YELLOW}---> Running node: {next_node}{RESET}")
                run_app.invoke(None, config=config)
    finally:
        sys.stdout = tee_stdout.stream
        sys.stderr = tee_stderr.stream
        tee_stdout.close()
        tee_stderr.close()

        # Copy artifacts to working directory after migration run completes
        try:
            mygrate_root = Path(__file__).resolve().parent.parent
            src_dir = Path(project_path).resolve() / "test" / "artifacts"
            codebase_name = Path(project_path).resolve().name
            dest_dir = mygrate_root / "working" / codebase_name / "artifacts"
            if src_dir.exists():
                import shutil
                shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
                print(f"\n-> [POST-RUN] Successfully copied artifacts from {src_dir} to {dest_dir}\n")
        except Exception as e:
            print(f"\n-> [POST-RUN] Error copying artifacts to working directory: {e}\n")


if __name__ == "__main__":
    main()

