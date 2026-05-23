import operator
from typing import TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage

class GlobalState(TypedDict):
    """
    Global State for the main workflow.
    """
    # Core context
    project_path: str
    target_java_version: str # e.g., "17" or "21"
    source_framework: Optional[str]
    source_version: Optional[str]
    target_framework: Optional[str]
    target_version: Optional[str]

    # Chat history (Human <-> Supervisor)
    messages: Annotated[list[BaseMessage], operator.add]

    # Global context & summaries of completed work
    completed_tasks_summary: Annotated[list[str], operator.add]

    # Domain specific data (dependency analysis removed)

    # Instructions to subagent (Supervisor -> Subagent)
    current_instruction: str

    # Result from subagent (Subagent -> Supervisor)
    last_subagent_result: str

    # Routing
    next_node: str
