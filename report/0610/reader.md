# Báo cáo Agent: Reader (0610 Update)

## 1. Tổng quan

| Thuộc tính | Chi tiết |
|---|---|
| **File chính** | [reader_agent.py](file:///d:/capstone_project/MYGRATE---Capstone-Project/src/agents/reader_agent.py) |
| **LLM** | ChatGroq (`llama-3.3-70b-versatile` mặc định) |
| **Prompt** | [reader.md](file:///d:/capstone_project/MYGRATE---Capstone-Project/src/prompts/reader.md) |
| **Vai trò** | Khám phá và Đánh giá (Discovery & Review) — phụ trách quét ban đầu, phát hiện công nghệ, tự động phân loại rủi ro (Phase 1) và đưa ra quyết định chọn phiên bản tối ưu cuối cùng (Phase 2). |

---

## 2. Ý tưởng & Cơ chế hoạt động

Trong bản cập nhật 0610, `ReaderAgent` đã được nâng cấp mạnh mẽ để giải quyết bài toán nâng cấp quy mô lớn (nhiều dự án trong thư mục `freshbrew_data/`) theo triết lý phân tách rủi ro sớm.

### 2.1. Pha 1: Quét bề mặt & Tự động phân loại (Discovery & Classification)
Khi được kích hoạt ở đầu pipeline, Reader Agent thực hiện quét toàn bộ thư mục dự án. Nếu đường dẫn chứa nhiều dự án độc lập (ví dụ: `freshbrew_data/` chứa cả `cantor` và `sonar-stash`), agent sẽ tự động duyệt các thư mục con và trích xuất:
- **Build System**: Tự động nhận diện Maven (`pom.xml`), Gradle (`build.gradle` hoặc `.kts`), hoặc Ant (`build.xml`).
- **JDK Target hiện tại**: Đọc từ properties hoặc khai báo compiler plugin.
- **Java Files Count**: Số lượng tệp tin mã nguồn để đánh giá độ phức tạp.
- **Framework chính**: Nhận diện Spring Boot, SonarQube Plugin, Jakarta EE, v.v. qua tập dependencies.
- **Báo cáo có sẵn**: Kiểm tra sự tồn tại của báo cáo `jdeprscan` cũ trong `/artifacts` hoặc `/target`. Nếu báo cáo có trạng thái `PARTIAL` hoặc `FAIL`, agent sẽ đánh dấu là không đáng tin cậy (do build lỗi trước khi quét).

Từ các thông tin trên, Reader Agent phân loại các dự án thành 3 nhóm độ phức tạp:
- **Green**: Đã có báo cáo jdeprscan OK, không phát hiện lỗi `forRemoval`, ít API bị deprecated. (Chỉ cần nâng POM + dependencies).
- **Yellow**: jdeprscan bị lỗi `PARTIAL`/`FAIL`, hoặc có lỗi `forRemoval`, hoặc chưa có báo cáo quét. (Cần phân tích sâu từng tệp tin).
- **Red**: Sử dụng framework phiên bản cũ đã bị loại bỏ API trong JDK mới (ví dụ: `sonar-plugin-api` < 9.x hoặc Spring Boot < 2.5). (Cần cấu trúc lại kiến trúc).

Agent tự động kết xuất ra bảng Markdown tổng quan trên màn hình và ghi lại báo cáo:
- `<project_path>/artifacts/reader_scan_report.json`
- `<project_path>/artifacts/reader_scan_report.md`

### 2.2. Pha 2: Đánh giá giải pháp (Final Candidate Review)
Sau khi `ArchitectAgent` chạy bộ giải Z3 và cho ra các cấu hình phiên bản nâng cấp, Reader Agent được gọi lại để:
- Chấm điểm độ tương thích (`_solution_score`) của từng giải pháp dựa trên độ mới của thư viện, số lượng cảnh báo bytecode và trạng thái JVM Runtime Smoke Test.
- Lựa chọn giải pháp tối ưu và giải thích lý do lựa chọn so với các phương án bị loại bỏ.
- Xuất báo cáo đánh giá cuối cùng vào:
  - `<target_project>/artifacts/reader_review.json`
  - `<target_project>/artifacts/reader_review.md`

---

## 3. Input / Output

### 3.1. Pha 1 (Discovery Scan)
- **Input**: Đường dẫn thư mục cần quét.
- **Output**: JSON chứa trạng thái (`status: "ok"`), danh sách các sub-projects (`projects`), danh sách dependencies gộp, và Markdown report chứa bảng tổng quan.

### 3.2. Pha 2 (Candidate Review)
- **Input**: Một JSON chứa danh sách các giải pháp nâng cấp ứng viên (`solutions`), thông tin các gói bytecode tương thích và kết quả smoke test của JVM.
- **Output**: JSON chứa đề xuất cuối cùng (`selected_solution`), các rủi ro còn lại (`risks`), bước thực hiện tiếp theo (`next_steps`), và báo cáo chi tiết dạng markdown (`markdown_report`).

---

## 4. Các công cụ (Tools) sử dụng

| Tên Tool | Hàm xử lý | Mô tả |
|---|---|---|
| `run_lightweight_index` | `_tool_run_lightweight_index` | Quét cấu trúc tệp tin, trích xuất dependencies, JDK target, frameworks, báo cáo cũ, và phân loại dự án. |
| `review_upgrade_candidates` | `_tool_review_upgrade_candidates` | Chấm điểm, đánh giá và lựa chọn giải pháp nâng cấp tối ưu từ bộ giải. |
| `submit_final_answer` | `BaseAgent` built-in | Trả kết quả JSON cuối cùng về cho workflow. |

---
*Báo cáo tạo ngày: 2026-06-10*
