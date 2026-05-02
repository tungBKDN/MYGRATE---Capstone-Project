import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from src.tools import list_project_structure, read_source_code, get_file_summary
from dotenv import load_dotenv

class ReaderAgent:
    """
    Isolated Reader Agent. 
    It is a standalone ReAct Agent that takes a prompt, uses tools, and returns a string.
    Nó KHÔNG nhận GlobalState.
    """
    def __init__(self, model_name: str = None):
        load_dotenv()
        if model_name is None:
            model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        api_key = os.getenv("GROQ_API_KEY")
        self.llm = ChatGroq(model_name=model_name, groq_api_key=api_key)
        self.tools = [list_project_structure, read_source_code, get_file_summary]
        # create_react_agent đóng gói sẵn vòng lặp AI <-> Tools
        self.agent = create_react_agent(self.llm, self.tools)

    def run(self, instruction: str) -> str:
        """
        Takes an instruction string, executes tool-calling loop, returns final answer.
        """
        print(f"-> [READER] Bắt đầu tác vụ độc lập với lệnh: {instruction[:50]}...")
        response = self.agent.invoke({"messages": [("user", instruction)]})
        # Chỉ trả về nội dung text cuối cùng, hoàn toàn độc lập
        return response["messages"][-1].content
