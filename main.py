from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from colorama import Fore, Style, init as colorama_init
from dotenv import load_dotenv

from src.agents.reader_agent import ReaderAgent

from src.tools.maven_upgrade_tools import (
    HAS_Z3,
    DependencySolver,
    _check_jdk_available,
    analyze_dependency_conflicts,
    build_library_resolutions,
    inject_constrained_versions,
    index_java_project,
    run_runtime_smoke_test,
    solve_with_z3,
)


colorama_init(autoreset=True)

DEFAULT_PROJECT_PATH = Path(__file__).resolve().parent / "freshbrew_data" / "cantor"
DEFAULT_TARGET_JAVA = "17"
DEFAULT_MAX_VERSIONS = 5
DEFAULT_MAX_SOLUTIONS = 5
DEFAULT_SMOKE_TOP_K = 3


def clear_screen() -> None:
    if sys.stdout.isatty():
        print("\x1b[2J\x1b[H", end="")


def color_text(text: str, color: str = "white", bold: bool = False) -> str:
    palette = {
        "cyan": Fore.CYAN,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "red": Fore.RED,
        "magenta": Fore.MAGENTA,
        "blue": Fore.BLUE,
        "white": Fore.WHITE,
    }
    prefix = palette.get(color, Fore.WHITE)
    emphasis = Style.BRIGHT if bold else ""
    return f"{emphasis}{prefix}{text}{Style.RESET_ALL}"


def banner(title: str, subtitle: str | None = None) -> str:
    line = "═" * 78
    parts = [color_text(line, "cyan", True), color_text(f"  {title}", "cyan", True), color_text(line, "cyan", True)]
    if subtitle:
        parts.append(subtitle)
    return "\n".join(parts)


def normalize_project_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = path.resolve()
    return path


def key_to_string(key: Any) -> str:
    if isinstance(key, tuple) and len(key) == 2:
        return f"{key[0]}:{key[1]}"
    return str(key)


def normalize_solution(solution: Dict[Any, Any]) -> Dict[str, Any]:
    return {key_to_string(key): value for key, value in solution.items()}


def shorten(text: str, limit: int = 180) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def format_table(rows: List[Tuple[str, str]]) -> str:
    if not rows:
        return ""
    key_width = min(max(len(k) for k, _ in rows), 28)
    lines = []
    for key, value in rows:
        key_part = f"{key:<{key_width}}"
        value_part = shorten(str(value), max(20, 78 - key_width - 5))
        lines.append(f"  {color_text(key_part, 'cyan', True)} : {value_part}")
    return "\n".join(lines)


def render_dashboard(state: Dict[str, Any], no_clear: bool = False) -> None:
    if not no_clear:
        clear_screen()

    step = state.get("step", "init")
    project_path = state.get("project_path", "")
    target_java = state.get("target_java", DEFAULT_TARGET_JAVA)
    status = state.get("status", "running")
    current_agent = state.get("current_agent", "cli")
    current_activity = state.get("current_activity", "Starting")
    messages = state.get("messages", [])[-8:]
    candidates = state.get("candidates", {})
    solutions = state.get("solutions", [])
    smoke_results = state.get("smoke_test_results", [])
    best_solution = state.get("best_solution", {})

    print(banner("MYGRATE CLI", f"Project: {project_path} | Target Java: {target_java} | Step: {step}"))
    print()
    print(
        format_table(
            [
                ("Status", status),
                ("Subagent", current_agent),
                ("Activity", current_activity),
                ("Project Type", state.get("project_type", "n/a")),
                ("Dependencies", state.get("dependency_count", 0)),
                ("Candidates", len(candidates)),
                ("Solutions", len(solutions)),
                ("Smoke Tests", len(smoke_results)),
                ("JDK Available", state.get("jdk_available", False)),
                ("Solver", state.get("solver_method", "n/a")),
            ]
        )
    )
    print()

    if messages:
        print(color_text("Recent events", "yellow", True))
        for message in messages:
            print(f"  - {message}")
        print()

    if candidates:
        print(color_text("Candidate libraries", "green", True))
        for lib_key, versions in list(candidates.items())[:8]:
            print(f"  - {lib_key}: {len(versions)} version(s) -> {', '.join(versions[:4])}")
        print()

    if best_solution:
        print(color_text("Best solution", "magenta", True))
        for lib_key, version in list(best_solution.items())[:10]:
            print(f"  - {lib_key} -> {version}")
        print()

    if smoke_results:
        print(color_text("Smoke test status", "blue", True))
        for index, smoke in enumerate(smoke_results[:3], start=1):
            result = smoke.get("result", {})
            solution = smoke.get("solution", {})
            first_lib = next(iter(solution.items()), ("n/a", "n/a"))
            print(
                f"  - #{index} {first_lib[0]} -> {first_lib[1]} | "
                f"{result.get('status', 'n/a')}"
            )
        print()

    print(color_text("Live refresh enabled. Output updates after each pipeline stage.", "white", False))


