import os
from dotenv import load_dotenv
from src.agents.architect_agent import ArchitectAgent
from langchain_core.messages import HumanMessage

def test_cantor_analysis():
    load_dotenv()
    # Ensure GROQ_API_KEY is set
    if not os.getenv("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY not found in environment.")
        return

    project_path = "freshbrew_data/cantor"
    target_java = "17"
    
    agent = ArchitectAgent()
    
    instruction = f"""
    Thực hiện phân tích chuyên sâu cho dự án Java tại '{project_path}':
    1. Liệt kê toàn bộ phụ thuộc từ pom.xml.
    2. Với mỗi phụ thuộc, liệt kê TẤT CẢ các version khả thi có thể chạy trên Java {target_java}.
    3. Trích xuất phụ thuộc bắc cầu (transitive dependencies) của các version tiềm năng đó để kiểm tra chéo (cross-check) xem chúng có xung đột với nhau không.
    4. Vẽ một Ma trận quyết định (Decision Matrix) gồm: Bản hiện tại, Legacy nhất, Ổn định nhất, Mới nhất.
    5. Cảnh báo về 'Dependency Hell': Chỉ rõ các xung đột chéo giữa các thư viện.
    6. LỰA CHỌN TỔ HỢP TỐI ƯU: Đưa ra một bộ version duy nhất (ví dụ: Lib A: v1, Lib B: v2) mà bạn sẽ sử dụng để migrate, kèm theo lý giải tại sao đây là lựa chọn cân bằng nhất giữa 'rủi ro' và 'tính hiện đại'.
    """
    
    result = agent.run(instruction)
    
    print("\n" + "="*50)
    print("ARCHITECT ANALYSIS RESULT")
    print("="*50)
    print(result)
    print("="*50)

if __name__ == "__main__":
    test_cantor_analysis()
