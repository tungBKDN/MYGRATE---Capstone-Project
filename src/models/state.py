import operator
from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from src.models.schemas import MigrationTask

class GraphState(TypedDict):
    """
    Global State for the Multi-Agent workflow.
    """
    # Core project info
    project_path: str
    
    # User Requirements (Step 2)
    source_framework: Optional[str]
    source_version: Optional[str]
    target_framework: Optional[str]
    target_version: Optional[str]
    
    # Analysis & Feasibility (Step 1 & 3)
    indexed_files: Annotated[list[str], operator.add]
    dependencies: Annotated[list[str], operator.add]
    feasibility_report: Optional[str]
    compatibility_matrix: dict
    
    # Migration progress
    migration_tasks: Annotated[list[MigrationTask], operator.add]
    human_approved: bool
    
    # Routing (Supervisor)
    next: str
    
    # Message history for tool calling
    messages: Annotated[list[BaseMessage], operator.add]
