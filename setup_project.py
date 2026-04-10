import os
import pathlib

def create_file(path: str, content: str = ""):
    pathobj = pathlib.Path(path)
    pathobj.parent.mkdir(parents=True, exist_ok=True)
    with open(pathobj, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"Created/Updated: {path}")

def setup():
    # 1. Required directories
    dirs = [
        "rules/python",
        "rules/java",
        "src/agents",
        "src/core",
        "src/models",
        "src/utils",
        "tests"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"Created directory: {d}")

    # __init__.py files
    init_paths = [
        "src/__init__.py",
        "src/agents/__init__.py",
        "src/core/__init__.py",
        "src/models/__init__.py",
        "src/utils/__init__.py",
        "tests/__init__.py",
    ]
    for p in init_paths:
        create_file(p, "")

    # Basic dummy/boilerplate files
    empty_files = [
        "src/agents/architect_agent.py",
        "src/agents/reader_agent.py",
        "src/agents/translator_agent.py",
        "src/core/tree_sitter_engine.py",
        "src/utils/file_io.py",
        "src/utils/logger.py"
    ]
    for p in empty_files:
        create_file(p, "\"\"\"Placeholder module.\"\"\"\n")

    # 1. requirements.txt
    reqs = """
langchain
langgraph
tree-sitter
tree-sitter-python
tree-sitter-java
pydantic
"""
    create_file("requirements.txt", reqs)

    # 2. src/models/schemas.py
    schemas = '''
from pydantic import BaseModel

class MigrationTask(BaseModel):
    """
    Data Transfer Object representing a single code migration task.
    """
    file_path: str
    rule_id: str
    original_code: str
    start_byte: int
    end_byte: int
    llm_suggested_code: str | None = None
'''
    create_file("src/models/schemas.py", schemas)

    # 3. src/models/state.py
    state = '''
import operator
from typing import TypedDict, Annotated
from src.models.schemas import MigrationTask

class GraphState(TypedDict):
    """
    Global State for the Multi-Agent workflow.
    """
    project_path: str
    compatibility_matrix: dict
    # Use the operator.add reducer to let LangGraph automatically merge the list of tasks from nodes
    migration_tasks: Annotated[list[MigrationTask], operator.add]
    human_approved: bool
'''
    create_file("src/models/state.py", state)

    # 4. src/workflow.py
    workflow = '''
from langgraph.graph import StateGraph, END
from src.models.state import GraphState

def run_architect(state: GraphState) -> GraphState:
    """Architect Agent: Analyzes structure to generate compatibility matrix."""
    print("-> [NODE: Architect] Executing...")
    return {"compatibility_matrix": {"analyzed": True}}

def run_reader(state: GraphState) -> GraphState:
    """Reader Agent: Parses syntax trees and identifies nodes for migration."""
    print("-> [NODE: Reader] Executing...")
    return {"migration_tasks": []}

def human_approval_mock(state: GraphState) -> GraphState:
    """Human-in-the-Loop Node: Mock for waiting engineer's approval."""
    print("-> [NODE: Human Approval] Executing...")
    # Does not change the human_approved state here, acts as a passthrough based on initial input.
    return state

def run_translator(state: GraphState) -> GraphState:
    """Translator Agent: Uses LLM to translate code blocks to modern syntax."""
    print("-> [NODE: Translator] Executing...")
    return state

def routing_after_approval(state: GraphState) -> str:
    """Conditional Edge logic resolving path post-approval."""
    if state.get("human_approved", False):
        print("   [ROUTING] Approved! Proceeding to Translator.")
        return "translator"
    else:
        print("   [ROUTING] Rejected! Stopping execution.")
        return "end"

# Initialize StateGraph
workflow = StateGraph(GraphState)

# Define nodes
workflow.add_node("architect", run_architect)
workflow.add_node("reader", run_reader)
workflow.add_node("approval", human_approval_mock)
workflow.add_node("translator", run_translator)

# Define edges
workflow.set_entry_point("architect")
workflow.add_edge("architect", "reader")
workflow.add_edge("reader", "approval")

# Conditional edges from Human Approval
workflow.add_conditional_edges(
    "approval",
    routing_after_approval,
    {
        "translator": "translator",
        "end": END
    }
)

workflow.add_edge("translator", END)

# Compile Graph
app = workflow.compile()
'''
    create_file("src/workflow.py", workflow)

    # 5. src/main.py
    main = '''
import argparse
from src.workflow import app

def main():
    """
    Entry point to run the Mygrate LangGraph workflow via CLI.
    """
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

    # Invoke the compiled graph with initial state
    final_state = app.invoke(initial_state)

    print("=" * 50)
    print("Final State Result:")
    for key, value in final_state.items():
        print(f" - {key}: {value}")

if __name__ == "__main__":
    main()
'''
    create_file("src/main.py", main)

if __name__ == "__main__":
    setup()
    print("\\n🚀 Scaffolded Project Successfully!")
