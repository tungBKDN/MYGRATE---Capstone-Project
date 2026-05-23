import os
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.workflow import app


def run_with_workflow(thread_id: str = "mygrate_orch_thread"):
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "project_path": "freshbrew_data/cantor",
        "target_java_version": "17",
        "messages": [],
        "completed_tasks_summary": [],
        "dependencies": [],
        "compatibility_matrix": {},
        "migration_tasks": [],
        "current_instruction": "Quét dự án và sinh ma trận tương thích",
        "last_subagent_result": "",
        "next_node": "supervisor"
    }

    try:
        app.invoke(initial_state, config=config)
        print("[+] Workflow invoked via app.invoke. Checkpointed state available.")
        # auto-run routed subagents until end
        while True:
            state_val = app.get_state(config).values
            next_node = state_val.get("next_node", "end")
            if next_node == "end":
                break
            print(f"---> Running routed node: {next_node}")
            app.invoke(None, config=config)

        latest = app.get_state(config).values
        last = latest.get("last_subagent_result", "")
        if last:
            print("[+] Supervisor completed. last_subagent_result available.")
        return True
    except Exception as e:
        print("[!] Workflow invoke failed:", e)
        return False


if __name__ == '__main__':
    # Try run via orchestrator workflow first. If fails, fallback to local deterministic pipeline.
    ok = run_with_workflow()
    if not ok:
        print("Falling back to deterministic pipeline (run_local_pipeline.py)")
        os.execv(sys.executable, [sys.executable, "scripts/run_local_pipeline.py", "freshbrew_data/cantor"])