def add_message(state: Dict[str, Any], message: str, no_clear: bool = False) -> None:
    state.setdefault("messages", []).append(message)
    render_dashboard(state, no_clear=no_clear)


def set_activity(
    state: Dict[str, Any],
    agent: str,
    step: str,
    activity: str,
    no_clear: bool = False,
) -> None:
    state["current_agent"] = agent
    state["step"] = step
    state["current_activity"] = activity
    add_message(state, f"[{agent}] {activity}", no_clear=no_clear)


def make_logger(state: Dict[str, Any], no_clear: bool = False):
    def _log(message: str) -> None:
        if message.startswith("[Download]"):
            state["current_agent"] = "ArchitectAgent"
            state["current_activity"] = message
        elif message.startswith("[Cache]"):
            state["current_agent"] = "ArchitectAgent"
            state["current_activity"] = message
        elif message.startswith("[Step "):
            state["current_agent"] = "ArchitectAgent"
            state["current_activity"] = message
        add_message(state, message, no_clear=no_clear)

    return _log


def build_report_path(project_path: Path) -> Path:
    report_root = Path("artifacts") / "codebase_discovery"
    report_root.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch if ch.isalnum() or ch in {".", "_", "-"} else "_" for ch in project_path.name).strip("_")
    if not safe_name:
        safe_name = "project"
    return report_root / f"{safe_name}_upgrade_report.json"


