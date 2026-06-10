# Báo cáo Agent: Supervisor (0610 Update)

## 1. Tổng quan

| Thuộc tính | Chi tiết |
|---|---|
| **File chính** | [supervisor.py](file:///d:/capstone_project/MYGRATE---Capstone-Project/src/agents/supervisor.py) |
| **LLM** | ChatGroq (`llama-3.3-70b-versatile` mặc định) |
| **Prompt** | [supervisor.md](file:///d:/capstone_project/MYGRATE---Capstone-Project/src/prompts/supervisor.md) |
| **Vai trò** | Điều phối & Orchestrator — quản lý trạng thái toàn cục (`GlobalState`), quyết định chuyển hướng quyền điều khiển giữa các sub-agents hoặc kết thúc pipeline. |

---

## 2. Ý tưởng & Cơ chế hoạt động

Supervisor Agent đóng vai trò là "bộ não" trung tâm điều phối toàn bộ workflow của Mygrate. Được xây dựng theo mô hình **ReAct (Reasoning + Acting)** kế thừa từ `BaseAgent`, Supervisor sử dụng LLM để suy luận về tiến trình hiện tại và gọi các tool điều phối để chuyển hướng.

### 2.1. Quy trình điều phối 2 pha mới (Two-Phase Sequence)
Trong bản cập nhật 0610, luồng điều phối được nâng cấp để hỗ trợ chạy `ReaderAgent` ở hai thời điểm khác nhau (Pha 1: Discovery và Pha 2: Final Review):

1. **Pha 1: Quét và phân loại (Discovery & Classification)**:
   - Supervisor nhận project path từ người dùng. Nếu chưa quét, chuyển quyền điều khiển sang `reader`.
   - `ReaderAgent` quét cấu trúc, tìm dependencies, và tự động phân loại (Green/Yellow/Red).
   - Kết quả hiển thị cho người dùng và dừng lại ở node `end` để chờ xác nhận chạy phân tích độ tương thích.

2. **Giải quyết ràng buộc phiên bản (Dependency Solving)**:
   - Khi người dùng đồng ý, Supervisor gọi `architect`.
   - `ArchitectAgent` chạy 7 bước giải quyết thư viện và chạy các JVM smoke test.

3. **Pha 2: Đánh giá và Đề xuất (Final Candidate Review)**:
   - Sau khi `architect` hoàn thành, Supervisor tự động gọi lại `reader` lần thứ hai để thực hiện đánh giá các giải pháp tương thích, chấm điểm ứng viên, và lựa chọn giải pháp tối ưu nhất, đồng thời viết báo cáo đề xuất vào thư mục `/artifacts`.
   - Trả lại kết quả cho người dùng, chuyển sang `end` và chờ phê duyệt thực thi nâng cấp code.

4. **Biến đổi mã nguồn (Code Transformation)**:
   - Khi được phê duyệt, Supervisor gọi `translator` để phân tích deprecation qua jdeprscan, tạo kế hoạch thay đổi AST và áp dụng các nâng cấp thư viện vào POM cũng như cập nhật code Java.
   - Hoàn thành và kết thúc pipeline (`end`).

---

## 3. Input / Output

### 3.1. Input (Global State Context)
Supervisor Agent đọc ngữ cảnh từ `GlobalState` dưới dạng một payload JSON rút gọn để tránh quá tải token:
```json
{
  "project_path": "freshbrew_data/sonar-stash",
  "project_type": "java",
  "target_java_version": "17",
  "dependencies_count": 14,
  "dependencies_preview": "sonar-plugin-api:6.7, guava:27.0.1-jre...",
  "last_subagent_result": "...",
  "completed_tasks": ["Indexed codebase"],
  "has_solutions": true,
  "has_reader_review": false,
  "has_translation": false
}
```

### 3.2. Output (Routing Decision)
Mọi quyết định của Supervisor bắt buộc phải gọi qua tool `route_to` để cập nhật trạng thái LangGraph dưới định dạng JSON:
```json
{
  "next_node": "reader | architect | translator | end",
  "current_instruction": "Yêu cầu chi tiết gửi cho node tiếp theo",
  "summary_update": "Tóm tắt công việc vừa hoàn thành để lưu vào lịch sử",
  "response_to_user": "Tin nhắn phản hồi hiển thị lên giao diện cho người dùng"
}
```

---

## 4. Các công cụ (Tools) sử dụng

| Tên Tool | Hàm xử lý | Mô tả |
|---|---|---|
| `route_to` | `_tool_route_to` | Quyết định chuyển quyền điều khiển đến node tiếp theo (`reader`, `architect`, `translator`, `end`). |

---

## 5. Cơ chế fallback dự phòng (Deterministic Fallback)

Nếu không cấu hình LLM (không có `GROQ_API_KEY`), Supervisor tự động kích hoạt hàm chạy tuần tự tuyến tính `_run_deterministic` để pipeline vẫn chạy ổn định:
- Nếu chưa có thông tin dependencies: Route sang `reader` (Phase 1).
- Nếu chưa có giải pháp nâng cấp: Route sang `architect`.
- Nếu có giải pháp nhưng chưa review: Route sang `reader` (Phase 2).
- Nếu đã review nhưng chưa thực hiện: Route sang `translator`.
- Nếu tất cả đã xong: Route sang `end`.

---
*Báo cáo tạo ngày: 2026-06-10*
