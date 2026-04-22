from langgraph.graph import StateGraph, END
from src.models.state import GraphState
from src.agents.supervisor import get_supervisor_node

# --- Sub-agent Nodes ---

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.reader_agent import get_reader_node
from langgraph.prebuilt import ToolNode
from src.tools import list_project_structure, read_source_code, get_file_summary

# Define tools for the ToolNode
tools = [list_project_structure, read_source_code, get_file_summary]
tool_node = ToolNode(tools)

def should_continue(state: GraphState):
    """
    Decision function to determine if we should call tools or return to supervisor.
    """
    messages = state.get("messages")
    if messages and messages[-1].tool_calls:
        return "tools"
    return "supervisor"


def run_architect(state: GraphState) -> dict:
    """
    Step 3: Feasibility Analysis using Gemini.
    """
    from dotenv import load_dotenv
    load_dotenv()
    print("-> [NODE: Architect] Evaluating feasibility using Gemini...")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"feasibility_report": "Error: GOOGLE_API_KEY missing. Cannot evaluate feasibility."}

    # Load architect prompt from file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "src", "prompts", "architect.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key)
    prompt = prompt_template.format(
        source_framework=state.get('source_framework'),
        source_version=state.get('source_version'),
        target_framework=state.get('target_framework'),
        target_version=state.get('target_version'),
        dependencies=state.get('dependencies')
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"feasibility_report": response.content}

def human_approval_node(state: GraphState) -> dict:
    """
    Step 2: Collect requirements / Human-in-the-loop.
    """
    print("-> [NODE: Approval] Interaction required...")
    # In a real CLI, we would use input() or a UI component.
    # For now, we simulate approval if the project path is valid.
    approved = True if state.get("project_path") else False
    return {"human_approved": approved}

def run_translator(state: GraphState) -> dict:
    """
    Translation/Migration logic: performs the actual code updates.
    """
    print("-> [NODE: Translator] Executing code transformation...")
    return {"migration_tasks": []}

# --- Graph Construction ---

workflow = StateGraph(GraphState)

# 1. Add nodes
workflow.add_node("supervisor", get_supervisor_node)
workflow.add_node("reader", get_reader_node)
workflow.add_node("architect", run_architect)
workflow.add_node("approval", human_approval_node)
workflow.add_node("translator", run_translator)
workflow.add_node("tools", tool_node) # Node thực thi công cụ

# 2. Define edges
# The supervisor is the entry point
workflow.set_entry_point("supervisor")

# Supervisor decides which sub-agent to invoke
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next"],
    {
        "reader": "reader",
        "architect": "architect",
        "approval": "approval",
        "translator": "translator",
        "end": END
    }
)

# Reader logic: can call tools or return to supervisor
workflow.add_conditional_edges(
    "reader",
    should_continue,
    {
        "tools": "tools",
        "supervisor": "supervisor"
    }
)

# After tools are executed, always go back to the agent that called them
workflow.add_edge("tools", "reader")

# Each sub-agent returns to the supervisor after finishing its task
workflow.add_edge("architect", "supervisor")
workflow.add_edge("approval", "supervisor")
workflow.add_edge("translator", "supervisor")

# 3. Compile Graph
app = workflow.compile()
