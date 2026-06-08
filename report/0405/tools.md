# Báo cáo: Tools & Supporting Modules

## 1. Tổng quan

Các tools là module "độc lập" được các agents gọi để thực hiện các tác vụ cụ thể. Tất cả nằm trong `src/tools/`.

## 2. Chi tiết từng Tool

### 2.1. CodebaseIndexer (`codebase_indexer.py`)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò** | Duyệt cấu trúc thư mục project Java |
| **Sử dụng bởi** | Reader Agent |
| **Entry point** | `index_codebase(project_path)` |

**Chức năng:**
- Quét thư mục project, xác định loại (Maven, Gradle, unknown)
- Liệt kê file Java, resource files, config files
- Xây dựng map cấu trúc project cho agents khác sử dụng
- Sử dụng `ProjectIndexer` từ `src/utils/indexer.py`

---

### 2.2. JDeprScanPipeline (`jdeprscan_pipeline.py`)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò** | Chạy jdeprscan tool của JDK để phát hiện deprecated API |
| **Sử dụng bởi** | Reader Agent, Translator Agent |
| **Entry points** | `run_jdeprscan_pipeline()`, `scan_jar()`, `build_classpath()` |

**Chức năng:**
- Chạy jdeprscan trên compiled classes
- Parse output JSON/text
- Trích xuất danh sách deprecated API usage
- Hỗ trợ smoke test với `DeprecatedSample.java`
- 4-step pipeline: B0 (Maven resolve) → B1 (Compile JDK 8) → B2 (jdeprscan project) → B3 (jdeprscan dependencies)
- JDK discovery: tìm JDK qua JAVA_HOME, Program Files, PATH
- Multi-threaded B3 scanning

**Dependencies:** JDK có `jdeprscan` tool trong `bin/`

---

### 2.3. MavenUpgradeTools (`maven_upgrade_tools.py`)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò** | Parse và phân tích pom.xml, kiểm tra dependency compatibility |
| **Sử dụng bởi** | Reader Agent, Architect Agent |
| **Entry points** | `index_java_project()`, `run_upgrade_pipeline()`, `build_java_upgrade_report()` |

**Chức năng:**
- Parse `pom.xml` — trích xuất dependencies (groupId, artifactId, version, scope)
- Kiểm tra compatibility với target Java version
- 7-step upgrade pipeline:
  1. Fetch candidate versions từ Maven Central
  2. Heuristic filter (loại unstable versions)
  3. Static bytecode check (JDK compatibility + Java EE refs)
  4. Compile check (javac --release)
  5. Transitive constraint modeling (deps.dev API)
  6. SAT/SMT solver (Z3 hoặc backtracking fallback)
  7. Runtime smoke test (JVM class loading)
- Tạo dependency graph bằng NetworkX + Matplotlib

**Dependencies:** `requests`, `networkx`, `matplotlib`, `z3` (optional)

---

### 2.4. ChangeFinder (`change_finder.py`)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò** | Tìm thay đổi giữa các version Java |
| **Sử dụng bởi** | Architect Agent, Translator Agent |
| **Entry point** | `find_change_candidates()`, `build_translation_report()` |

**Chức năng:**
- Tìm kiếm trong OpenRewrite rules và MigrationMiner data
- Match deprecated API với replacement suggestions
- Xây dựng change map cho từng version upgrade
- Cluster lines thành regions cho snippet generation
- Merge và deduplicate candidates

**Data classes:** `ChangeCandidate` (file_path, start_line, end_line, match_type, dependency, reason, snippet)

---

### 2.5. FileSystem (`file_system.py`)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò** | Đọc/ghi file trong project đang migration |
| **Sử dụng bởi** | Translator Agent |
| **Tools** | `list_project_structure`, `read_source_code`, `get_file_summary` |

**Chức năng:**
- Đọc source file Java
- Ghi file (sửa đổi)
- Backup file gốc trước khi thay đổi
- Tìm kiếm file theo pattern
- LangChain `@tool` decorators cho agent integration

---

### 2.6. VisualizationEngine (`visualization_engine.py`)

| Thuộc tính | Chi tiết |
|---|---|
| **Vai trò** | Tạo biểu đồ và visualization cho dependency migration |
| **Sử dụng bởi** | Architect Agent |
| **Entry point** | `generate_dashboard()` |

**Chức năng:**
- Tạo dependency graph
- Visualize migration plan
- Xuất báo cáo dạng chart/image
- Sử dụng NetworkX + Matplotlib

**Dependencies:** `networkx`, `matplotlib`

---

## 3. Core Modules

### 3.1. TreeSitterEngine (`src/core/tree_sitter_engine.py`)

- Parse Java code thành AST sử dụng tree-sitter
- Query nodes bằng S-expression pattern
- Extract và replace nodes
- Unparse AST trở lại source code
- Hỗ trợ Python và Java

### 3.2. ASTTransformer (`src/ast_parser/transformer.py`)

- `TypeHintModernizer` — chuyển Python type hints từ `Union[X, Y]` → `X | Y` và `Optional[X]` → `X | None` (PEP 604)
- `modernize_code()` — parse, transform, và unparse Python source
- Tích hợp với TreeSitterEngine cho Java transformations

### 3.3. RuleExtractor (`src/data_distillation/src/rule_extractor.py`)

- Trích xuất migration rules từ OpenRewrite YAML files
- Parse rule format: ChangePackage, ChangeMethodName, RemoveMethodInvocations, ChangeMethodTargetToStatic
- Extract before/after patterns
- Index rules cho tìm kiếm nhanh
- Gắn metadata: target_version, reason, rule_id

---

## 4. Vấn đề chung

| Vấn đề | Mô tả | Đề xuất |
|---|---|---|
| Error handling | Nhiều tools thiếu error handling chi tiết | Thêm try/except và logging |
| Type hints | Thiếu type hints nhất quán | Thêm type hints cho maintainability |
| Documentation | Docstrings cần thiết ở nhiều places | Thêm docstrings |
| Test coverage | Hầu hết tools chưa có unit test riêng | Thêm unit tests |
| Z3 dependency | Z3 là optional, fallback không tối ưu | Document Z3 installation |

---
*Báo cáo tạo ngày: 2026-06-05*