# Ví dụ & Hướng dẫn từng bước (Examples)

1. Ví dụ: Phân tích thư mục mẫu `freshbrew_data/cantor`

```powershell
& .\.venv\Scripts\Activate.ps1
python src/main.py -i freshbrew_data/cantor -o artifacts/cantor_report
```

Kết quả: kiểm tra `artifacts/cantor_report` để xem báo cáo chi tiết và notebook kết quả.

2. Ví dụ: Chạy pipeline ở chế độ `dry-run`

```powershell
python src/main.py -i src/ -o artifacts/dry_run --dry-run
```

3. Ví dụ: Thêm agent đơn giản để in file list

1. Tạo `src/agents/list_agent.py` với class `ListAgent` có method `run()`.
2. Đăng ký trong `src/workflow.py` và gọi pipeline.

4. Tutorial: Tạo patch nâng cấp dependency Maven (kịch bản)

- Bước 1: Index project và tìm file `pom.xml` (sử dụng `tools/maven_upgrade_tools.py`).
- Bước 2: `architect_agent` xác định dependency cần cập nhật.
- Bước 3: `translator_agent` sinh patch sửa `pom.xml`.
- Bước 4: `supervisor` kiểm thử build (nếu có môi trường) hoặc ghi chú thay đổi vào report.
