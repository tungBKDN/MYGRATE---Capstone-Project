# Báo cáo Agent: Architect (0610 Update)

## 1. Tổng quan

| Thuộc tính | Chi tiết |
|---|---|
| **File chính** | [architect_agent.py](file:///d:/capstone_project/MYGRATE---Capstone-Project/src/agents/architect_agent.py) |
| **LLM** | ChatGroq (`llama-3.3-70b-versatile` mặc định) |
| **Prompt** | [architect.md](file:///d:/capstone_project/MYGRATE---Capstone-Project/src/prompts/architect.md) |
| **Vai trò** | Phân tích Ràng buộc & Tương thích (Compatibility Solver) — chạy bộ giải Z3/Backtracking và JVM smoke test để tìm ra tập phiên bản thư viện tương thích với JDK mục tiêu. |

---

## 2. Ý tưởng & Cơ chế hoạt động

Architect Agent chịu trách nhiệm giải quyết bài toán nâng cấp phiên bản thư viện sao cho thỏa mãn đồng thời hai điều kiện:
1. **Tương thích tĩnh**: Không sử dụng bytecode JDK mới hơn JDK mục tiêu, không gọi các API đã bị xóa.
2. **Không xung đột transitive**: Các thư viện phụ thuộc bắc cầu không yêu cầu các phiên bản xung đột nhau.

Để làm việc này, Architect Agent chạy một quy trình phân tích gồm 7 bước chính:

```
[B1: Maven Central Fetch] → [B2: Heuristic Filter] → [B3: Bytecode & Java EE Scan]
                                                           ↓
[B6: Z3/Backtrack Solver] ← [B5: Transitive Modeling] ← [B4: Javac Compile Check]
         ↓
[B7: JVM Smoke Test] → [Báo cáo Upgrade JSON]
```

### 2.1. Quy trình phân tích 7 bước (The 7-Step Pipeline)
1. **Step 1: Fetch candidate versions**: Tìm tất cả phiên bản hiện có của thư viện trên Maven Central.
2. **Step 2: Heuristic filter**: Loại bỏ các phiên bản không ổn định (alpha, beta, rc, snapshot, preview) để giảm không gian tìm kiếm.
3. **Step 3: Static check**: Quét tệp JAR để phát hiện phiên bản bytecode (ví dụ: JDK 17 là major class version 61) và tìm các tham chiếu đến các gói Java EE đã bị xóa (`javax.xml.bind`, `javax.activation`, v.v.). Chạy thêm `jdeprscan` cục bộ để phát hiện deprecated APIs.
4. **Step 4: Compile check**: Biên dịch thử mã nguồn Stub đối với JAR ứng viên bằng lệnh `javac --release <target_jdk>` để kiểm tra tính tương thích biên dịch.
5. **Step 5: Transitive constraint modeling**: Truy vấn Deps.dev để dựng cây phụ thuộc bắc cầu của từng phiên bản ứng viên, phát hiện các cạnh xung đột phiên bản.
6. **Step 6: Z3 SAT Solver**: Mô phỏng các ràng buộc phiên bản và quan hệ phụ thuộc thành các mệnh đề logic Boolean, chạy bộ giải tối ưu **Z3 SMT Solver** (hoặc thuật toán Backtracking nếu Z3 không khả dụng) để tìm ra 5 cấu hình phiên bản tương thích tĩnh tốt nhất.
7. **Step 7: JVM Runtime Smoke Test**: Đối với 3 cấu hình tốt nhất, agent tải các JAR tương ứng về, tạo mã nguồn test để nạp thử các class phổ biến bằng ClassLoader của JVM nhằm xác thực tính tương thích lúc chạy.

### 2.2. Triết lý lưu trữ Artifacts mới
Trong bản cập nhật 0610, toàn bộ kết quả phân tích và đồ thị trực quan hóa của Architect được ghi trực tiếp vào:
- `<target_project>/artifacts/upgrade_report.json`
- `<target_project>/artifacts/dependency_graphs/` (các tệp đồ thị PNG của kế hoạch nâng cấp).

---

## 3. Input / Output

### 3.1. Input
- Danh sách dependencies gốc từ Reader (`pom_data`).
- Phiên bản JDK mục tiêu (ví dụ: "17").

### 3.2. Output
- `upgrade_report`: Lưu trữ thông tin chi tiết của bộ giải, bao gồm danh sách xung đột, các gói class phiên bản bytecode, và kết quả kiểm tra `javac`.
- `candidate_solutions`: Top 5 cấu hình phiên bản tương thích được tìm thấy.
- `compatibility_matrix`: Danh sách các cạnh xung đột dependencies.

---

## 4. Các công cụ (Tools) sử dụng

| Tên Tool | Hàm xử lý | Mô tả |
|---|---|---|
| `run_upgrade_analysis` | `_tool_run_upgrade_analysis` | Thực thi quy trình 7 bước giải quyết tương thích thư viện. |

---
*Báo cáo tạo ngày: 2026-06-10*
