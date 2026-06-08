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
    source_framework: Optional[str]
    source_version: Optional[str]
    target_framework: Optional[str]
    target_version: Optional[str]

    # --- Chat history (Human <-> Supervisor) ---
    messages: Annotated[list[BaseMessage], operator.add]

    # --- Completed work summaries ---
    completed_tasks_summary: Annotated[list[str], operator.add]

    # --- Reader output ---
    pom_data: Optional[dict]
    dependencies: list
    index_report: Optional[dict]

    # --- Architect output ---
    upgrade_report: Optional[dict]
    candidate_solutions: Optional[list]
    compatibility_matrix: dict
    reader_review: Optional[dict]

    # --- jdeprscan output ---
    jdeprscan_report: Optional[dict]

    # --- Migration tasks ---
    migration_tasks: list

    # --- Routing ---
    current_instruction: str
    last_subagent_result: str
    next_node: str
