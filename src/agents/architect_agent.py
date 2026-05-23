import os
import json
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langsmith import traceable
from langchain_core.messages import ToolMessage

# Dependency/version checking tools were removed. Architect now provides
# higher-level guidance but does not run version audits in this workspace.

class ArchitectAgent:
    """
    Architect Agent responsible for analyzing codebase and generating
    Compatibility Matrix and Upgrade Plans using a manual ReAct loop for maximum control.
    """
    def __init__(self, model_name: str = None):
        load_dotenv()
        if model_name is None:
            model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        api_key = os.getenv("GROQ_API_KEY")

        # Back to Llama-3.3 on Groq
        self.llm = ChatGroq(
            model_name=model_name,
            groq_api_key=api_key,
            temperature=0
        )

        # Tools removed: this agent will not call external dependency tooling.
        self.tools_list = []
        self.llm_with_tools = self.llm

        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'architect.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.architect_instructions = f.read()

    @traceable(name="Architect Migration Analysis")
    def run(self, instruction: str) -> str:
        print(f"-> [ARCHITECT] High-level analysis requested: {instruction[:80]}...")
        # The detailed dependency/version analysis tools have been removed from the
        # codebase. Return a short guidance summary and ask the user to re-run after
        # the Reader or provide manual dependency details.
        guidance = {
            "summary": "Dependency/version analysis features were removed.",
            "advice": "Run the Reader to extract project files, then provide explicit dependency lists or restore the dependency tools to perform automated audits.",
        }
        return json.dumps(guidance, ensure_ascii=False)