def run_pipeline(
    project_path: str,
    target_java: str,
    max_versions: int,
    max_solutions: int,
    smoke_top_k: int,
    no_clear: bool = False,
) -> Dict[str, Any]:
    project_root = normalize_project_path(project_path)
    state: Dict[str, Any] = {
        "project_path": str(project_root),
        "target_java": target_java,
        "status": "running",
        "step": "initializing",
        "project_type": "n/a",
        "dependency_count": 0,
        "jdk_available": False,
        "solver_method": "pending",
        "messages": [],
        "current_agent": "CLI",
        "current_activity": "Initializing pipeline",
        "candidates": {},
        "solutions": [],
        "smoke_test_results": [],
        "best_solution": {},
    }

    render_dashboard(state, no_clear=no_clear)
    set_activity(state, "ReaderAgent", "reader-index", f"Scanning project at {project_root}", no_clear=no_clear)
    log_event = make_logger(state, no_clear=no_clear)

    index_result = index_java_project(str(project_root))
    if index_result.get("status") != "ok":
        state["status"] = index_result.get("status", "error")
        state["step"] = "index-failed"
        state["messages"].append(index_result.get("message", "Indexing failed"))
        render_dashboard(state, no_clear=no_clear)
        return {"status": state["status"], **index_result}

    state["project_type"] = index_result.get("project_type", "unknown")
    dependencies = index_result.get("dependencies", [])
    state["dependency_count"] = len(dependencies)
    set_activity(
        state,
        "ReaderAgent",
        "indexed",
        f"Index complete: {state['project_type']} project with {len(dependencies)} dependency(s)",
        no_clear=no_clear,
    )

    root_deps = [dep for dep in dependencies if dep.get("scope") in ("compile", "runtime", "test", None)]
    if not root_deps:
        state["status"] = "error"
        set_activity(state, "ReaderAgent", "no-dependencies", "No root dependencies found to analyze.", no_clear=no_clear)
        return {
            "status": "error",
            "message": "No compatible dependencies found.",
            "project_path": str(project_root),
            "project_type": state["project_type"],
        }

    solver = DependencySolver(target_java=target_java, logger=log_event)
    set_activity(
        state,
        "ArchitectAgent",
        "step-1-3",
        f"Starting Step 1-3 scan for {len(root_deps)} root dependency(s)",
        no_clear=no_clear,
    )

    for index, dep in enumerate(root_deps, start=1):
        group_id = dep.get("groupId", "")
        artifact_id = dep.get("artifactId", "")
        if not group_id or not artifact_id:
            continue
        set_activity(
            state,
            "ArchitectAgent",
            f"step-1-3:{artifact_id}",
            f"[{index}/{len(root_deps)}] Scanning {group_id}:{artifact_id}",
            no_clear=no_clear,
        )
        solver.add_library(group_id, artifact_id, max_versions=max_versions)

    inject_constrained_versions(solver)
    state["candidates"] = {f"{g}:{a}": versions for (g, a), versions in solver.candidates.items()}
    set_activity(
        state,
        "ArchitectAgent",
        "step-1-3-complete",
        f"Step 1-3 complete: {len(solver.candidates)} candidate library set(s)",
        no_clear=no_clear,
    )

    jdk_available = _check_jdk_available()
    state["jdk_available"] = jdk_available
    if jdk_available:
        set_activity(state, "ArchitectAgent", "step-4", "Running Step 4 compile checks with javac --release", no_clear=no_clear)
        solver.run_step4()
        set_activity(state, "ArchitectAgent", "step-4-complete", "Step 4 complete", no_clear=no_clear)
    else:
        set_activity(
            state,
            "ArchitectAgent",
            "step-4-skipped",
            "JDK not available; Step 4 and Step 7 smoke tests will be skipped.",
            no_clear=no_clear,
        )

    set_activity(state, "ArchitectAgent", "step-5", "Building transitive dependency resolution graph", no_clear=no_clear)
    full_tree, lib_resolutions = build_library_resolutions(solver.candidates, solver.constraints)
    conflict_edges = analyze_dependency_conflicts(lib_resolutions)
    set_activity(
        state,
        "ArchitectAgent",
        "step-5-complete",
        f"Step 5 complete: {len(lib_resolutions)} resolved transitive group(s), {len(conflict_edges)} conflict edge(s)",
        no_clear=no_clear,
    )

    set_activity(state, "ArchitectAgent", "step-6", "Solving compatible dependency combinations", no_clear=no_clear)
    z3_solutions = solve_with_z3(solver.candidates, solver.constraints, max_solutions=max_solutions) if HAS_Z3 else None
    solver.solve()
    backtrack_solutions = solver.solutions

    if z3_solutions:
        chosen_solutions = z3_solutions
        solver_method = "z3"
    elif backtrack_solutions:
        chosen_solutions = [normalize_solution(solution) for solution in backtrack_solutions]
        solver_method = "backtracking"
    else:
        chosen_solutions = []
        solver_method = "none"

    state["solver_method"] = solver_method
    state["solutions"] = chosen_solutions[:max_solutions]
    set_activity(
        state,
        "ArchitectAgent",
        "step-6-complete",
        f"Step 6 complete: solver={solver_method}, solutions={len(chosen_solutions)}",
        no_clear=no_clear,
    )

    smoke_results: List[Dict[str, Any]] = []
    if jdk_available and chosen_solutions:
        set_activity(state, "ArchitectAgent", "step-7", f"Running Step 7 smoke tests for top {smoke_top_k} solution(s)", no_clear=no_clear)
        for index, solution in enumerate(chosen_solutions[:smoke_top_k], start=1):
            set_activity(state, "ArchitectAgent", f"step-7:{index}", f"Smoke testing solution #{index}", no_clear=no_clear)
            adapted = {}
            for lib_key, version in solution.items():
                if isinstance(lib_key, tuple):
                    adapted[lib_key] = version
                else:
                    parts = str(lib_key).split(":", 1)
                    if len(parts) == 2:
                        adapted[(parts[0], parts[1])] = version
                    else:
                        adapted[lib_key] = version
            result = run_runtime_smoke_test(adapted, solver.constraints, target_jdk=target_java, logger=log_event)
            smoke_results.append({"solution": solution, "result": result})
    elif not jdk_available:
        smoke_results = [{"solution": {}, "result": {"status": "SKIP", "reason": "JDK not available"}}]

    state["smoke_test_results"] = smoke_results

    best_solution: Dict[str, Any] = {}
    if chosen_solutions:
        passed = [item for item in smoke_results if item.get("result", {}).get("status") == "PASS"]
        if passed:
            best_solution = passed[0].get("solution", {})
        else:
            best_solution = chosen_solutions[0]
    state["best_solution"] = best_solution

    set_activity(
        state,
        "ReaderAgent",
        "reader-final-review",
        "Reviewing all validated candidates and selecting the final recommendation.",
        no_clear=no_clear,
    )

    reader_agent = ReaderAgent()
    review_instruction = json.dumps(
        {
            "project_path": str(project_root),
            "project_type": state["project_type"],
            "target_java": target_java,
            "dependencies": dependencies,
            "candidates": state["candidates"],
            "solutions": chosen_solutions[:max_solutions],
            "smoke_test_results": smoke_results,
            "best_solution": best_solution,
            "solver_method": solver_method,
            "step3_reports": {
                f"{g}:{a}:{v}": payload.get("step3", {}) for (g, a, v), payload in solver.reports.items()
            },
            "index_summary": index_result.get("index_summary", {}),
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    )
    reader_review_raw = reader_agent.review_candidates(review_instruction)
    try:
        reader_review = json.loads(reader_review_raw)
    except Exception:
        reader_review = {"status": "error", "message": "ReaderAgent produced invalid JSON.", "raw": reader_review_raw}

    selected_solution = reader_review.get("selected_solution") if isinstance(reader_review, dict) else None
    if isinstance(selected_solution, dict) and selected_solution:
        best_solution = selected_solution
        state["best_solution"] = best_solution
        add_message(state, "ReaderAgent selected the final best solution from the candidate set.", no_clear=no_clear)

    report = {
        "status": "ok",
        "pipeline": "live-7-step",
        "project_path": str(project_root),
        "project_type": state["project_type"],
        "target_java": target_java,
        "jdk_available": jdk_available,
        "solver_method": solver_method,
        "dependencies": dependencies,
        "candidates": state["candidates"],
        "conflict_edges": conflict_edges,
        "solutions": chosen_solutions[:max_solutions],
        "best_solution": best_solution,
        "smoke_test_results": smoke_results,
        "step3_reports": {
            f"{g}:{a}:{v}": payload.get("step3", {}) for (g, a, v), payload in solver.reports.items()
        },
        "index_summary": index_result.get("index_summary", {}),
        "pom_data": index_result.get("pom_data", {}),
        "transitive_tree_size": len(full_tree),
        "reader_review": reader_review,
    }

    report_path = build_report_path(project_root)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
    report["report_path"] = str(report_path)

    state["status"] = "done"
    set_activity(state, "CLI", "complete", f"Report written to {report_path}", no_clear=no_clear)

    print()
    print(banner("FINAL RESULT", f"Report saved at: {report_path}"))
    print()
    print(color_text("Summary", "green", True))
    print(format_table(
        [
            ("Project", project_root.name),
            ("Target Java", target_java),
            ("Solver", solver_method),
            ("Solutions", len(chosen_solutions)),
            ("Smoke Tests", len(smoke_results)),
            ("Report", str(report_path)),
        ]
    ))
    print()

    if chosen_solutions:
        print(color_text("Solutions", "magenta", True))
        for index, solution in enumerate(chosen_solutions[:max_solutions], start=1):
            print(f"  [{index}]")
            for lib_key, version in solution.items():
                print(f"    - {lib_key} -> {version}")
            if index < min(len(chosen_solutions), max_solutions):
                print()
    else:
        print(color_text("No valid solution found.", "red", True))

    if smoke_results:
        print()
        print(color_text("Smoke Tests", "blue", True))
        for index, smoke in enumerate(smoke_results, start=1):
            result = smoke.get("result", {})
            solution = smoke.get("solution", {})
            label = next(iter(solution.items()), ("n/a", "n/a"))
            print(f"  - #{index} {label[0]} -> {label[1]} : {result.get('status', 'n/a')}")

    if reader_review:
        print()
        print(color_text("ReaderAgent Review", "yellow", True))
        markdown_report = reader_review.get("markdown_report")
        if markdown_report:
            print(markdown_report)
        else:
            print(f"  - Status: {reader_review.get('status', 'n/a')}")
            selected_index = reader_review.get("selected_solution_index")
            if selected_index:
                print(f"  - Selected solution: #{selected_index}")
            selected = reader_review.get("selected_solution", {})
            if isinstance(selected, dict):
                for lib_key, version in list(selected.items())[:10]:
                    print(f"  - {lib_key} -> {version}")
            why_selected = reader_review.get("why_selected")
            if why_selected:
                print(f"  - Why: {shorten(str(why_selected), 220)}")

    print()
    print(color_text("Done.", "green", True))

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MYGRATE live dependency upgrade CLI")
    parser.add_argument("--path", type=str, default=str(DEFAULT_PROJECT_PATH), help="Path to the Java project")
    parser.add_argument("--target-java", type=str, default=DEFAULT_TARGET_JAVA, help="Target Java version")
    parser.add_argument("--max-versions", type=int, default=DEFAULT_MAX_VERSIONS, help="Max versions to scan per library")
    parser.add_argument("--max-solutions", type=int, default=DEFAULT_MAX_SOLUTIONS, help="Max solutions to return")
    parser.add_argument("--smoke-top-k", type=int, default=DEFAULT_SMOKE_TOP_K, help="Smoke-test the top K solutions")
    parser.add_argument("--no-clear", action="store_true", help="Disable live screen refresh")
    return parser


def main() -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    if not Path(args.path).exists():
        print(color_text(f"Project path not found: {args.path}", "red", True))
        return 1

    try:
        run_pipeline(
            project_path=args.path,
            target_java=args.target_java,
            max_versions=args.max_versions,
            max_solutions=args.max_solutions,
            smoke_top_k=args.smoke_top_k,
            no_clear=args.no_clear,
        )
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as exc:
        print(color_text(f"Unhandled error: {exc}", "red", True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
