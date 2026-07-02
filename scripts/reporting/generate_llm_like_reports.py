#!/usr/bin/env python3
import json
from pathlib import Path

from script_utils import clean_ansi

MODELS = ("deepseek-v3.2_cloud", "qwen3.5_cloud")


def read_log_content(log_path):
    if not log_path.exists():
        return None

    try:
        return clean_ansi(log_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return ""


def classify_success(metrics):
    passed = metrics.get("passed_tests", 0)
    total = metrics.get("total_tests", 0)
    drop = metrics.get("coverage_drop_pp", 0.0)
    steps = metrics.get("step_count", 0)

    if drop < 0:
        cov_msg = f"độ bao phủ code thậm chí còn tăng thêm {abs(drop):.2f}%"
    elif drop == 0:
        cov_msg = "độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi)"
    else:
        cov_msg = f"độ bao phủ chỉ giảm nhẹ {drop:.2f}% (nằm trong ngưỡng cho phép)"

    return (
        "SUCCESS",
        (
            f"Dịch chuyển thành công hoàn toàn lên Java 17 sau {steps} bước gọi LLM. "
            f"Dự án biên dịch thông suốt, toàn bộ {passed}/{total} bài test gốc đều vượt qua và {cov_msg}. "
            f"Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định."
        ),
    )


def find_any_line(log_content, needles):
    for line in log_content.splitlines():
        if any(needle in line for needle in needles):
            return True
    return False


def collect_lines_matching(log_content, start_token, stop_token="[INFO]"):
    entries = []
    in_block = False
    for line in log_content.splitlines():
        if start_token in line:
            in_block = True
            continue
        if in_block:
            if line.startswith(stop_token):
                in_block = False
            elif line.startswith("[ERROR]") and start_token not in line:
                entries.append(line.replace("[ERROR]", "").strip())
    return entries


def classify_failure(metrics, log_content):
    compilation_success = metrics.get("compilation_success", False)
    gate2_tests_pass = metrics.get("gate2_tests_pass", False)
    gate3_coverage_ok = metrics.get("gate3_coverage_ok", False)

    if find_any_line(log_content, ("Failed to prepare POM for JaCoCo", "Opening and ending tag mismatch")):
        return "POM_CONFIG_SYNTAX_ERROR", (
            "Thất bại do gặp lỗi cú pháp cấu trúc XML trong file `pom.xml`. "
            "Trong quá trình tự động chèn plugin JaCoCo hoặc nâng cấp phiên bản, Agent đã đóng/mở sai thẻ `<plugins>` "
            "hoặc `<execution>`, dẫn đến Maven không thể parse được file cấu hình."
        )

    passed_t = metrics.get("passed_tests", 0)
    baseline_t = metrics.get("baseline_total_tests", 0)
    if compilation_success and passed_t < baseline_t and baseline_t > 0:
        return "TEST_COUNT_MISMATCH_SKIPPED", (
            f"Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). "
            f"Dù biên dịch thành công, dự án chỉ thực thi được {passed_t}/{baseline_t} bài test gốc. "
            f"Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test."
        )

    if not compilation_success:
        if find_any_line(log_content, ("Could not resolve dependencies", "Failed to collect dependencies", "Could not transfer artifact")):
            return "COMPILATION_DEPENDENCY_RESOLVE_FAILED", (
                "Biên dịch thất bại do không thể phân giải được các dependency hoặc plugin Maven. "
                "Hệ thống gặp lỗi kết nối đến repository hoặc bị chặn quyền truy cập (unauthorized) khi tải các thư viện cần thiết."
            )

        comp_errs = collect_lines_matching(log_content, "COMPILATION ERROR :")
        if comp_errs:
            err_msg = comp_errs[0]
            if len(comp_errs) > 1:
                err_msg += f" (và {len(comp_errs) - 1} lỗi biên dịch khác)"
            return "COMPILATION_SOURCE_INCOMPATIBLE", (
                f"Biên dịch thất bại do không tương thích mã nguồn Java 17. "
                f"Lỗi chính được ghi nhận: \"{err_msg}\". "
                f"Agent chưa sửa đổi hết các API cũ hoặc thư viện bị loại bỏ trên JDK mới."
            )

        return "COMPILATION_SOURCE_INCOMPATIBLE", (
            "Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). "
            "Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng "
            "vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build."
        )

    if not gate2_tests_pass:
        failures = collect_lines_matching(log_content, "Results :", stop_token="[INFO]")
        failures.extend(collect_lines_matching(log_content, "Results:", stop_token="[INFO]"))
        failures = [entry for entry in failures if not any(k in entry for k in ("Failures:", "Errors:", "Skipped:"))]

        if failures:
            err_msg = failures[0]
            if len(failures) > 1:
                err_msg += f" (và {len(failures) - 1} test case khác bị đỏ)"
            return "TEST_RUNTIME_LOGIC_FAILED", (
                f"Dự án biên dịch thành công nhưng thất bại ở Gate 2 do lỗi logic chạy test. "
                f"Chi tiết: \"{err_msg}\". "
                f"Điều này chỉ ra lỗi không tương thích runtime của thư viện hoặc môi trường chạy test với Java 17."
            )

        return "TEST_RUNTIME_LOGIC_FAILED", (
            "Biên dịch thành công nhưng có một hoặc nhiều bài test gốc bị chạy lỗi (fail/error). "
            "Agent không tìm được cấu hình dependency tương thích hoàn toàn để làm xanh toàn bộ test suite."
        )

    if not gate3_coverage_ok:
        drop = metrics.get("coverage_drop_pp", 0.0)
        return "COVERAGE_DROP_EXCEEDED", (
            f"Dự án biên dịch và vượt qua toàn bộ test suite thành công. Tuy nhiên, thất bại ở Gate 3 "
            f"do độ bao phủ dòng code (Code Coverage) bị sụt giảm quá mạnh ({drop:.2f} pp, vượt ngưỡng cho phép 5.0 pp). "
            f"Nguyên nhân thường do thay đổi lớn ở cấu trúc file hoặc một phần code test bị cô lập."
        )

    return "UNKNOWN", "Không xác định rõ nguyên nhân thất bại từ log. Cần kiểm tra thủ công file log."


def classify_and_explain(codebase, metrics, log_path):
    is_skip = metrics.get("is_skip", False)
    success = metrics.get("overall_success", False)

    if is_skip:
        return "BASELINE_INVALID", (
            f"Dự án được bỏ qua do số liệu baseline không hợp lệ (không có bài test nào hoặc độ bao phủ bằng 0.0%). "
            f"Hệ thống đã tự động skip theo cấu hình để tránh gây sai lệch kết quả đánh giá chung của toàn bộ batch."
        )

    if success:
        return classify_success(metrics)

    log_content = read_log_content(log_path)
    if log_content is None:
        return "COMPILATION_SOURCE_INCOMPATIBLE", (
            "Không tìm thấy file log chạy của dự án này (có thể do thư mục workspace bị dọn dẹp hoặc tiến trình bị hủy đột ngột). "
            "Kết quả lưu vết cho thấy dự án không hoàn thành được pha biên dịch và kiểm thử cuối cùng."
        )

    if log_content == "":
        log_content = ""

    return classify_failure(metrics, log_content)


def load_eval_data(eval_path):
    try:
        with open(eval_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        return f"Error loading {eval_path.name}: {exc}"


def build_report_lines(model, eval_data, model_working):
    report_lines = [
        f"# Báo cáo Đánh giá và Phân tích Dịch chuyển Codebase: {model}",
        "",
        "Báo cáo này tổng hợp chi tiết kết quả dịch chuyển Java 17 cho từng codebase, kèm theo lý do giải thích cụ thể cho từng trường hợp.",
        "",
    ]

    success_list = []
    skip_list = []
    fail_list = []

    for codebase in sorted(eval_data.keys()):
        metrics = eval_data[codebase]
        is_skip = metrics.get("is_skip", False)
        success = metrics.get("overall_success", False)
        log_file = model_working / codebase / "artifacts" / "cli_output.log"
        enum_reason, explanation = classify_and_explain(codebase, metrics, log_file)

        if is_skip:
            skip_list.append((codebase, metrics, enum_reason, explanation))
        elif success:
            success_list.append((codebase, metrics, enum_reason, explanation))
        else:
            fail_list.append((codebase, metrics, enum_reason, explanation))

    report_lines.extend(render_success_section(success_list))
    report_lines.extend(render_skip_section(skip_list))
    report_lines.extend(render_failure_section(fail_list))
    return report_lines


def render_success_section(success_list):
    lines = [f"## ✅ Các Codebase Dịch chuyển Thành công ({len(success_list)})", ""]
    for codebase, _metrics, enum_val, exp in success_list:
        lines.append(f"### `{codebase}`")
        lines.append("")
        lines.append("- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)")
        lines.append(f"- **Lý do (Enum)**: `{enum_val}`")
        lines.append(f"- **Giải thích**: {exp}")
        lines.append("")
    return lines


def render_skip_section(skip_list):
    lines = [f"## ⏭️ Các Codebase Bị Bỏ Qua / Skip ({len(skip_list)})", ""]
    for codebase, _metrics, enum_val, exp in skip_list:
        lines.append(f"### `{codebase}`")
        lines.append("")
        lines.append("- **Kết quả**: SKIPPED")
        lines.append(f"- **Lý do (Enum)**: `{enum_val}`")
        lines.append(f"- **Giải thích**: {exp}")
        lines.append("")
    return lines


def render_failure_section(fail_list):
    lines = [f"## ❌ Các Codebase Dịch chuyển Thất Bại ({len(fail_list)})", ""]
    for codebase, metrics, enum_val, exp in fail_list:
        lines.append(f"### `{codebase}`")
        lines.append("")
        lines.append("- **Kết quả**: THẤT BẠI")
        lines.append(
            f"- **Cổng lỗi**: Compile: {'PASS' if metrics.get('compilation_success') else 'FAIL'} | "
            f"Tests: {'PASS' if metrics.get('gate2_tests_pass') else 'FAIL'} | Coverage: {'PASS' if metrics.get('gate3_coverage_ok') else 'FAIL'}"
        )
        lines.append(f"- **Lý do (Enum)**: `{enum_val}`")
        lines.append(f"- **Giải thích**: {exp}")
        lines.append("")
    return lines


def main():
    root = Path(__file__).resolve().parents[2]
    working_dir = root / "working"
    report_dir = root / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    for model in MODELS:
        eval_path = root / f"eval_{model}.json"
        if not eval_path.exists():
            print(f"Skipping {model}: {eval_path.name} not found.")
            continue

        eval_data = load_eval_data(eval_path)
        if isinstance(eval_data, str):
            print(eval_data)
            continue

        model_working = working_dir / model
        if not model_working.exists():
            print(f"Skipping {model}: Working directory {model_working} not found.")
            continue

        report_lines = build_report_lines(model, eval_data, model_working)
        report_path = report_dir / f"inspect_{model}.md"
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"Generated {report_path.name}")


if __name__ == "__main__":
    main()
