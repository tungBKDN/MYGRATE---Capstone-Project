import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from src.models.state import GlobalState
from src.agents.supervisor import get_supervisor_node
from src.agents.reader_agent import ReaderAgent

# --- Các Wrapper Node (Đảm bảo Subagents bị cách ly hoàn toàn với GlobalState) ---

def reader_node(state: GlobalState):
    """Lấy instruction từ Global State, gọi ReaderAgent độc lập."""
    instruction = state.get("current_instruction", "")
    project_path = state.get("project_path", "")
    full_instruction = f"Target Project: {project_path}\nNhiệm vụ: {instruction}"
    
    agent = ReaderAgent()
    result = agent.run(full_instruction)
    # Subagent không được ghi trực tiếp vào state, chỉ trả về biến trung gian
    return {"last_subagent_result": result}

def architect_node(state: GlobalState):
    """Lấy instruction từ Global State, gọi LLM Architect độc lập."""
    instruction = state.get("current_instruction", "")
    print("-> [ARCHITECT] Bắt đầu tác vụ độc lập...")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(base_dir, "src", "prompts", "architect.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        system_prompt = "You are the architect."
    
    api_key = os.getenv("GOOGLE_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", google_api_key=api_key)
    response = llm.invoke([
        ("system", system_prompt),
        ("user", instruction)
    ])
    return {"last_subagent_result": response.content}

def translator_node(state: GlobalState):
    """Wrapper: Tương tự cho Translator."""
    instruction = state.get("current_instruction", "")
    print("-> [TRANSLATOR] Bắt đầu tác vụ dịch code...")
    return {"last_subagent_result": "Đã thực hiện xong mô phỏng dịch code."}

# --- Xây dựng Graph ---

workflow = StateGraph(GlobalState)

workflow.add_node("supervisor", get_supervisor_node)
workflow.add_node("reader", reader_node)
workflow.add_node("architect", architect_node)
workflow.add_node("translator", translator_node)

workflow.set_entry_point("supervisor")

# Routing từ supervisor
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next_node"],
    {
        "reader": "reader",
        "architect": "architect",
        "translator": "translator",
        "end": END
    }
)

# Hub-and-Spoke: Sau khi làm xong, mọi subagent trả kết quả về cho supervisor
workflow.add_edge("reader", "supervisor")
workflow.add_edge("architect", "supervisor")
workflow.add_edge("translator", "supervisor")

# Khởi tạo Checkpointer cho phép Human-in-the-loop (Tạm dừng luồng)
memory = MemorySaver()

# Tạm dừng TRƯỚC KHI supervisor chạy. 
# Điều này cho phép user xem xét kết quả từ subagent trước đó, hoặc bổ sung yêu cầu trước khi supervisor phân việc.
app = workflow.compile(checkpointer=memory, interrupt_before=["supervisor"])
