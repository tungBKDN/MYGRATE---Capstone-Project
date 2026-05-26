import os
import argparse
import json

from dotenv import load_dotenv
from src.workflow import app


def main():
    """
    Entry point to run the Mygrate LangGraph workflow via CLI.

    Workflow: Reader (discover) -> Architect (analyze) -> Translator (migrate)
    """
    load_dotenv()

    parser = argparse.ArgumentParser(description="Mygrate Multi-Agent Workflow")
    parser.add_argument("--path", type=str, required=True, help="Path to the project directory")
    parser.add_argument("--target-java", type=str, default="17", help="Target Java version (e.g. 17, 21)")
    parser.add_argument("--approve", action="store_true", help="Simulate human approval (set flag to skip interrupts)")
    args = parser.parse_args()

    initial_state = {
        "project_path": args.path,
        "target_java_version": args.target_java,
        "project_type": None,
        "source_framework": None,
        "source_version": None,
        "target_framework": None,
        "target_version": None,
        "messages": [],
        "completed_tasks_summary": [],
        "pom_data": None,
        "dependencies": [],
        "index_report": None,
        "upgrade_report": None,
        "candidate_solutions": None,
        "compatibility_matrix": {},
        "reader_review": None,
        "migration_tasks": [],
        "current_instruction": "",
        "last_subagent_result": "",
        "next_node": "supervisor",
    }

    print("=" * 50)
    print(f"Starting MYGRATE workflow for project: {args.path}")
    print(f"Target Java: {args.target_java}")
    print("=" * 50)

    if os.environ.get("LANGSMITH_API_KEY"):
        print("-> [TELEMETRY] LangSmith Tracing is ENABLED.")
    else:
        print("-> [TELEMETRY] LangSmith not configured.")

    config = {}

    if args.approve:
        # Auto-approve: run without interrupts
        final_state = app.invoke(initial_state, config=config)
    else:
        # Human-in-the-loop: will pause before each supervisor turn
        final_state = app.invoke(initial_state, config=config)

    print("\n" + "=" * 50)
    print("Final State Result Summary:")
    print(f"  Project Type: {final_state.get('project_type', 'unknown')}")
    print(f"  Dependencies Found: {len(final_state.get('dependencies', []))}")

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
                report_path = parsed.get("report_path")
                if report_path:
                    print(f"  Report Path: {report_path}")
        except Exception:
            pass
    print("=" * 50)


if __name__ == "__main__":
    main()
