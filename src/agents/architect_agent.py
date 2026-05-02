import os
import json
import re
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langsmith import traceable

from src.tools import (
    parse_maven_dependencies, 
    get_latest_version, 
    list_all_versions,
    get_transitive_dependencies,
    check_java_compatibility, 
    batch_check_java_compatibility,
    parse_python_dependencies,
    get_latest_pypi_version,
    check_python_compatibility,
    list_project_structure,
    index_project_structure,
    find_main_build_file
)

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
        
        self.tools_list = [
            parse_maven_dependencies, get_latest_version, list_all_versions,
            get_transitive_dependencies, check_java_compatibility, 
            batch_check_java_compatibility,
            parse_python_dependencies, get_latest_pypi_version,
            check_python_compatibility, list_project_structure,
            index_project_structure, find_main_build_file
        ]
        
        self.llm_with_tools = self.llm.bind_tools(self.tools_list)
        
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'architect.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.architect_instructions = f.read()

    @traceable(name="Architect Migration Analysis")
    def run(self, instruction: str) -> str:
        print(f"-> [ARCHITECT] Deep Audit (Llama Mode): {instruction[:50]}...")
        
        messages = [
            ("system", f"You are a dependency analyzer. Follow these instructions strictly:\n\n{self.architect_instructions}"),
            ("user", instruction)
        ]
        
        has_called_tools = False
        libs_found = []
        versions_tested_count = {}
        
        # Max steps to ensure full matrix analysis
        for i in range(15):
            print(f"   [STEP {i+1}] LLM reasoning...")
            try:
                response = self.llm_with_tools.invoke(messages)
            except Exception as e:
                if "429" in str(e) or "rate_limit_exceeded" in str(e).lower():
                    print("\n" + "!"*50)
                    print("!!! RATE LIMIT REACHED (429) !!!")
                    # Try to extract and print headers for the user to see the condition
                    if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                        headers = e.response.headers
                        print("--- Rate Limit Details ---")
                        for key in ['x-ratelimit-limit-tokens', 'x-ratelimit-remaining-tokens', 'x-ratelimit-reset-tokens', 'x-ratelimit-reset-requests']:
                            if key in headers:
                                print(f"{key}: {headers[key]}")
                    print("!"*50 + "\n")
                raise e
            
            messages.append(response)
            
            if not response.tool_calls:
                # DEEP AUDIT ENFORCEMENT:
                needs_more = False
                # Ensure we have at least 3 compatibility checks per library found
                for lib in libs_found:
                    if versions_tested_count.get(lib, 0) < 3:
                        needs_more = True
                        break
                
                if needs_more and i < 8:
                    print(f"   [SYSTEM] Matrix incomplete. Forcing more version checks for {libs_found}.")
                    messages.append(("user", f"Matrix incomplete. You must test at least 3 versions for EACH library in {libs_found}. TIP: Use batch_check_java_compatibility to test multiple versions at once and save tokens."))
                    continue
                
                if not has_called_tools and i < 2:
                    messages.append(("user", "You MUST use tools. Call parse_maven_dependencies first."))
                    continue
                
                if "```json" not in response.content:
                    print("   [SYSTEM] Forcing final report format...")
                    schema_instruction = """
Analysis complete. Generate the FINAL REPORT now.
- **Markdown Section**: In the user's language. Include a table with columns: Library, Current (Version), Target (Version), Status.
- **JSON Section**: Valid JSON in a code block with:
  - `recommendations`: { "group:artifact": { "action": "upgrade" (if target != current) or "keep", "current_version", "target_version", "candidates_tested": ["v1", "v2"], "score", "reasoning" } }
  - `cross_compatibility`: [ { "lib1": "group:artifact", "lib2": "group:artifact", "status": "safe" | "warning" | "conflict", "reason": "..." } ]
  - `visualization_data`: { "nodes": [ { "id", "label": "name (version)", "version", "status" } ], "edges": [ { "source", "target", "type" } ] }
- **CRITICAL**: If `target_version` is different from `current_version`, the `action` MUST be "upgrade".
"""
                    messages.append(("user", schema_instruction))
                    final_response = self.llm.invoke(messages)
                    return final_response.content
                
                return response.content
            
            has_called_tools = True
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                print(f"   [EXECUTE TOOL] {tool_name}({tool_args})")
                
                tool_func = next((t for t in self.tools_list if getattr(t, 'name', getattr(t, '__name__', None)) == tool_name), None)
                if tool_func:
                    try:
                        result = tool_func(**tool_args)
                        
                        # Fix: Robust result parsing for libs_found
                        parsed_result = result
                        if isinstance(result, str):
                            try:
                                parsed_result = json.loads(result)
                            except:
                                pass
                        
                        if tool_name == "parse_maven_dependencies" and isinstance(parsed_result, dict):
                            deps = parsed_result.get('dependencies', [])
                            libs_found = [f"{d['groupId']}:{d['artifactId']}" for d in deps if isinstance(d, dict) and 'groupId' in d]
                        
                        if tool_name == "check_java_compatibility":
                            lib_key = f"{tool_args.get('group_id')}:{tool_args.get('artifact_id')}"
                            versions_tested_count[lib_key] = versions_tested_count.get(lib_key, 0) + 1
                        
                        if tool_name == "batch_check_java_compatibility":
                            lib_key = f"{tool_args.get('group_id')}:{tool_args.get('artifact_id')}"
                            num_versions = len(tool_args.get('versions', []))
                            versions_tested_count[lib_key] = versions_tested_count.get(lib_key, 0) + num_versions

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_name,
                            "content": json.dumps(result) if isinstance(result, dict) else str(result)
                        })
                    except Exception as e:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_name,
                            "content": f"Error: {str(e)}"
                        })
                
        return messages[-1].content
