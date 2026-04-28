import operator
from typing import TypedDict, Annotated, Optional
from langchain_core.messages import BaseMessage

class GlobalState(TypedDict):
    """
    Global State for the main workflow.
    ONLY the Supervisor and Human read/write this.
    Subagents are isolated and only receive text prompts.
    """
    # Core context
    project_path: str
    target_java_version: str # e.g., "17" or "21"
    
    # Chat history (Human <-> Supervisor)
    messages: Annotated[list[BaseMessage], operator.add]
    
    # Global context & summaries of completed work
    completed_tasks_summary: Annotated[list[str], operator.add]
    
    # Domain specific data
    dependencies: list[dict] # Extracted from pom.xml
    compatibility_matrix: dict # Result from Architect
    
    # Instructions to subagent (Supervisor -> Subagent)
    current_instruction: str
    
    # Result from subagent (Subagent -> Supervisor)
    last_subagent_result: str
    
    # Routing
    next_node: str
