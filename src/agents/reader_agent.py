import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from src.tools import list_project_structure, read_source_code, get_file_summary
from dotenv import load_dotenv

class ReaderAgent:
    """
    Isolated Reader Agent. 
    It is a standalone ReAct Agent that takes a prompt, uses tools, and returns a string.
    Nó KHÔNG nhận GlobalState.
    """
    def __init__(self, model_name: str = "gemini-flash-latest"):
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
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
