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
