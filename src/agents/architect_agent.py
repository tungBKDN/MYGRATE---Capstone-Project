import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from langgraph.prebuilt import create_react_agent
from src.tools import (
    parse_maven_dependencies, 
    get_latest_version, 
    list_all_versions,
    get_transitive_dependencies,
    check_java_compatibility,
    parse_python_dependencies,
    get_latest_pypi_version,
    check_python_compatibility,
    list_project_structure,
    index_project_structure,
    find_main_build_file
)
from dotenv import load_dotenv

class ArchitectAgent:
    """
    Architect Agent responsible for analyzing codebase and generating 
    Compatibility Matrix and Upgrade Plans.
    """
    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        self.llm = ChatGroq(model_name=model_name, groq_api_key=api_key, temperature=0)
        self.tools = [
            parse_maven_dependencies, 
            get_latest_version, 
            list_all_versions,
            get_transitive_dependencies,
            check_java_compatibility, 
            parse_python_dependencies,
            get_latest_pypi_version,
            check_python_compatibility,
            list_project_structure,
            index_project_structure,
            find_main_build_file
        ]
        self.agent = create_react_agent(self.llm, self.tools)

    def run(self, instruction: str) -> str:
        print(f"-> [ARCHITECT] Analyzing project: {instruction[:50]}...")
        response = self.agent.invoke({"messages": [
            ("system", """You are a highly precise and paranoid software architect. 
            ZERO TOLERANCE RULES:
            1. IDENTIFY TARGET VERSION: Identify the target Java version (e.g., 17, 21, 22) from the user's instruction. Pass it to `check_java_compatibility`.
            2. NO EXTERNAL LIBRARIES: ONLY report on libraries explicitly found in the `parse_maven_dependencies` output. If a library is NOT in the POM, DO NOT mention it. Mentioning libraries like "Spring" or "Hibernate" when they are not in the project is a CRITICAL FAILURE.
            3. STOP ON ABNORMAL DATA: If ANY tool returns an error or empty result, STOP and report it.
            4. NO HALLUCINATION: Never invent version numbers or compatibility status.
            5. DATA VERIFICATION: Every claim must be backed by tool output.
            Your primary goal is to ensure 100% data integrity. If in doubt, STOP and report.
            """),
            ("user", instruction)
        ]})
        return response["messages"][-1].content
