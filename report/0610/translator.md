# Báo cáo Agent: Translator (0610 Update)

## 1. Tổng quan

| Thuộc tính | Chi tiết |
|---|---|
| **File chính** | [translator_agent.py](file:///d:/capstone_project/MYGRATE---Capstone-Project/src/agents/translator_agent.py) |
| **LLM** | ChatGroq (`llama-3.3-70b-versatile` mặc định) |
| **Prompt** | [translator.md](file:///d:/capstone_project/MYGRATE---Capstone-Project/src/prompts/translator.md) |
| **Vai trò** | Thực thi Chuyển đổi mã nguồn (Source Code Migrator) — chạy quét jdeprscan chi tiết mã nguồn, phân tích cú pháp AST, tạo kế hoạch thay đổi, chỉnh sửa XML cấu hình POM và kiểm chứng biên dịch. |

---

## 2. Ý tưởng & Cơ chế hoạt động

Translator Agent chịu trách nhiệm thực thi các thay đổi mã nguồn thực tế của quá trình nâng cấp JDK. Agent hoạt động dựa trên triết lý **Phân tích từng bước & Suy luận an toàn (Self-Reasoning Constraint)**.

### 2.1. Phân tích Deprecation 3 lớp (The jdeprscan Pipeline)
Trước khi chỉnh sửa bất kỳ tệp tin nào, Translator Agent chạy công cụ jdeprscan để thu thập dữ liệu chẩn đoán qua 3 lớp:
1. **Lớp mã nguồn dự án**: Phát hiện các dòng lệnh gọi API deprecated hoặc `forRemoval=true` (ví dụ: `StringBufferInputStream` đã bị xóa ở JDK 17).
2. **Lớp thư viện phụ thuộc**: Phát hiện các JAR bên thứ ba nào gọi API deprecated của JDK.
3. **Lớp pom.xml**: Xác định các dependency nào cần được nâng cấp dựa trên hai lớp trên.

### 2.2. Xây dựng kế hoạch thay đổi (AST & Grep Search)
Agent sử dụng công cụ phân tích AST (qua thư viện **tree-sitter**) và tìm kiếm văn bản (Grep/Regex) để định vị chính xác vị trí lỗi:
- `find_code_usages`: Sử dụng bộ phân tích cú pháp AST để tìm khai báo Class, lời gọi Method, hoặc import của một thư viện cụ thể.
- `search_codebase`: Quét regex các tệp tin cấu hình (XML, Properties) để định vị chuỗi ký tự lỗi.

### 2.3. Áp dụng thay đổi & Kiểm chứng
- **Chỉnh sửa POM cấu hình**: Sử dụng công cụ `MavenPomEditor` để thêm/cập nhật thư viện, điều chỉnh version hoặc chỉnh sửa thẻ cấu hình XML một cách an toàn mà không làm mất định dạng file ban đầu.
- **Biến đổi file code**: Ghi các mã nguồn đã chuyển đổi (nhờ LLM sinh) vào thư mục `/artifacts` của dự án để chuẩn bị tích hợp.
- **Kiểm chứng bằng Maven**: Sử dụng `MavenRunner` kích hoạt trình biên dịch Maven (`mvn compile` hoặc `mvn test`) để xác thực xem các thay đổi đã giải quyết được lỗi biên dịch chưa.

---

## 3. Input / Output

### 3.1. Input
- Đường dẫn mã nguồn dự án (`project_path`).
- Phiên bản JDK mục tiêu.
- Dữ liệu kế hoạch nâng cấp từ bộ giải.

### 3.2. Output
Các báo cáo kết quả quét được ghi trực tiếp vào thư mục `/artifacts` của dự án đích:
- `jdeprscan_report.json`: Báo cáo chi tiết kết quả quét API JDK deprecated.
- `mygrate_report.json`: Kế hoạch thay đổi chi tiết từng file mã nguồn.
- `migration_report.md`: Báo cáo tổng hợp hướng dẫn nâng cấp mã nguồn cho nhà phát triển.

---

## 4. Các công cụ (Tools) sử dụng

| Tên Tool | Hàm xử lý | Mục đích |
|---|---|---|
| `run_jdeprscan` | `_tool_run_jdeprscan` | Chạy pipeline chẩn đoán B0-B3 thu thập API lỗi. |
| `build_change_plan` | `_tool_build_change_plan` | Quét cấu trúc tìm kiếm các tệp tin cần thay đổi. |
| `enrich_report` | `_tool_enrich_report` | Kết xuất báo cáo Markdown hướng dẫn nâng cấp. |
| `find_code_usages` | `_tool_find_code_usages` | Phân tích cú pháp AST (tree-sitter) định vị lời gọi API. |
| `search_codebase` | `_tool_search_codebase` | Grep/Regex nội dung văn bản trong toàn bộ project. |
| `get_file_migration_details` | `_tool_get_file_migration_details` | Lấy chi tiết các dòng code lỗi của 1 file cụ thể. |
| `write_file` | `_tool_write_file` | Lưu mã nguồn mới vào thư mục `/artifacts`. |
| `edit_pom_dependency` | `_tool_edit_pom_dependency` | Chỉnh sửa tệp tin cấu hình Maven `pom.xml`. |
| `run_maven_command` | `_tool_run_maven_command` | Thực thi Maven biên dịch và chạy test kiểm chứng. |

---
*Báo cáo tạo ngày: 2026-06-10*
