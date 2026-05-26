# Tài liệu tham khảo API (API Reference)

Phần này liệt kê các module, lớp và hàm quan trọng trong `src/` kèm mô tả ngắn và ví dụ sử dụng.

1. `src/main.py`

- `main()` - Entrypoint CLI. Parse args, gọi `workflow.run()`.

2. `src/workflow.py`

- `run_pipeline(config)` - Thi hành pipeline: khởi tạo indexer, các agent và điều phối luồng.

3. `src/agents/reader_agent.py`

- `ReaderAgent` - Lớp chịu trách nhiệm đọc mã nguồn, trả về danh sách document.
- `read(path)` - Trích xuất nội dung file và metadata.

4. `src/agents/architect_agent.py`

- `ArchitectAgent` - Phân tích cấu trúc hệ thống, xác định chiến lược nâng cấp.
- `analyze(documents)` - Trả về các đề xuất ở mức module/class.

5. `src/ast_parser/transformer.py`

- `transform_source(source_code)` - Trả về AST đã chuẩn hóa.

6. `src/core/tree_sitter_engine.py`

- `parse_file(path)` - Sử dụng tree-sitter để parse, trả về AST.

7. `src/models/schemas.py` và `src/models/state.py`

- Định nghĩa các cấu trúc JSON/schema dùng chung (Document, Report, ChangeSet).

8. `src/tools/codebase_indexer.py`

- `index(path)` - Tạo chỉ mục file, đường dẫn, và metadata phục vụ phân tích.

Ghi chú: Đây là bản tóm tắt; mở riêng từng file trong `src/` để xem tất cả hàm và lớp kèm docstring.
