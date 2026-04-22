import os
import argparse
from dotenv import load_dotenv
from src.workflow import app

def main():
    """
    Entry point to run the Mygrate LangGraph workflow via CLI.
    """
    load_dotenv()  # Load environment variables from .env

    parser = argparse.ArgumentParser(description="Mygrate Multi-Agent Workflow")
    parser.add_argument("--path", type=str, required=True, help="Path to the user's project directory to migrate")
    parser.add_argument("--source-fw", type=str, default="tensorflow", help="Source framework")
    parser.add_argument("--source-ver", type=str, default="2.15.0", help="Source version")
    parser.add_argument("--target-ver", type=str, default="2.16.1", help="Target version")
    parser.add_argument("--approve", action="store_true", help="Simulate human approval (set flag to True)")
    args = parser.parse_args()

    initial_state = {
        "project_path": args.path,
        "source_framework": args.source_fw,
        "source_version": args.source_ver,
        "target_framework": args.source_fw,
        "target_version": args.target_ver,
        "indexed_files": [],
        "dependencies": [],
        "feasibility_report": None,
        "compatibility_matrix": {},
        "migration_tasks": [],
        "human_approved": args.approve,
        "next": "supervisor"
    }

    print("=" * 50)
    print(f"Starting MYGRATE workflow for project: {args.path}")
    print(f"Goal: Upgrade {args.source_fw} from {args.source_ver} to {args.target_ver}")
    print("=" * 50)

    # Telemetry: LangSmith is enabled via environment variables (LANGSMITH_TRACING=true)
    if os.environ.get("LANGSMITH_API_KEY"):
        print("-> [TELEMETRY] LangSmith Tracing is ENABLED.")
    else:
        print("-> [TELEMETRY] LangSmith not configured. Set LANGSMITH_API_KEY in .env for tracing.")

    config = {}

    # Invoke the compiled graph with initial state and config
    final_state = app.invoke(initial_state, config=config)

    print("\n" + "=" * 50)
    print("Final State Result Summary:")
    print(f" - Feasibility: {final_state.get('feasibility_report')}")
    print(f" - Files Indexed: {len(final_state.get('indexed_files', []))}")
    print(f" - Tasks Generated: {len(final_state.get('migration_tasks', []))}")
    print("=" * 50)

if __name__ == "__main__":
    main()
