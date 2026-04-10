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
    parser.add_argument("--approve", action="store_true", help="Simulate human approval (set flag to True)")
    args = parser.parse_args()

    initial_state = {
        "project_path": args.path,
        "compatibility_matrix": {},
        "migration_tasks": [],
        "human_approved": args.approve
    }

    print("=" * 50)
    print(f"Starting MYGRATE workflow for project: {args.path}")
    print(f"Initial Human Approval Status: {args.approve}")
    print("=" * 50)

    # Initialize Langfuse CallbackHandler if credentials exist
    callbacks = []
    if os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"):
        print("-> [TELEMETRY] Langfuse Callback Handler is ENABLED.")
        from langfuse.callback import CallbackHandler
        langfuse_handler = CallbackHandler()
        callbacks.append(langfuse_handler)
    else:
        print("-> [TELEMETRY] Langfuse not configured. Please set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env.")

    config = {"callbacks": callbacks} if callbacks else {}

    # Invoke the compiled graph with initial state and config
    final_state = app.invoke(initial_state, config=config)

    print("=" * 50)
    print("Final State Result:")
    for key, value in final_state.items():
        print(f" - {key}: {value}")

if __name__ == "__main__":
    main()
