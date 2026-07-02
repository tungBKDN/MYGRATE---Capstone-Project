#!/usr/bin/env python3
import json
import re
from pathlib import Path

from script_utils import clean_ansi

MODELS = ("deepseek-v3.2_cloud", "qwen3.5_cloud")

LOG_FILE_NAME = "cli_output.log"

SUCCESS_TITLE = "## ✅ Successful Migrations ({count})"
SKIPPED_TITLE = "## ⏭️ Skipped Codebases ({count})"
FAILED_TITLE = "## ❌ Failed Migrations ({count})"


def read_log_lines(log_path):
    if not log_path.exists():
        return None, "Log file not found (the workspace folder may have been cleaned/recreated)."

    try:
        content = clean_ansi(log_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return None, f"Failed to read log file: {exc}"

    return content.splitlines(), None


def find_first_log_match(lines, needle):
    for line in lines:
        if needle in line:
            return line.strip()
    return None


def extract_failure_reason(log_path, gate1_ok, gate2_ok, gate3_ok):
    lines, error_message = read_log_lines(log_path)
    if error_message:
        return error_message

    for line in lines:
        if "Gate 2 Failed: Final test count 0 is less than baseline" in line:
            pom_issue = find_first_log_match(lines, "Failed to prepare POM for JaCoCo")
            if pom_issue:
                return pom_issue

            xml_issue = find_first_log_match(lines, "Opening and ending tag mismatch")
            if xml_issue:
                return xml_issue

            return (
                "Final evaluation compilation failed: The project changes or POM modifications introduced "
                "build/compilation errors, preventing the test suite from compiling and executing."
            )

        match = re.search(r"Gate 2 Failed: Final test count (\d+) is less than baseline (\d+)", line)
        if match:
            return (
                f"Test Count Mismatch: Only {match.group(1)} tests executed compared to a baseline of "
                f"{match.group(2)}. Some test classes were skipped or excluded."
            )

    pom_issue = find_first_log_match(lines, "Failed to prepare POM for JaCoCo")
    if pom_issue:
        return pom_issue

    xml_issue = find_first_log_match(lines, "Opening and ending tag mismatch")
    if xml_issue:
        return xml_issue

    compiler_errors = []
    in_compilation_error = False
    for line in lines:
        if "COMPILATION ERROR :" in line:
            in_compilation_error = True
            compiler_errors = []
            continue
        if in_compilation_error:
            if line.startswith("[INFO]") and "error" in line.lower():
                in_compilation_error = False
            elif line.startswith("[ERROR]") and "COMPILATION ERROR" not in line:
                error_line = line.replace("[ERROR]", "").strip()
                if error_line and len(compiler_errors) < 6:
                    compiler_errors.append(error_line)

    if compiler_errors:
        return "Compilation Failure:\n" + "\n".join([f"  - {err}" for err in compiler_errors])

    test_failures = []
    in_results = False
    for line in lines:
        if "Results :" in line or "Results:" in line:
            in_results = True
            test_failures = []
            continue
        if in_results:
            if line.startswith("[INFO]") or "Tests run:" in line:
                in_results = False
            elif line.startswith("[ERROR]") and not any(k in line for k in ("Failures:", "Errors:", "Skipped:")):
                failure_line = line.replace("[ERROR]", "").strip()
                if failure_line and len(test_failures) < 6:
                    test_failures.append(failure_line)

    if test_failures:
        return "Test Failures:\n" + "\n".join([f"  - {err}" for err in test_failures])

    build_errors = []
    for line in lines:
        line_str = line.strip()
        if line_str.startswith("[ERROR]") and not any(
            marker in line_str for marker in ("-classpath", "COMPILATION ERROR", "MojoFailureException", "MojoExecutionException")
        ):
            error_line = line_str.replace("[ERROR]", "").strip()
            if error_line and error_line not in build_errors:
                build_errors.append(error_line)

    if build_errors:
        return "Maven Build Errors:\n" + "\n".join([f"  - {err}" for err in build_errors[-6:]])

    for line in reversed(lines):
        if "Tests run:" in line and ("Failures:" in line or "Errors:" in line):
            return f"Test Execution Failed: {line.strip()}"

    return "Build failed. See logs for full output details."


def load_eval_data(eval_path):
    try:
        with open(eval_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        return f"Error loading {eval_path.name}: {exc}"


def classify_codebase(model_results, codebase, metrics):
    is_skip = metrics.get("is_skip", False)
    success = metrics.get("overall_success", False)
    log_file = model_results / codebase / LOG_FILE_NAME

    if is_skip:
        return "skip", None
    if success:
        return "success", None

    return "fail", extract_failure_reason(
        log_file,
        metrics.get("compilation_success", False),
        metrics.get("gate2_tests_pass", False),
        metrics.get("gate3_coverage_ok", False),
    )


def build_report_lines(model, eval_data, model_results):
    report_lines = [
        f"# Migration Inspection Report: {model}",
        "",
        "This report lists the migration outcome for each codebase, categorized by success, skipped, and failure reasons.",
        "",
    ]

    success_list = []
    skip_list = []
    fail_list = []

    for codebase in sorted(eval_data.keys()):
        metrics = eval_data[codebase]
        category, reason = classify_codebase(model_results, codebase, metrics)

        if category == "skip":
            skip_list.append((codebase, metrics))
        elif category == "success":
            success_list.append((codebase, metrics))
        else:
            fail_list.append((codebase, metrics, reason))

    report_lines.extend(render_success_section(success_list))
    report_lines.extend(render_skipped_section(skip_list))
    report_lines.extend(render_failure_section(fail_list))
    return report_lines


def render_success_section(success_list):
    lines = [SUCCESS_TITLE.format(count=len(success_list)), ""]
    if success_list:
        lines.append("| Codebase | Compile | Tests | Coverage (Baseline -> Final) | Steps |")
        lines.append("| --- | --- | --- | --- | --- |")
        for codebase, metrics in success_list:
            cov_str = f"{metrics.get('baseline_coverage', 0.0):.2f}% -> {metrics.get('line_coverage', 0.0):.2f}%"
            test_str = f"{metrics.get('passed_tests', 0)}/{metrics.get('total_tests', 0)}"
            lines.append(f"| `{codebase}` | PASS | PASS ({test_str}) | {cov_str} | {metrics.get('step_count', 0)} |")
    else:
        lines.append("No successful migrations found.")
    lines.append("")
    return lines


def render_skipped_section(skip_list):
    lines = [SKIPPED_TITLE.format(count=len(skip_list)), ""]
    if skip_list:
        lines.append("These codebases were skipped due to incomplete baseline metrics (e.g. 0% coverage or 0 passed tests):")
        lines.append("")
        for codebase, metrics in skip_list:
            lines.append(
                f"- `{codebase}`: Skipped (Baseline Total Tests = {metrics.get('baseline_total_tests')}, "
                f"Baseline Coverage = {metrics.get('baseline_coverage', 0.0):.2f}%)"
            )
    else:
        lines.append("No codebases were skipped.")
    lines.append("")
    return lines


def render_failure_section(fail_list):
    lines = [FAILED_TITLE.format(count=len(fail_list)), ""]
    if fail_list:
        for codebase, metrics, reason in fail_list:
            lines.append(f"### `{codebase}`")
            lines.append("")
            lines.append(f"- **Step count**: {metrics.get('step_count', 0)}")
            lines.append(
                f"- **Outcome gates**: Compile: {'PASS' if metrics.get('compilation_success') else 'FAIL'} | "
                f"Tests: {'PASS' if metrics.get('gate2_tests_pass') else 'FAIL'} | "
                f"Coverage: {'PASS' if metrics.get('gate3_coverage_ok') else 'FAIL'}"
            )
            lines.append("- **Failure Reason**:")
            lines.append("```text")
            lines.append(reason)
            lines.append("```")
            lines.append("")
    else:
        lines.append("No failed migrations found.")
    return lines


def main():
    root = Path(__file__).resolve().parents[2]
    results_dir = root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    for model in MODELS:
        eval_path = results_dir / f"eval_{model}.json"
        if not eval_path.exists():
            print(f"Skipping {model}: {eval_path.name} not found.")
            continue

        eval_data = load_eval_data(eval_path)
        if isinstance(eval_data, str):
            print(eval_data)
            continue

        model_results = results_dir / model
        if not model_results.exists():
            print(f"Skipping {model}: Results directory {model_results} not found.")
            continue

        report_lines = build_report_lines(model, eval_data, model_results)
        report_path = results_dir / f"inspect_{model}.md"
        report_path.write_text("\n".join(report_lines), encoding="utf-8")
        print(f"Generated {report_path.name}")


if __name__ == "__main__":
    main()
