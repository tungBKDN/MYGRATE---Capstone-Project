import json
import os

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.models.state import GlobalState
from src.agents.supervisor import get_supervisor_node
from src.agents.reader_agent import ReaderAgent
from src.agents.architect_agent import ArchitectAgent
from src.agents.translator_agent import TranslatorAgent


# --- Wrapper Nodes ---

def reader_node(state: GlobalState):
    """Reader: index codebase, parse POM, return project info + dependencies."""
    project_path = state.get("project_path", "")
    target_java = state.get("target_java_version", "17")

    full_instruction = (
        f"Target Project: {project_path}\n"
        f"Target Java Version: {target_java}\n"
        f"Nhiệm vụ: Index the codebase and extract dependencies."
    )

    agent = ReaderAgent()
    result = agent.run(full_instruction)
    update = {"last_subagent_result": result}

    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict):
            if parsed.get("project_type"):
                update["project_type"] = parsed.get("project_type")
            if parsed.get("dependencies"):
                update["dependencies"] = parsed.get("dependencies")
            if parsed.get("pom_data"):
                update["pom_data"] = parsed.get("pom_data")
            if parsed.get("index_summary"):
                update["index_report"] = parsed.get("index_summary")
    except Exception:
        pass

    return update


def architect_node(state: GlobalState):
    """Architect: run full 7-step dependency pipeline."""
    dependencies = state.get("dependencies", [])
    target_java = state.get("target_java_version", "17")

    full_instruction = (
        f"Dependencies: {json.dumps(dependencies)}\n"
        f"Target Java Version: {target_java}\n"
        f"Nhiệm vụ: Run the full upgrade pipeline to find compatible combinations."
    )

    agent = ArchitectAgent()
    result = agent.run(full_instruction)
    update = {"last_subagent_result": result}

    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict):
            if parsed.get("solutions"):
                update["candidate_solutions"] = parsed.get("solutions")
            if parsed.get("smoke_test_results"):
                update["upgrade_report"] = parsed
            if parsed.get("conflict_edges") is not None:
                update["compatibility_matrix"] = parsed.get("conflict_edges", [])
    except Exception:
        pass

    return update



def translator_node(state: GlobalState):
    """Translator: run jdeprscan pipeline first, then apply code transformations."""
    instruction_payload = {
        "project_path": state.get("project_path", ""),
        "target_java_version": state.get("target_java_version", "17"),
        "project_type": state.get("project_type"),
        "current_instruction": state.get("current_instruction", ""),
        "migration_tasks": state.get("migration_tasks", []),
        "dependencies": state.get("dependencies", []),
        "pom_data": state.get("pom_data"),
        "index_report": state.get("index_report"),
        "upgrade_report": state.get("upgrade_report"),
        "candidate_solutions": state.get("candidate_solutions"),
        "reader_review": state.get("reader_review"),
        "compatibility_matrix": state.get("compatibility_matrix", {}),
        "jdeprscan_report": state.get("jdeprscan_report"),
    }
    agent = TranslatorAgent()
    result = agent.run(json.dumps(instruction_payload, ensure_ascii=False, indent=2, default=str))

    update = {"last_subagent_result": result}

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
    workflow.add_node("reader", reader_node)
    workflow.add_node("architect", architect_node)
    workflow.add_node("translator", translator_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x["next_node"],
        {
            "reader": "reader",
            "architect": "architect",
            "translator": "translator",
            "end": END,
        },
    )

    workflow.add_edge("reader", "supervisor")
    workflow.add_edge("architect", "supervisor")
    workflow.add_edge("translator", "supervisor")

    if interrupt:
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory, interrupt_before=["supervisor"])
    else:
        return workflow.compile()


# Default: human-in-the-loop mode
app = build_app(interrupt=True)
