import os
import re
import json
from dotenv import load_dotenv
from src.agents.architect_agent import ArchitectAgent
from src.tools.visualization_engine import generate_dashboard

def test_cantor_analysis():
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY not found in environment.")
        return

    print("Khởi chạy Mygrate Architect Agent...")
    agent = ArchitectAgent()
    
    instruction = "Thực hiện phân tích chuyên sâu cho dự án Java tại freshbrew_data/cantor để migrate lên Java 17. Đối với mỗi đề xuất version, bắt buộc đính kèm verification_url từ tool. Nhớ xuất ra JSON theo đúng định dạng được yêu cầu."
    
    print("\n[Đang suy luận và thu thập dữ liệu...]")
    report = agent.run(instruction)
    
    print("\n==================================================")
    print("ARCHITECT ANALYSIS RESULT (MARKDOWN)")
    print("==================================================")
    print(report)
    print("==================================================\n")
    
    # Extract JSON block using regex
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', report, re.DOTALL)
    
    if json_match:
        json_data = json_match.group(1)
        json_path = "migration_intelligence.json"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            f.write(json_data)
            
        print(f"[+] Intelligence JSON extracted and saved to: {json_path}")
        
        # Generate Visualization Image
        print("[+] Generating Visualization Image (Matplotlib)...")
        img_path = "dependency_graph.png"
        generate_dashboard(json_path, img_path)
        
    else:
        print("[-] Error: Agent did not return a valid JSON block.")

if __name__ == "__main__":
    test_cantor_analysis()
