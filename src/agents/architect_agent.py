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
            STRICT INSTRUCTIONS:
            1. MANDATORY TOOL CALL: You MUST call `parse_maven_dependencies` first. Use ONLY its output.
            2. NO HALLUCINATION: If a library is not in the tool output, it DOES NOT EXIST.
            3. VERIFICATION LINKS: You MUST use the `verification_url` returned by `check_java_compatibility` for EVERY version in the matrix. DO NOT use links from your training data (e.g., mvnrepository.com).
            4. REPORT TEMPLATE:
               ## PROJECT: [ArtifactID]
               ### DIRECT DEPENDENCIES:
               - [GroupID]:[ArtifactID] (Current: [Version])
               ### DECISION MATRIX:
               | Library | Current | Latest | Compatible? | Verification Link |
               |---|---|---|---|---|
               | [A] | [V1] | [V2] | [Yes/No] | [URL] |
               ### TRANSITIVE ANALYSIS:
               - [A] -> [Transitive Libs]
               ### RECOMMENDATION:
               [Final Combination + Reason]
            Your primary goal is to ensure 100% data integrity. If in doubt, STOP and report.
            """),
            ("user", instruction)
        ]})
        return response["messages"][-1].content
