import json
import os
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from src.models.state import GlobalState

# Valid nodes the supervisor can route to
VALID_NODES = {"reader", "architect", "translator", "end"}


class SupervisorAgent:
    def __init__(self, model_name: str = None):
        load_dotenv()
        if model_name is None:
            model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        api_key = os.getenv("GROQ_API_KEY")
        self.llm = ChatGroq(model_name=model_name, groq_api_key=api_key, temperature=0)

    def process(self, state: GlobalState) -> dict:
        """
        Load system prompt, build context from state and invoke the LLM to decide the next node and instruction.

        Params:
        - state: GlobalState - the current global state of the agent system
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prompt_path = os.path.join(base_dir, "src", "prompts", "supervisor.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"System prompt file not found at {prompt_path}. Please ensure it exists.")

        # Build context from state
        deps_preview = ""
        dependencies = state.get("dependencies", [])
        if dependencies:
            deps_preview = ", ".join(
                f"{d.get('artifactId', '?')}:{d.get('version', '?')}"
                for d in dependencies[:10]
            )

        state_context = f"""
Project Path: {state.get('project_path', 'unknown')}
Project Type: {state.get('project_type', 'unknown')}
Target Java Version: {state.get('target_java_version', '17')}
Dependencies ({len(dependencies)}): {deps_preview or 'not yet scanned'}
Last Subagent Result (truncated): {str(state.get('last_subagent_result', ''))[:500]}
Completed Tasks: {state.get('completed_tasks_summary', [])}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Global State Context:\n{state_context}"),
        ]

        # Append chat history
        user_msgs = state.get("messages", [])
        if user_msgs:
            messages.extend(user_msgs[-10:])

        print("-> [SUPERVISOR] Analyzing state and deciding next step...")
        response = self.llm.invoke(messages)

        try:
            data = json.loads(response.content)
            next_node = data.get("next_node", "end").lower()
            instruction = data.get("current_instruction", "")
            summary = data.get("summary_update", "")
            response_text = data.get("response_to_user", "")
        except (json.JSONDecodeError, AttributeError):
            print("-> [SUPERVISOR] JSON parse failed. Falling back to end.")
            next_node = "end"
            instruction, summary, response_text = "", "", "Supervisor could not parse the response."

        # Validate next_node against allowed nodes
        if next_node not in VALID_NODES:
            print(f"-> [SUPERVISOR] Invalid node '{next_node}'. Falling back to end.")
            next_node = "end"

        update = {"next_node": next_node, "current_instruction": instruction}
        if summary:
            update["completed_tasks_summary"] = [summary]
        if response_text:
            update["messages"] = [AIMessage(content=response_text)]

        print(f"-> [SUPERVISOR] Routing to: {next_node}")
        return update


def get_supervisor_node(state: GlobalState):
    supervisor = SupervisorAgent()
    return supervisor.process(state)