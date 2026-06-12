import operator
from typing import TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage


class GlobalState(TypedDict):
    """
    Global State for the Mygrate workflow.

    Flow: Reader (discover) -> Architect (analyze) -> Translator (migrate)
    Each agent reads from state and returns an update dict.
    """

    # --- Core context ---
    project_path: str
    target_java_version: str
    project_type: Optional[str]

    # --- Chat history (Human <-> Supervisor) ---
    messages: Annotated[list[BaseMessage], operator.add]

    # --- Completed work summaries ---
    completed_tasks_summary: Annotated[list[str], operator.add]

    # --- Reader output ---
    dependencies: list

    # --- Architect output ---
    upgrade_report: Optional[dict]
    candidate_solutions: Optional[list]
    reader_review: Optional[dict]

    # --- jdeprscan output ---
    jdeprscan_report: Optional[dict]

    # --- Migration tasks ---
    migration_tasks: list

    # --- Routing ---
    current_instruction: str
    last_subagent_result: str
    next_node: str

