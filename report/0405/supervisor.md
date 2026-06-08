# Báo cáo Agent: Supervisor

## 1. Tổng quan

| Thuộc tính | Chi tiết |
|---|---|
| **File** | `src/agents/supervisor.py` |
| **Class** | `SupervisorAgent` |
| **LLM** | ChatGroq (`llama-3.3-70b-versatile` mặc định) |
| **Prompt** | `src/prompts/supervisor.md` |
| **Vai trò** | Điều phối (orchestrator) — phân tích state toàn cục, quyết định node tiếp theo trong workflow |

## 2. Chức năng chính

Supervisor là "bão" điều phối của pipeline MYGRATE. Nó:

1. **Đọc GlobalState** — trích xuất thông tin dự án (path, type, target Java version, dependencies, kết quả subagent trước, completed_tasks)
2. **Xây dựng context** — tạo chuỗi `state_context` tóm tắt trạng thái hiện tại
3. **Gọi LLM** — gửi system_prompt + state_context + chat history (10 tin nhắn gần nhất) đến ChatGroq
4. **Parse JSON response** — mong đợi LLM trả về JSON với các trường:
   - `next_node`: node tiếp theo (`reader`, `architect`, `reader_review`, `translator`, `end`)
   - `current_instruction`: hướng dẫn cho node tiếp theo
   - `summary_update`: tóm tắt công việc hoàn thành
   - `response_to_user`: tin nhắn phản hồi cho người dùng
5. **Fallback** — nếu JSON parse thất bại, mặc định route đến `end`

## 3. Input / Output

**Input:** `GlobalState`

```python
{
    "project_path": str,          # Đường dẫn project Java
    "project_type": str,          # Loại project (maven, gradle, unknown)
    "target_java_version": str,   # Mặc định "17"
    "dependencies": list[dict],   # [{artifactId, version, ...}]
    "last_subagent_result": str,  # Kết quả subagent gần nhất
    "completed_tasks_summary": list[str],
    "messages": list[BaseMessage],
}
```

**Output:** `dict` cập nhật state

```python
{
    "next_node": str,             # → node tiếp theo
    "current_instruction": str,   # → hướng dẫn cho node
    "completed_tasks_summary": str,  # (optional, nếu có summary_update)
    "messages": [AIMessage],       # (optional, nếu có response_to_user)
}
```

## 4. Workflow Integration

Supervisor là node trung tâm trong LangGraph workflow (`src/workflow.py`). Mỗi node khác (reader, architect, reader_review, translator) đều trả về state và quay lại supervisor, quyết định bước tiếp theo:

```
START → supervisor → reader → supervisor
                  → architect → reader_review → supervisor
                  → reader_review → supervisor
                  → translator → supervisor
                  → END
```

## 5. Routing Logic (từ Prompt)

| Điều kiện | Route đến |
|---|---|
| Project chưa được indexed | `reader` |
| Reader trả về dependencies | `architect` |
| Architect hoàn thành, chưa review | `reader_review` |
| Reader review hoàn thành | `end` (present solution) |
| User approve migration | `translator` |
| Chat thông thường / greeting | `end` |

## 6. Dependencies

| Dependency | Mục đích |
|---|---|
| `langchain_groq` / ChatGroq | Gọi LLM Groq API |
| `langchain_core.messages` | Xử lý SystemMessage, HumanMessage, AIMessage |
| `dotenv` | Load biến môi trường GROQ_API_KEY, GROQ_MODEL |

## 7. Vấn đề & Cải tiến tiềm năng

| Vấn đề | Hiện tại | Đề xuất |
|---|---|---|
| Dead code (dòng 46-47) | Tạo list `messages` với `None` rồi gán `messages = []` | Dọn dẹp dead code |
| Import muộn (dòng 49) | `from langchain_core.messages import ...` nằm trong method | Chuyển import lên module-level |
| Hardcoded fallback | Khi JSON parse thất bại, luôn route đến `end` | Thêm retry logic hoặc graceful degradation |
| Không có validation | Không kiểm tra `next_node` hợp lệ | Validate against danh sách node hợp lệ |
| Context truncation | `last_subagent_result` bị cắt 500 ký tự | Cho phép cấu hình truncation limit |
| Khởi tạo lại mỗi lần gọi | `get_supervisor_node()` tạo mới `SupervisorAgent` | Cache/Singleton cho workflow |

## 8. Test Coverage

- Chưa có unit test riêng cho SupervisorAgent
- Cần test: JSON parse success/failure, state_context building, routing logic

---
*Báo cáo tạo ngày: 2026-06-05*