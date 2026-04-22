import os
import json
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from src.tools.file_system import list_project_structure, read_source_code, get_file_summary
from src.models.state import GraphState
from dotenv import load_dotenv

class ReaderAgent:
    """
    Reader Agent: The explorer.
    Uses file system tools to discover project structure and dependencies.
    """

    def __init__(self, model_name: str = "gemini-flash-latest"):
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
        self.tools = [list_project_structure, read_source_code, get_file_summary]
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def run(self, state: GraphState) -> Dict[str, Any]:
        """
        Executes the discovery task with correct message sequence for Gemini.
        """
        project_path = state.get("project_path")
        history = state.get("messages", [])
        
        # Load system prompt
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prompt_path = os.path.join(base_dir, "src", "prompts", "reader.md")
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()

        system_prompt += (
            "\n\nIMPORTANT: When you have finished exploring and have the list of files and dependencies, "
            "provide your final answer in JSON format at the end of your message, like this:\n"
            "FINAL_RESULT: {\"indexed_files\": [\"path/to/file1\", ...], \"dependencies\": [\"dep1\", ...]}"
        )

        # Xây dựng danh sách tin nhắn đúng chuẩn Gemini:
        # [System, Human (lần đầu), AI, Tool, AI, Tool...]
        messages = [SystemMessage(content=system_prompt)]
        
        first_question = HumanMessage(content=f"Please analyze the project at path: {project_path}")
        
        # Nếu chưa có lịch sử, chúng ta bắt đầu bằng câu hỏi đầu tiên
        if not history:
            messages.append(first_question)
            new_messages_to_add = [first_question]
        else:
            # Nếu đã có lịch sử, lịch sử đó CẦN phải bắt đầu bằng HumanMessage 
            # (Trong LangGraph, messages sẽ được cộng dồn vào state)
            messages.extend(history)
            new_messages_to_add = []

        # Gọi LLM
        response = self.llm_with_tools.invoke(messages)
        
        # Lưu cả câu hỏi (nếu là lần đầu) và câu trả lời của AI vào state
        new_messages_to_add.append(response)
        update = {"messages": new_messages_to_add}
        
        # Kiểm tra nếu đã hoàn thành
        if not response.tool_calls and "FINAL_RESULT:" in response.content:
            try:
                result_part = response.content.split("FINAL_RESULT:")[1].strip()
                data = json.loads(result_part)
                update["indexed_files"] = data.get("indexed_files", [])
                update["dependencies"] = data.get("dependencies", [])
            except Exception as e:
                print(f"-> [READER] Error parsing final result: {e}")

        return update

def get_reader_node(state: GraphState):
    return ReaderAgent().run(state)
