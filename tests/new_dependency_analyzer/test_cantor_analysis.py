import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from src.tools.java_dependency_tools import DependencySolver, inject_constrained_versions

def test_cantor_dependency_resolution():
    """
    Test khả năng giải quyết đồ thị phụ thuộc thực tế của dự án 'cantor'.
    Bao gồm các thư viện gốc: junit, slf4j-api, hadoop-common.
    Quy trình này sẽ gọi API thực tế tới Maven Central và deps.dev.
    """
    # Khởi tạo Solver với JDK đích là 17
    solver = DependencySolver(target_java="17")
    
    # Các dependency trích xuất từ pom.xml của cantor
    cantor_dependencies = [
        {"groupId": "junit", "artifactId": "junit"},
        {"groupId": "org.slf4j", "artifactId": "slf4j-api"},
        {"groupId": "org.apache.hadoop", "artifactId": "hadoop-common"}
    ]
    
    # Bước 1, 2, 3: Tải candidate, lọc heuristic, quét tĩnh
    # Để test nhanh, ta giới hạn max_versions=3
    for dep in cantor_dependencies:
        solver.add_library(
            group_id=dep["groupId"], 
            artifact_id=dep["artifactId"], 
            max_versions=3
        )
        
    # Xác nhận các library đã được thêm vào hệ thống
    assert ("junit", "junit") in solver.candidates
    assert ("org.slf4j", "slf4j-api") in solver.candidates
    assert ("org.apache.hadoop", "hadoop-common") in solver.candidates
        
    # Bước 5: Tiêm các version bị ép buộc (Constraint-Driven)
    inject_constrained_versions(solver)
    
    # Bước 6: Chạy thuật toán Backtracking Solver
    solver.solve()
    
    # Xác thực: Cần tìm thấy ít nhất 1 tổ hợp thỏa mãn không bị xung đột
    assert len(solver.solutions) > 0, "Không tìm thấy tổ hợp hợp lệ nào cho cantor"
    
    # Kiểm tra cấu trúc của tổ hợp đầu tiên
    first_solution = solver.solutions[0]
    
    # Format của key trong solution là tuple: ("groupId", "artifactId")
    assert ("junit", "junit") in first_solution
    assert ("org.slf4j", "slf4j-api") in first_solution
    assert ("org.apache.hadoop", "hadoop-common") in first_solution
    
    print(f"\n✅ Tìm thấy {len(solver.solutions)} tổ hợp tương thích cho Cantor. Tổ hợp tiêu biểu: {first_solution}")

def test_agent_initialization():
    from src.agents.dependency_analyzer_agent import DependencyAnalyzerAgent
    
    agent_java = DependencyAnalyzerAgent(language="java")
    assert agent_java.language == "java"
    assert len(agent_java.tools_list) > 0
    
    agent_python = DependencyAnalyzerAgent(language="python")
    assert agent_python.language == "python"
    assert len(agent_python.tools_list) > 0  # Implemented

if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
