# Báo cáo Agent: Reader

## 1. Tổng quan

| Thuộc tính | Chi tiết |
|---|---|
| **File chính** | `src/agents/reader_agent.py` |
| **File phụ** | `src/agents/reader.py` (re-export `UniversalASTReader`) |
| **LLM** | ChatGroq (`llama-3.3-70b-versatile` mặc định) |
| **Prompt** | `src/prompts/reader.md` |
| **Vai trò** | Khám phá (discovery) — phân tích codebase Java, trích xuất dependencies, cấu trúc project, deprecated API usage |

## 2. Chức năng chính

Reader Agent chịu trách nhiệm khám phá codebase — bước đầu tiên trong pipeline migration:

1. **Quét cấu trúc project** — sử dụng `CodebaseIndexer` duyệt thư mục, xác định file Java, pom.xml, build.gradle
2. **Phân tích dependencies** — parse `pom.xml`, trích xuất artifactId, groupId, version
3. **Chạy jdeprscan** — phát hiện deprecated API qua `JDeprScanPipeline`
4. **Xây dựng context** — tổng hợp thông tin thành state cho các agent sau sử dụng
5. **Gọi LLM** — gửi thông tin codebase lên LLM để phân tích sâu hơn
6. **Final Review mode** — khi nhận context chứa candidate solutions, chuyển sang mode review để chọn giải pháp tốt nhất

### 2.1. Final Review Mode

Khi instruction chứa các từ khóa như "candidate solutions", "final review", "select the best", Reader chuyển sang review mode:

- Nhận danh sách solutions + smoke test results
- Chấm điểm từng solution bằng `_solution_score()`
- Ưu tiên solution đã PASS smoke test
- Tạo markdown report chi tiết
- Nếu LLM available, enrich review bằng LLM

## 3. Input / Output

**Input:** `GlobalState`

```python
{
    "project_path": str,          # Đường dẫn project Java
    "project_type": str,          # Loại project (maven, gradle, unknown)
    "target_java_version": str,   # Mặc định "17"
    "current_instruction": str,   # Hướng dẫn từ supervisor
}
```

**Output:** `dict` cập nhật state

```python
{
    "dependencies": list[dict],   # Danh sách dependencies từ pom.xml
    "project_type": str,           # Loại project (xác định)
    "deprecated_apis": list,       # Kết quả jdeprscan
    "last_subagent_result": str,   # Tóm tắt kết quả reader
    "next_node": "supervisor",     # Luôn quay lại supervisor
}
```

## 4. Tools sử dụng

| Tool | File | Mục đích |
|---|---|---|
| CodebaseIndexer | `src/tools/codebase_indexer.py` | Duyệt cấu trúc thư mục, xác định loại project |
| JDeprScanPipeline | `src/tools/jdeprscan_pipeline.py` | Chạy jdeprscan, phát hiện deprecated API |
| MavenUpgradeTools | `src/tools/maven_upgrade_tools.py` | Parse pom.xml, trích xuất dependencies |
| ChangeFinder | `src/tools/change_finder.py` | Tìm thay đổi giữa các version |
| FileSystem | `src/tools/file_system.py` | Đọc/ghi file |

## 5. Workflow Integration

```
supervisor → reader → supervisor
```

Reader là node đầu tiên được gọi sau supervisor, cung cấp dữ liệu nền cho architect và translator.

## 6. Dependencies

| Dependency | Mục đích |
|---|---|
| `langchain_groq` / ChatGroq | Gọi LLM |
| `langchain_core.messages` | Xử lý messages |
| `tree_sitter` | Parse Java AST (qua `TreeSitterEngine`) |
| `dotenv` | Load biến môi trường |

## 7. Vấn đề & Cải tiến tiềm năng

| Vấn đề | Hiện tại | Đề xuất |
|---|---|---|
| Dual file confusion | Cả `reader_agent.py` và `reader.py` tồn tại | Hợp nhất thành một file duy nhất |
| Large codebase handling | Không có cơ chế chunking cho project lớn | Thêm chunking/pagination |
| Error handling | JDeprScanPipeline có thể fail nếu JDK không có | Cần graceful fallback |
| LLM optional | LLM có thể None nếu không có API key | Đã handle, nhưng cần logging tốt hơn |

## 8. Test Coverage

- Chưa có unit test riêng cho ReaderAgent
- Cần test: pom_xml parsing, jdeprscan integration, state output format, final review mode

---
*Báo cáo tạo ngày: 2026-06-05*