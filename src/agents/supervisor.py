from typing import Literal
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.models.state import GraphState

from dotenv import load_dotenv

class SupervisorAgent:
    """
    Supervisor Agent: The brain of the system.
    Uses Google Gemini to decide which sub-agent should work next.
    """

    def __init__(self, model_name: str = "gemini-flash-latest"):
        load_dotenv() # Tự động nạp API Key và cấu hình LangSmith
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("WARNING: GOOGLE_API_KEY not found. Using simple logic for supervisor.")
            self.llm = None
        else:
            self.llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)

    def route(self, state: GraphState) -> Literal["reader", "architect", "translator", "approval", "end"]:
        """
        Routing logic to determine the next agent.
        """
        if not self.llm:
            # Fallback to simple logic
            if not state.get("indexed_files"): return "reader"
            if not state.get("feasibility_report"): return "architect"
            if not state.get("human_approved"): return "approval"
            if not state.get("migration_tasks"): return "translator"
            return "end"

        # Load system prompt from file
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prompt_path = os.path.join(base_dir, "src", "prompts", "supervisor.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()

        state_str = (
            f"Indexed files: {state.get('indexed_files')}\n"
            f"Feasibility Report: {state.get('feasibility_report')}\n"
            f"Approved: {state.get('human_approved')}\n"
            f"Migration Tasks: {state.get('migration_tasks')}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Current State:\n{state_str}")
        ]

        response = self.llm.invoke(messages)
        content = response.content
        
        # Robustly extract text content from the LLM response
        if isinstance(content, list):
            # If it's a list, it might be a list of dicts (parts) or strings
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
            content = "".join(text_parts)
        elif isinstance(content, dict) and "text" in content:
            content = content["text"]
        
        next_agent = str(content).strip().lower()
        
        # Validation
        valid_agents = ["reader", "architect", "translator", "approval", "end"]
        if next_agent not in valid_agents:
            print(f"DEBUG: LLM returned invalid agent '{next_agent}'. Defaulting to end.")
            return "end"
            
        return next_agent

def get_supervisor_node(state: GraphState):
    """
    Node function for LangGraph to invoke the supervisor logic.
    """
    supervisor = SupervisorAgent()
    next_agent = supervisor.route(state)
    print(f"-> [SUPERVISOR] Next agent: {next_agent}")
    return {"next": next_agent}
