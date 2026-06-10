# Báo cáo: Công cụ và Thư viện bổ trợ (0610 Update)

## 1. Tổng quan

Hệ thống Mygrate sử dụng một tập hợp các công cụ chuyên biệt để phân tích mã nguồn tĩnh, giải quyết ràng buộc phiên bản và biến đổi XML.

---

## 2. Danh mục Công cụ chính

### 2.1. Codebase Indexer (`src/tools/codebase_indexer.py` & `src/utils/indexer.py`)
- **Mục đích**: Duyệt toàn bộ cấu trúc thư mục, thống kê các loại tệp tin, và phân loại dự án (Java, Python, Mixed).
- **Hoạt động**: Thu thập danh sách các tệp tin mã nguồn và định vị mọi tệp tin build manifest (`pom.xml`, `build.gradle`, `build.xml`).

### 2.2. JDeprScan Pipeline (`src/tools/jdeprscan_pipeline.py`)
- **Mục đích**: Chẩn đoán mức độ tương thích JDK bằng công cụ `jdeprscan` thông qua quy trình 4 bước B0-B3:
  - **B0 (Resolve)**: Gọi Maven tải dependencies về thư mục `target/dependency/`. Tự động lưu cache thời gian thay đổi `pom.xml` (`.cache_pom_mtime`) để tránh tải lại vô ích.
  - **B1 (Compile)**: Biên dịch thử mã nguồn dự án bằng JDK 8 để tạo JAR nội bộ (có chèn `tools.jar` nếu cần).
  - **B2 (Project Scan)**: Chạy `jdeprscan --release <target_jdk>` trên dự án JAR để tìm API deprecated/forRemoval.
  - **B3 (Dependency Scan)**: Chạy quét song song đa luồng (multi-threaded `ThreadPoolExecutor`) trên tất cả JAR dependencies để tìm kiếm API bị loại bỏ. Gom nhóm kết quả theo ecosystem của thư viện.

### 2.3. Dependency Solver (`src/tools/maven_upgrade_tools.py`)
- **Mục đích**: Tìm kiếm và đề xuất phiên bản nâng cấp tương thích cho tất cả dependencies.
- **Hoạt động**:
  - Tra cứu Maven Central để lấy danh sách phiên bản.
  - Quét bytecode JAR để xác định phiên bản JDK biên dịch và các tham chiếu nguy hiểm Java EE.
  - Dùng **Z3 Solver** mô hình hóa các ràng buộc phiên bản logic Boolean, giải quyết mâu thuẫn phụ thuộc bắc cầu.
  - Chạy JVM Smoke Test: Biên dịch mã nguồn kiểm chứng động bằng ClassLoader của JDK mới để đảm bảo JAR nạp được lúc Runtime.

### 2.4. Maven POM Editor (`src/tools/maven/maven_pom_editor.py`)
- **Mục đích**: Đọc và chỉnh sửa XML của tệp `pom.xml` một cách an toàn.
- **Hoạt động**: Kế thừa công cụ chỉnh sửa cấu trúc của `freshbrew`, hỗ trợ thêm/cập nhật dependency, thay đổi giá trị property, cập nhật phiên bản plugin mà không phá vỡ cấu trúc format XML hoặc namespace của file POM gốc.

### 2.5. Maven Runner (`src/tools/maven/maven_runner.py`)
- **Mục đích**: Giao tiếp trực tiếp với tiến trình hệ thống để chạy lệnh Maven.
- **Hoạt động**: Khởi tạo tiến trình `subprocess` để chạy `mvn compile`, `mvn test`, `mvn dependency:copy-dependencies` bằng môi trường JDK được cấu hình, bắt các lỗi stderr để trả về chẩn đoán cho Translator Agent.

### 2.6. AST Parser & Usages (`src/tools/codebase_search_tools.py` & `src/ast_parser/`)
- **Mục đích**: Phân tích ngữ nghĩa mã nguồn Java thay vì dùng Regex thô sơ.
- **Hoạt động**: Sử dụng thư viện **tree-sitter** để phân tích cú pháp AST của mã nguồn Java, định vị chính xác vị trí lỗi biên dịch hoặc các câu lệnh import lỗi thời.

---

## 3. Quản lý Artifacts tập trung theo Dự án đích
Toàn bộ kết quả và báo cáo của các công cụ trên được chuyển đổi để ghi trực tiếp vào thư mục `/artifacts` của chính dự án đang được quét (e.g. `freshbrew_data/sonar-stash/artifacts/`):
- `reader_scan_report.*`: Báo cáo quét ban đầu.
- `jdeprscan_report.json`: Dữ liệu quét deprecation JDK.
- `mygrate_report.json` / `migration_report.md`: Kế hoạch nâng cấp code.
- `upgrade_report.json`: Báo cáo giải quyết tương thích của solver.
- `reader_review.*`: Quyết định chọn giải pháp nâng cấp tối ưu.

---
*Báo cáo tạo ngày: 2026-06-10*
