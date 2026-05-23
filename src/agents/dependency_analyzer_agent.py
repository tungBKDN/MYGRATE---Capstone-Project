import os
import json
from typing import List, Any
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
from src.tools.java_dependency_tools import (
    fetch_candidate_versions,
    heuristic_version_filter,
    static_compatibility_check,
    solve_transitive_constraints,
    runtime_smoke_test
)

class DependencyAnalyzerAgent:
    """Agent Dependency Analyzer sử dụng Dữ liệu thực từ Maven/deps.dev cho Java (và sẽ hỗ trợ Python)."""
    
    def __init__(self, language: str = "java", model_name: str = ""):
        load_dotenv()
        self.language = language.lower()
        if not model_name:
            model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        api_key = os.getenv("GROQ_API_KEY")
        
        self.llm = ChatGroq(
            model=model_name, 
            groq_api_key=api_key, 
            temperature=0
        )
        
        self.tools_list: List[Any] = []
        if self.language == "java":
            self.tools_list = [
                fetch_candidate_versions,
                heuristic_version_filter,
                static_compatibility_check,
                solve_transitive_constraints,
                runtime_smoke_test
            ]
        elif self.language == "python":
            from src.tools.python_dependency_tools import (
                parse_python_dependencies,
                get_latest_pypi_version,
                check_python_compatibility
            )
            self.tools_list = [
                parse_python_dependencies,
                get_latest_pypi_version,
                check_python_compatibility
            ]
        else:
            raise ValueError(f"Unsupported language: {self.language}")
            
        self.llm_with_tools = self.llm.bind_tools(self.tools_list)
        
        if self.language == "java":
            pipeline_desc = """Follow this pipeline for Java:
1. Use fetch_candidate_versions to get all versions.
2. Use heuristic_version_filter to narrow down candidates.
3. Use static_compatibility_check for bytecode validation via physical JAR stream scanning.
4. If multiple dependencies exist, use solve_transitive_constraints to find combinations (this automatically runs steps 1,2,3 for all given dependencies and resolves them).
5. Use runtime_smoke_test (compile check) to verify the top combination."""
        else:
            pipeline_desc = """Follow this pipeline for Python:
1. Use parse_python_dependencies to extract package requirements.
2. Use get_latest_pypi_version to find latest versions.
3. Use check_python_compatibility to verify package compatibility with the target Python version."""

        self.system_prompt = f"""
You are the Dependency Analyzer Agent for {self.language.upper()}.
Your job is to find compatible library versions for a target environment and resolve transitive conflicts using REAL data.
{pipeline_desc}

Return your final answer with the verified dependencies and validation report details.
"""
    def run(self, instruction: str) -> str:
        print(f"-> [DEPENDENCY ANALYZER] Running pipeline for: {instruction[:50]}...")
        
        messages: List[Any] = [
            ("system", self.system_prompt),
            ("user", instruction)
        ]
        
        # ReAct Loop
        for i in range(10):
            response = self.llm_with_tools.invoke(messages)
            messages.append(response)
            
            if not response.tool_calls:
                return response.content
                
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                print(f"   [EXECUTE TOOL] {tool_name}({tool_args})")
                
                tool_func = next((t for t in self.tools_list if getattr(t, 'name', getattr(t, '__name__', None)) == tool_name), None)
                if tool_func:
                    try:
                        if hasattr(tool_func, "invoke"):
                            result = tool_func.invoke(tool_args)
                        else:
                            result = tool_func(**tool_args)
                        messages.append(ToolMessage(
                            tool_call_id=tool_call["id"],
                            name=tool_name,
                            content=json.dumps(result) if isinstance(result, dict) or isinstance(result, list) else str(result)
                        ))
                    except Exception as e:
                        messages.append(ToolMessage(
                            tool_call_id=tool_call["id"],
                            name=tool_name,
                            content=f"Error: {str(e)}"
                        ))
                else:
                    messages.append(ToolMessage(
                        tool_call_id=tool_call["id"],
                        name=tool_name,
                        content="Error: Tool not found."
                    ))
                    
        return messages[-1].content
