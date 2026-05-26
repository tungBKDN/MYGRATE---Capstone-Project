# Hướng dẫn sử dụng (Usage)

Tài liệu này mô tả cách chạy công cụ, các tuỳ chọn cấu hình và các kịch bản phổ biến.

1. Yêu cầu

- Python 3.10+ (hoặc theo `pyproject.toml` / `requirements.txt`).
- Các phụ thuộc được liệt kê trong `requirements.txt` hoặc môi trường ảo.

2. Chạy nhanh (Quick start)

Windows PowerShell:

```powershell
# Kích hoạt môi trường ảo (nếu có)
& .\.venv\Scripts\Activate.ps1
python main.py --help
```

Hoặc chạy trực tiếp file entrypoint:

```bash
python src/main.py --input path/to/codebase --output artifacts/report.json
```

3. Tham số chính (CLI)

- `--input` hoặc `-i`: đường dẫn đến mã nguồn hoặc thư mục chứa project.
- `--output` hoặc `-o`: đường dẫn lưu artifacts và báo cáo.
- `--profile`: tên cấu hình pipeline (ví dụ `default`, `deep-scan`).
- `--dry-run`: chạy giả lập, không áp dụng thay đổi.
- `--verbose` / `--debug`: bật log chi tiết.

4. Kịch bản phổ biến

- Phân tích nhanh: `python src/main.py -i ./freshbrew_data/cantor -o ./artifacts -p default`
- Kiểm tra và thử nghiệm patch (dry-run): `python src/main.py -i ./src -o ./artifacts --dry-run`

5. Phân tích kết quả

- Các file output chính được lưu trong `artifacts/`.
- Mở `artifacts/report.json` hoặc `artifacts/*.ipynb` để xem báo cáo chi tiết.

6. Lưu ý vận hành

- Đảm bảo quyền đọc/ghi cho thư mục đầu vào/đầu ra.
- Với mã lớn, cân nhắc tăng tham số bộ nhớ hoặc phân mảnh quy trình theo module.
