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
