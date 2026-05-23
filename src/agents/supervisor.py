import os
import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.models.state import GlobalState
from dotenv import load_dotenv

class SupervisorAgent:
    def __init__(self, model_name: str = None):
        load_dotenv()
        if model_name is None:
            model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        api_key = os.getenv("GROQ_API_KEY")
        # Groq doesn't support 'json_object' format natively like OpenAI/Gemini yet in all models,
        # but Llama 3 is very good at following JSON instructions.
        self.llm = ChatGroq(model_name=model_name, groq_api_key=api_key, temperature=0)

    def process(self, state: GlobalState) -> dict:
        """
        Quyết định xem sẽ nói chuyện với người dùng, hay giao việc cho subagent nào.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prompt_path = os.path.join(base_dir, "src", "prompts", "supervisor.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = "You are the supervisor."

        system_prompt += """
Bạn là Supervisor cho MYGRATE, hệ thống hỗ trợ nâng cấp phiên bản mã nguồn (Java, Python).
Bạn PHẢI trả về JSON có cấu trúc sau:
{
    "next_node": "Tên agent tiếp theo (reader, architect, translator) HOẶC 'end' nếu cần hỏi con người hoặc kết thúc",
    "current_instruction": "Câu lệnh MỚI dành cho subagent (nếu next_node không phải end). Ví dụ: 'Phân tích mã nguồn và trích xuất thông tin cần thiết'",
    "summary_update": "Tóm tắt kết quả của subagent trước (nếu có) để lưu vào bộ nhớ. Nếu không có gì đáng lưu, để rỗng",
    "response_to_user": "Câu trả lời gửi cho người dùng (nếu next_node là 'end' hoặc bạn muốn phản hồi họ)"
}
"""
        # Đóng gói ngữ cảnh cho LLM (Chỉ Supervisor mới thấy cái này)
        state_context = f"""
Project Path: {state.get('project_path')}
Completed Tasks Summaries: {state.get('completed_tasks_summary', [])}
Last Subagent Result: {state.get('last_subagent_result', 'Chưa có')}
"""

        messages = [SystemMessage(content=system_prompt)]
        messages.append(HumanMessage(content=f"Global State Context:\n{state_context}"))

        # Thêm lịch sử trò chuyện với con người
        user_msgs = state.get("messages", [])
        if user_msgs:
            messages.extend(user_msgs)

        print("-> [SUPERVISOR] Phân tích Global State và yêu cầu từ User...")
        response = self.llm.invoke(messages)

        try:
            data = json.loads(response.content)
            next_node = data.get("next_node", "end").lower()
            instruction = data.get("current_instruction", "")
            summary = data.get("summary_update", "")
            response_text = data.get("response_to_user", "")
        except:
            print("-> [SUPERVISOR] Lỗi Parse JSON. Trả luồng về end.")
            next_node = "end"
            instruction, summary, response_text = "", "", "Lỗi xử lý JSON từ Supervisor."

        update = {"next_node": next_node, "current_instruction": instruction}
        if summary:
            update["completed_tasks_summary"] = [summary]
        if response_text:
            update["messages"] = [AIMessage(content=response_text)]

        print(f"-> [SUPERVISOR] Quyết định gọi: {next_node}")
        return update

def get_supervisor_node(state: GlobalState):
    supervisor = SupervisorAgent()
    return supervisor.process(state)
