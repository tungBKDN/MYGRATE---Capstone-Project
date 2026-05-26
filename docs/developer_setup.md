# Thiết lập môi trường phát triển (Developer setup)

Hướng dẫn này dành cho người phát triển muốn chạy, debug, và đóng góp code.

1. Tạo môi trường ảo

Windows PowerShell:

```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Cấu trúc dự án quan trọng

- `src/`: mã nguồn Python chính.
- `artifacts/`: kết quả chạy, báo cáo.
- `scripts/`: script tiện ích (run_local_pipeline.py, orchestrator_runner.py).
- `tests/` hoặc `run_tests.py`: nơi chứa test (nếu có).

3. Kiểm tra và chạy test

```powershell
python run_tests.py
# hoặc (nếu dùng pytest)
pytest -q
```

4. Lint và format

Sử dụng `black` và `flake8` (nếu có trong requirements):

```powershell
black src/ tests/ docs/
flake8 src/
```

5. Debugging

- Chạy module trực tiếp với `python -m src.main` hoặc cấu hình trong IDE (VSCode/ PyCharm).
- Thêm breakpoint hoặc in log ở mức DEBUG.

6. Thêm agent mới

1. Tạo file agent mới trong `src/agents/`, tuân theo interface các agent hiện tại.
2. Đăng ký agent trong `src/workflow.py` nếu cần.
3. Viết test riêng cho agent và chạy toàn bộ test suite.
