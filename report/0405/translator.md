# Báo cáo Agent: Translator

## 1. Tổng quan

| Thuộc tính | Chi tiết |
|---|---|
| **File** | `src/agents/translator_agent.py` |
| **Notebook** | `src/translator/translator.ipynb` |
| **LLM** | ChatGroq (`llama-3.3-70b-versatile` mặc định) — optional, fallback nếu không có API key |
| **Vai trò** | Thực hiện migration — thay đổi code Java theo kế hoạch từ Architect |

## 2. Chức năng chính

Translator Agent là "bộ thực thi" của pipeline, chuyển đổi code Java thực tế:

1. **Nhận migration plan** — từ state, lấy danh sách thay đổi cần thực hiện
2. **Chạy jdeprscan pipeline (B0-B3)** — phát hiện deprecated API usage trong project code và dependencies
   - B0: Maven resolve dependencies
   - B1: Compile project với JDK 8
   - B2: jdeprscan project JAR (JDK 17)
   - B3: jdeprscan mỗi dependency JAR (multi-threaded)
3. **Xây dựng translation report** — từ change candidates (ChangeFinder)
4. **Enrich với LLM** — nếu LLM available, thêm narrative fields và code change recommendations
5. **Ghi kết quả** — trả về JSON report đầy đủ

### 2.1. jdeprscan Pipeline Integration

Translator chạy jdeprscan **trước** khi build translation report, vì jdeprscan cung cấp 3 layers phân tích:

| Layer | Mô tả |
|---|---|
| Layer 1 (Project Code) | forRemoval và deprecated API calls trong source code |
| Layer 2 (Dependencies) | JARs sử dụng deprecated APIs |
| Layer 3 (pom.xml) | Dependencies có forRemoval=true |

### 2.2. LLM Enrichment

Nếu LLM available, Translator gửi:
- System prompt: hướng dẫn cách sử dụng jdeprscan data để ưu tiên forRemoval=true items
- User prompt: instruction + existing change plan JSON
- LLM trả về enriched JSON với `markdown_report` và `migration_notes`

## 3. Input / Output

**Input:** `GlobalState`

```python
{
    "project_path": str,
    "target_java_version": str,
    "migration_tasks": list[dict],   # Từ architect
    "current_instruction": str,      # Hướng dẫn từ supervisor
    "deprecated_apis": list,         # API cần thay thế
    "dependencies": list[dict],
    "pom_data": dict,
    "upgrade_report": dict,
    "candidate_solutions": list,
    "reader_review": dict,
    "jdeprscan_report": dict,
}
```

**Output:** `dict` cập nhật state

```python
{
    "last_subagent_result": str,        # Tóm tắt thay đổi thực hiện
    "jdeprscan_report": dict,           # (optional) Kết quả jdeprscan
    "completed_tasks_summary": str,     # Danh sách task hoàn thành
    "next_node": "supervisor",
}
```

## 4. Tools sử dụng

| Tool | File | Mục đích |
|---|---|---|
| JDeprScanPipeline | `src/tools/jdeprscan_pipeline.py` | Chạy jdeprscan B0-B3 |
| ChangeFinder | `src/tools/change_finder.py` | Xác định vị trí cần thay đổi |
| TreeSitterEngine | `src/core/tree_sitter_engine.py` | Parse và manipulate Java AST |
| ASTTransformer | `src/ast_parser/transformer.py` | Transform AST theo rules |
| FileSystem | `src/tools/file_system.py` | Đọc/ghi file source code |

## 5. Workflow Integration

```
supervisor → translator → supervisor
```

Translator là node thực thi cuối cùng, sau khi Architect lập kế hoạch và Reader review chọn giải pháp.

## 6. AST Processing Pipeline

```
Source Code → TreeSitterEngine.parse() → AST
                                              ↓
AST → ASTTransformer.transform(rules) → Modified AST
                                              ↓
Modified AST → TreeSitterEngine.unparse() → Updated Source Code
```

- **TreeSitterEngine** (`src/core/tree_sitter_engine.py`): Sử dụng tree-sitter library, parse Java code thành AST, hỗ trợ query nodes bằng S-expression, cho phép extract và replace các node cụ thể
- **ASTTransformer** (`src/ast_parser/transformer.py`): Áp dụng migration rules lên AST, xử lý import statements, method calls, class declarations

## 7. Vấn đề & Cải tiến tiềm năng

| Vấn đề | Hiện tại | Đề xuất |
|---|---|---|
| Code generation quality | LLM có thể tạo code không compile | Thêm compilation check sau mỗi transformation |
| Partial transformation | Nếu một file fail, toàn bộ batch có thể bị ảnh hưởng | Implement transaction-like rollback cho mỗi file |
| No rollback mechanism | Không có cơ chế hoàn tác thay đổi nếu migration fail | Thêm backup/restore mechanism |
| Context window | File Java lớn có thể vượt quá context window của LLM | Chunking cho file lớn |
| jdeprscan dependency | Pipeline fail nếu JDK không có | Graceful fallback, chỉ dùng ChangeFinder data |
| Instruction parsing | Parse instruction bằng regex + JSON | Nên chuyển sang structured input |

## 8. Test Coverage

- `tests/test_translator_agent.py` — có file test nhưng cần kiểm tra nội dung chi tiết
- Cần test: AST parsing, rule application, file I/O, edge cases (empty files, syntax errors)
- Cần test: jdeprscan pipeline integration, LLM enrichment fallback

---
*Báo cáo tạo ngày: 2026-06-05*