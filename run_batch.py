"""
MYGRATE Batch Execution Runner
================================
Chạy pipeline migration trên nhiều codebase cùng lúc.

Mặc định: chạy TẤT CẢ thư mục trong freshbrew_data/.
Nếu muốn chạy tập con, truyền tên codebase qua --only:
    python run_batch.py --only log4j2-elasticsearch kafka-spout

Kết quả được lưu vào eval_<model>.json tại thư mục gốc.
Những codebase đã có kết quả sẽ tự động được BỎ QUA (skip) trừ khi --force.
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
RED    = "\033[31m"
CYAN   = "\033[36m"
YELLOW = "\033[33m"
BLUE   = "\033[34m"
GREY   = "\033[90m"


def _model_slug() -> str:
    """Return a filesystem-safe model name derived from env vars."""
    raw = os.getenv("OLLAMA_MODEL", os.getenv("GROQ_MODEL", "default"))
    return raw.replace(":", "_").replace("/", "_")


def _eval_file(project_root: Path) -> Path:
    return project_root / f"eval_{_model_slug()}.json"


def _load_eval(project_root: Path) -> dict:
    """Load existing eval results; return empty dict on any error."""
    path = _eval_file(project_root)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _has_result(eval_data: dict, codebase_name: str) -> bool:
    """True if there is already an entry for this codebase in eval data."""
    return codebase_name in eval_data


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="MYGRATE Batch Execution Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--only", nargs="*", metavar="CODEBASE",
        help="Run only these codebase names (space-separated). Default: all.",
    )
    parser.add_argument(
        "--clean", action="store_true", default=False,
        help="Wipe and re-copy fresh codebase from freshbrew_data before each run.",
    )
    parser.add_argument(
        "--force", action="store_true", default=False,
        help="Run even for codebases that already have results in eval_<model>.json.",
    )
    parser.add_argument(
        "--target-java", type=str, default="17",
        help="Target Java version (default: 17).",
    )
    parser.add_argument(
        "--pause-every", type=int, default=0, metavar="N",
        help="Pause and ask to continue every N completions (0 = never pause).",
    )
    parser.add_argument(
        "--reverse", action="store_true", default=False,
        help="Run codebases in reverse order (useful for running parallel processes).",
    )
    args = parser.parse_args()

    project_root  = Path(__file__).resolve().parent
    freshbrew_dir = project_root / "freshbrew_data"
    working_dir   = project_root / "working"

    if not freshbrew_dir.exists():
        print(f"{RED}[ERROR] freshbrew_data/ not found. Run clone_mini_dataset.ps1 first.{RESET}")
        sys.exit(1)

    # ── Resolve candidate list ────────────────────────────────────────────────
    all_codebases = sorted(d.name for d in freshbrew_dir.iterdir() if d.is_dir())

    if args.only:
        # Validate each name given via --only
        selected = []
        for name in args.only:
            if name in all_codebases:
                selected.append(name)
            else:
                print(f"{YELLOW}[WARN] '{name}' not found in freshbrew_data/ — skipping.{RESET}")
        codebases = selected
    else:
        codebases = all_codebases

    if not codebases:
        print(f"{RED}[ERROR] No codebases to process.{RESET}")
        sys.exit(1)

    # ── Load existing eval results to decide what to skip ────────────────────
    eval_data    = _load_eval(project_root)
    model_slug   = _model_slug()
    eval_path    = _eval_file(project_root)

    print(f"\n{CYAN}{BOLD}MYGRATE Batch Runner{RESET}")
    print(f"  Model         : {YELLOW}{model_slug}{RESET}")
    print(f"  Eval file     : {BLUE}{eval_path}{RESET}")
    print(f"  Freshbrew dir : {BLUE}{freshbrew_dir}{RESET}")
    print(f"  Working dir   : {BLUE}{working_dir}{RESET}")
    print(f"  Target Java   : {YELLOW}{args.target_java}{RESET}")
    print(f"  Force rerun   : {YELLOW}{args.force}{RESET}")
    print(f"  Clean copy    : {YELLOW}{args.clean}{RESET}")
    print(f"  Reverse order : {YELLOW}{args.reverse}{RESET}")
    print()

    # ── Classify: skip vs run ─────────────────────────────────────────────────
    to_run   = []
    skipped  = []
    for name in codebases:
        if not args.force and _has_result(eval_data, name):
            skipped.append(name)
        else:
            to_run.append(name)

    if args.reverse:
        to_run.reverse()

    if skipped:
        print(f"{GREY}Skipping {len(skipped)} already-evaluated codebase(s):{RESET}")
        for s in skipped:
            res = eval_data[s]
            if res.get("is_skip"):
                print(f"  {YELLOW}↷{RESET} {s:<38} {YELLOW}[SKIPPED: Abnormal Baseline]{RESET}")
            else:
                ok  = res.get("overall_success", False)
                tag = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
                print(f"  {tag} {s:<38} (gate1={res.get('compilation_success','?')}, "
                      f"gate2={res.get('gate2_tests_pass','?')}, gate3={res.get('gate3_coverage_ok','?')})")
        print()

    if not to_run:
        print(f"{GREEN}{BOLD}All codebases already evaluated. Nothing to run.{RESET}")
        print(f"Use --force to re-run everything, or --only <name> to rerun specific ones.")
        sys.exit(0)

    print(f"{CYAN}Will run {len(to_run)} codebase(s):{RESET}")
    for name in to_run:
        print(f"  • {name}")
    print()

    # ── Resolve python executable ─────────────────────────────────────────────
    python_exe = sys.executable
    for venv_name in (".venv", "venv"):
        venv_py = project_root / venv_name / "Scripts" / "python.exe"
        if venv_py.exists():
            python_exe = str(venv_py)
            break

    working_dir.mkdir(parents=True, exist_ok=True)

    completed = 0
    total     = len(to_run)

    for i, name in enumerate(to_run):
        # ── Optional pause ────────────────────────────────────────────────────
        if args.pause_every > 0 and completed > 0 and completed % args.pause_every == 0:
            print(f"\n{YELLOW}{BOLD}=== PAUSE: Processed {completed} codebases ==={RESET}")
            try:
                choice = input(f"{YELLOW}Continue? (Y/n): {RESET}").strip().lower()
                if choice in ("n", "no"):
                    print(f"{CYAN}Batch execution aborted by user.{RESET}")
                    break
            except KeyboardInterrupt:
                print(f"\n{RED}Aborted.{RESET}")
                sys.exit(0)

        source_path = freshbrew_dir / name
        model_working = working_dir / model_slug
        model_working.mkdir(parents=True, exist_ok=True)
        target_path = model_working / name

        if not source_path.exists():
            print(f"{RED}[SKIP] Source '{name}' does not exist in freshbrew_data/.{RESET}")
            continue

        print(f"\n{CYAN}{BOLD}[{i+1}/{total}] {name}{RESET}")

        # ── Prepare working copy ──────────────────────────────────────────────
        target_pom = target_path / "pom.xml"
        
        # Use UNC paths on Windows to bypass 260-char MAX_PATH limit
        source_path_str = str(source_path.resolve())
        target_path_str = str(target_path.resolve())
        target_pom_str = str(target_pom.resolve())
        if os.name == "nt":
            source_path_str = "\\\\?\\" + source_path_str
            target_path_str = "\\\\?\\" + target_path_str
            target_pom_str = "\\\\?\\" + target_pom_str

        if args.clean or not os.path.exists(target_path_str) or not os.path.exists(target_pom_str):
            if os.path.exists(target_path_str):
                print(f"  -> Cleaning {target_path} ...")
                def remove_readonly(func, path, excinfo):
                    import stat
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                shutil.rmtree(target_path_str, onerror=remove_readonly)
            print(f"  -> Copying fresh copy ...")
            shutil.copytree(source_path_str, target_path_str, ignore=shutil.ignore_patterns("target"))
        else:
            print(f"  -> {GREEN}Using existing copy (incremental mode){RESET}")

        # ── Run pipeline ──────────────────────────────────────────────────────
        cmd = [
            python_exe,
            "-m", "src.main",
            "--path", str(target_path.absolute()),
            "--target-java", args.target_java,
            "--approve",
        ]
        print(f"  -> {GREY}{' '.join(cmd)}{RESET}")

        try:
            res = subprocess.run(cmd, cwd=str(project_root), shell=False)
            if res.returncode == 0:
                print(f"  {GREEN}✓ Completed {name}{RESET}")
            else:
                print(f"  {RED}✗ Exit code {res.returncode} for {name}{RESET}")
        except KeyboardInterrupt:
            print(f"\n{RED}Interrupted by user.{RESET}")
            sys.exit(0)
        except Exception as e:
            print(f"  {RED}[ERROR] Subprocess failed: {e}{RESET}")

        completed += 1

        # ── Reload eval to show running tally ─────────────────────────────────
        eval_data = _load_eval(project_root)
        if name in eval_data:
            res_entry = eval_data[name]
            if res_entry.get("is_skip"):
                print(f"  Result: {YELLOW}↷ SKIPPED (Abnormal Baseline: cov={res_entry.get('baseline_coverage', 0.0):.2f}%, passed_tests={res_entry.get('baseline_passed_tests', 0)}){RESET}")
            else:
                ok = res_entry.get("overall_success", False)
                g1 = "PASS" if res_entry.get("compilation_success") else "FAIL"
                g2 = "PASS" if res_entry.get("gate2_tests_pass")    else "FAIL"
                g3 = "PASS" if res_entry.get("gate3_coverage_ok")   else "FAIL"
                tag = f"{GREEN}✓ SUCCESS{RESET}" if ok else f"{RED}✗ FAIL{RESET}"
                print(f"  Result: {tag}  Gate1={g1}  Gate2={g2}  Gate3={g3}  "
                      f"Tests={res_entry.get('passed_tests',0)}/{res_entry.get('total_tests',0)}  "
                      f"Steps={res_entry.get('step_count',0)}")

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n{GREEN}{BOLD}=== Batch Done: {completed}/{total} ran ==={RESET}")

    eval_data = _load_eval(project_root)
    if eval_data:
        successes  = sum(1 for v in eval_data.values() if v.get("overall_success") and not v.get("is_skip"))
        skipped_count = sum(1 for v in eval_data.values() if v.get("is_skip"))
        total_eval = len(eval_data)
        print(f"\n{CYAN}Cumulative results in {eval_path.name}:{RESET}")
        print(f"  Overall success: {GREEN}{successes}{RESET}/{total_eval - skipped_count} (Skipped: {YELLOW}{skipped_count}{RESET})")
        print(f"\n  {'Codebase':<40} {'G1':^6} {'G2':^6} {'G3':^6} {'Tests':^12} {'Steps':^6}")
        print(f"  {'-'*40} {'------':^6} {'------':^6} {'------':^6} {'------------':^12} {'------':^6}")
        for cb_name, v in sorted(eval_data.items()):
            if v.get("is_skip"):
                g1, g2, g3 = "SKIP", "SKIP", "SKIP"
                marker = f"{YELLOW}↷{RESET}"
                g1c = g2c = g3c = YELLOW
                pt, tt, sc = 0, 0, 0
                test_str = "-"
                step_str = "-"
            else:
                g1  = "PASS" if v.get("compilation_success") else "FAIL"
                g2  = "PASS" if v.get("gate2_tests_pass")    else "FAIL"
                g3  = "PASS" if v.get("gate3_coverage_ok")   else "FAIL"
                ok  = v.get("overall_success", False)
                pt  = v.get("passed_tests", 0)
                tt  = v.get("total_tests",  0)
                sc  = v.get("step_count",   0)
                g1c = GREEN if g1 == "PASS" else RED
                g2c = GREEN if g2 == "PASS" else RED
                g3c = GREEN if g3 == "PASS" else RED
                marker = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
                test_str = f"{pt}/{tt}"
                step_str = str(sc)
            print(f"  {marker} {cb_name:<38} {g1c}{g1}{RESET:^6} {g2c}{g2}{RESET:^6} {g3c}{g3}{RESET:^6} {test_str:^12} {step_str:^6}")


if __name__ == "__main__":
    main()
