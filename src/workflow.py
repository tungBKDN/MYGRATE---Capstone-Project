import json
import os
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.models.state import GlobalState
from src.agents.supervisor import get_supervisor_node
from src.agents.reader_agent import ReaderAgent
from src.agents.architect_agent import ArchitectAgent
from src.agents.translator_agent import TranslatorAgent


# --- Wrapper Nodes ---

def architect_node(state: GlobalState):
    """Architect: run initial project index (if not done yet), then run the full 7-step dependency pipeline and candidate review."""
    project_path = state.get("project_path", "")
    target_java = state.get("target_java_version", "17")
    
    # 1. Run lightweight index programmatically if dependencies are missing
    dependencies = state.get("dependencies", [])
    project_type = state.get("project_type")
    
    if not dependencies or not project_type:
        from src.tools.maven_upgrade_tools import index_java_project
        print(f"-> [ARCHITECT] Running programmatic initial project scan...")
        scan_res = index_java_project(project_path)
        if scan_res.get("status") == "ok":
            dependencies = scan_res.get("dependencies", [])
            project_type = scan_res.get("project_type", "java")
        else:
            dependencies = []
            project_type = "java"

    # 2. Run the full 7-step upgrade analysis
    full_instruction = (
        f"Dependencies: {json.dumps(dependencies)}\n"
        f"Target Java Version: {target_java}\n"
        f"Nhiệm vụ: Run the full upgrade pipeline to find compatible combinations."
    )

    agent = ArchitectAgent()
    result = agent.run(full_instruction)
    
    # Base updates
    update = {
        "last_subagent_result": result,
        "project_type": project_type,
        "dependencies": dependencies
    }

    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict):
            if parsed.get("solutions"):
                update["candidate_solutions"] = parsed.get("solutions")
            update["upgrade_report"] = parsed

            # 3. Perform final candidate review programmatically
            try:
                from src.agents.reader_agent import ReaderAgent
                payload = {
                    "project_path": project_path,
                    "project_type": project_type,
                    "target_java": target_java,
                    "dependencies": dependencies,
                    "candidates": parsed.get("candidates", {}),
                    "solutions": parsed.get("solutions", []),
                    "smoke_test_results": parsed.get("smoke_test_results", []),
                    "solver_method": parsed.get("solver_method", "z3"),
                    "step3_reports": {
                        k: {"analysis": {"compatibility_status": v.get("analysis", {}).get("compatibility_status")}}
                        for k, v in parsed.get("step3_reports", {}).items()
                        if isinstance(v, dict)
                    }
                }
                print(f"-> [ARCHITECT] Running final candidate review...")
                review_agent = ReaderAgent()
                review_res = review_agent.review_candidates(payload)
                update["reader_review"] = review_res
                
                # Write reports to artifacts folder
                artifacts_dir = Path(project_path) / "test" / "artifacts"
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                with open(artifacts_dir / "reader_review.json", "w", encoding="utf-8") as f:
                    json.dump(review_res, f, ensure_ascii=False, indent=2, default=str)
                md_content = review_res.get("markdown_report")
                if md_content:
                    with open(artifacts_dir / "reader_review.md", "w", encoding="utf-8") as f:
                        f.write(md_content)
            except Exception as e:
                print(f"Warning: Failed to run candidate review in Architect: {e}")
    except Exception as e:
        print(f"Warning: Failed to parse ArchitectAgent result: {e}")

    return update

def translator_node(state: GlobalState):
    """Translator: run jdeprscan pipeline first, then apply code transformations."""
    instruction_payload = {
        "project_path": state.get("project_path", ""),
        "target_java_version": state.get("target_java_version", "17"),
        "project_type": state.get("project_type"),
        "current_instruction": "APPLY: " + state.get("current_instruction", "") if not state.get("current_instruction", "").startswith("APPLY:") else state.get("current_instruction", ""),
        "migration_tasks": state.get("migration_tasks", []),
        "jdeprscan_report": state.get("jdeprscan_report"),
        "baseline_coverage": state.get("baseline_coverage", 0.0),
        "baseline_total_tests": state.get("baseline_total_tests", 0),
        "baseline_passed_tests": state.get("baseline_passed_tests", 0),
    }
    agent = TranslatorAgent()
    result = agent.run(json.dumps(instruction_payload, ensure_ascii=False, indent=2, default=str))

    # Always signal that the translator session has ended (success or deadlock).
    # The supervisor will fast-path to 'end' when it sees this flag, instead of
    # asking its LLM whether to call translator again.
    update = {"last_subagent_result": result, "translator_completed": True}

    # Extract jdeprscan report from translator result and store in state
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict) and parsed.get("jdeprscan"):
            update["jdeprscan_report"] = parsed["jdeprscan"]
    except Exception:
        pass

    return update


# --- Build Graph ---

def build_app(interrupt: bool = True):
    """Build the LangGraph workflow.

    Args:
        interrupt: If True, pause before each supervisor turn (human-in-the-loop).
                   If False, pipeline runs end-to-end without pauses (for testing/batch).
    """
    workflow = StateGraph(GlobalState)

    workflow.add_node("supervisor", get_supervisor_node)
    workflow.add_node("architect", architect_node)
    workflow.add_node("translator", translator_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x["next_node"],
        {
            "architect": "architect",
            "translator": "translator",
            "end": END,
            "supervisor": "supervisor",
        },
    )

    workflow.add_edge("architect", "supervisor")
    workflow.add_edge("translator", "supervisor")

    if interrupt:
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory, interrupt_before=["supervisor"])
    else:
        return workflow.compile()


# Default: human-in-the-loop mode
app = build_app(interrupt=True)
