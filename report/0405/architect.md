# Báo cáo Agent: Architect

## 1. Tổng quan

| Thuộc tính | Chi tiết |
|---|---|
| **File** | `src/agents/architect_agent.py` |
| **LLM** | **Không sử dụng LLM** — purely tool-driven |
| **Prompt** | `src/prompts/architect.md` (tham khảo, không gọi trực tiếp) |
| **Vai trò** | Lập kế hoạch migration — phân tích dependencies, deprecated APIs, xuất chiến lược nâng cấp |

## 2. Chức năng chính

Architect Agent là "bộ lập kế hoạch" của pipeline, hoạt động sau khi Reader thu thập dữ liệu:

1. **Phân tích dependencies** — đánh giá từng dependency có tương thích với target Java version hay không
2. **Phân tích deprecated APIs** — dựa trên kết quả jdeprscan, xác định API cần thay thế
3. **Tra cứu migration rules** — sử dụng data từ OpenRewrite và MigrationMiner để xuất thay đổi có thể
4. **Lập kế hoạch migration** — tạo danh sách bước migration plan với thứ tự ưu tiên
5. **Chạy 7-step pipeline** — gọi `run_upgrade_pipeline()` từ MavenUpgradeTools

### 2.1. 7-Step Dependency Pipeline

| Step | Mô tả |
|---|---|
| 1 | Fetch candidate versions từ Maven Central |
| 2 | Heuristic filter (loại alpha/beta/snapshot) |
| 3 | Static bytecode check (JDK compatibility + Java EE refs) |
| 4 | Compile check (javac --release verification) |
| 5 | Transitive constraint modeling (deps.dev API) |
| 6 | SAT/SMT solver (Z3 hoặc backtracking fallback) |
| 7 | Runtime smoke test (JVM class loading) |

## 3. Input / Output

**Input:** `GlobalState`

```python
{
    "project_path": str,
    "target_java_version": str,
    "dependencies": list[dict],   # Từ reader
    "deprecated_apis": list,       # Từ reader/jdeprscan
    "current_instruction": str,    # Hướng dẫn từ supervisor
}
```

**Output:** `dict` cập nhật state

```python
{
    "candidate_solutions": list,       # Danh sách giải pháp tương thích
    "upgrade_report": dict,            # Báo cáo nâng cấp (smoke test results)
    "compatibility_matrix": list,      # Các conflict edges
    "last_subagent_result": str,       # Tóm tắt kế hoạch
    "next_node": "reader_review",      # Luôn chuyển sang reader_review
}
```

## 4. Tools & Data sử dụng

| Tool/Data | File | Mục đích |
|---|---|---|
| MavenUpgradeTools | `src/tools/maven_upgrade_tools.py` | Chạy 7-step pipeline, parse POM |
| ChangeFinder | `src/tools/change_finder.py` | Tìm thay đổi giữa các version Java |
| OpenRewrite Rules | `src/data_distillation/openrewrite/` | Quy tắc migration tự động |
| MigrationMiner Links | `src/data_distillation/migrationminer/` | Liên kết đến migration thực tế |
| VisualizationEngine | `src/tools/visualization_engine.py` | Tạo biểu đồ dependency |

## 5. Workflow Integration

```
supervisor → architect → reader_review → supervisor
```

Architect nhận dữ liệu từ Reader qua state, và tạo kế hoạch cho Translator thực hiện. Sau khi architect xong, flow tự động chuyển sang `reader_review` (không quay lại supervisor ngay).

## 6. Data Distillation

Architect sử dụng dữ liệu "chưng cất" (distilled) từ 2 nguồn:

### OpenRewrite Rules (`data_distillation/openrewrite/`)
- `java-version-8.yml`, `java-version-11.yml`, `java-version-17.yml`, `java-version-21.yml`, `java-version-25.yml`
- Chứa các quy tắc migration tự động cho từng version Java
- Loại: ChangePackage, ChangeMethodName, RemoveMethodInvocations, ChangeMethodTargetToStatic

### MigrationMiner (`data_distillation/migrationminer/`)
- `links.txt` chứa các liên kết đến migration thực tế
- Được khai thác từ open-source projects

## 7. Vấn đề & Cải tiến tiềm năng

| Vấn đề | Hiện tại | Đề xuất |
|---|---|---|
| Không dùng LLM | Architect hoàn toàn tool-driven, không có LLM reasoning | Có thể thêm LLM để phân tích conflict phức tạp |
| Rule matching | Cần cơ chế tìm kiếm rule hiệu quả hơn | Index OpenRewrite rules bằng cấu trúc dữ liệu phù hợp (trie, hash_map) |
| Scope resolution | `affected_scopes` cần được tính toán chính xác hơn | Tích hợp Maven dependency tree analysis |
| Version-specific logic | Cần phân biệt rõ ràng giữa các version Java (8→11, 11→17, 17→21) | Thêm validation cho migration plan |
| Instruction parsing | Dùng regex để extract values từ instruction string | Nên chuyển sang structured input |

## 8. Test Coverage

- Chưa có unit test riêng cho ArchitectAgent
- Cần test: rule matching, plan generation, scope resolution, 7-step pipeline

---
*Báo cáo tạo ngày: 2026-06-05*