import os
import sys
import json
from pathlib import Path

# Adjust path to import src modules
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.tools.maven import MavenRunner

def main():
    freshbrew_dir = project_root / "freshbrew_data"
    working_dir = project_root / "working"
    working_dir.mkdir(parents=True, exist_ok=True)
    
    output_json_path = working_dir / "precalc_baseline.json"

    if not freshbrew_dir.exists():
        print(f"Error: Thư mục {freshbrew_dir} không tồn tại.")
        sys.exit(1)

    print(f"Bắt đầu quét và tính toán baseline cho các codebase trong {freshbrew_dir}...")
    
    # Tìm các thư mục con có chứa pom.xml
    codebases = []
    for p in sorted(freshbrew_dir.iterdir()):
        if p.is_dir() and (p / "pom.xml").exists():
            codebases.append(p)

    if not codebases:
        print("Không tìm thấy codebase Maven nào.")
        sys.exit(0)

    print(f"Tìm thấy {len(codebases)} codebase.")

    # Đọc cache cũ nếu đã tồn tại để cập nhật/tránh mất dữ liệu
    cache_data = {}
    if output_json_path.exists():
        try:
            with open(output_json_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            print(f"Đã nạp file baseline đã lưu với {len(cache_data)} bản ghi.")
        except Exception as e:
            print(f"Cảnh báo: Không đọc được file baseline cũ: {e}")

    runner = MavenRunner(target_java_version="")

    for i, cb_path in enumerate(codebases):
        name = cb_path.name
        if name in cache_data:
            print(f"\n[{i+1}/{len(codebases)}] {name} -> [SKIP] Đã có kết quả trong cache.")
            continue
            
        print(f"\n[{i+1}/{len(codebases)}] Đang xử lý {name} tại {cb_path}...")
        
        try:
            # Chạy tính toán coverage và test
            res = runner.coverage(cb_path, clean=True)
            coverage = res.line_coverage_pct if res.coverage_found else 0.0
            
            cache_data[name] = {
                "total_test": res.total_tests,
                "test_pass": res.passed_tests,
                "cov": coverage
            }
            print(f"  -> Hoàn thành: total_test={res.total_tests}, test_pass={res.passed_tests}, cov={coverage:.2f}%")
            
            # Ghi đè file lưu trữ ngay sau mỗi lần hoàn thành của 1 dự án để tránh mất mát nếu crash
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"  -> Lỗi khi xử lý {name}: {e}")
        finally:
            # Restore files to HEAD and delete target/build artifacts to keep freshbrew_data pristine
            import subprocess
            subprocess.run(["git", "checkout", "."], cwd=str(cb_path), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "clean", "-fdx"], cwd=str(cb_path), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"\nHoàn tất! File kết quả lưu tại: {output_json_path}")

if __name__ == "__main__":
    main()
