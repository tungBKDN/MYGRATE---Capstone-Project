#!/usr/bin/env python3
"""Classify evaluation failures into the legacy cause buckets."""

import json
from pathlib import Path

from script_utils import clean_ansi

CAUSE_NAMESPACE = "1. Namespace Migration"
CAUSE_TARGET_SETTINGS = "2. Target Settings Not Updated"
CAUSE_DEPENDENCY_REPLACEMENT = "3. No Compatible Dependency Replacement Available"
CAUSE_BREAKING_API = "4. Breaking API Changes in Upgraded Dependencies"
CAUSE_LOOP_BEHAVIOR = "5. Ineffective Agent Loop Behavior"

CAUSES = (
    CAUSE_NAMESPACE,
    CAUSE_TARGET_SETTINGS,
    CAUSE_DEPENDENCY_REPLACEMENT,
    CAUSE_BREAKING_API,
    CAUSE_LOOP_BEHAVIOR,
)

MODELS = ("deepseek-v3.2_cloud", "qwen3.5_cloud")

NAMESPACE_KEYWORDS = (
    "javax.annotation",
    "javax.xml.bind",
    "javax.crypto",
    "javax.activation",
    "javax.jws",
    "javax.xml.ws",
)

DEPENDENCY_FAILURE_PATTERNS = (
    "Could not resolve dependencies",
    "Failed to collect dependencies",
    "Could not transfer artifact",
)

BREAKING_API_PATTERNS = (
    "cannot find symbol",
    "method does not override",
    "cannot be applied to given types",
)


def load_log_content(log_path):
    if not log_path.exists():
        return ""

    try:
        return clean_ansi(log_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return ""


def classify_old_cause(codebase, metrics, log_path):
    if metrics.get("overall_success", False):
        return None

    is_skip = metrics.get("is_skip", False)
    step_count = metrics.get("step_count", 0)

    # If the project was skipped due to abnormal baseline (0 tests / 0% coverage),
    # it means no compatible testing/JaCoCo dependency is available for the JDK 17 environment.
    if is_skip or step_count == 0:
        return CAUSE_DEPENDENCY_REPLACEMENT

    comp = metrics.get("compilation_success", False)
    passed_tests = metrics.get("passed_tests", 0)
    baseline_tests = metrics.get("baseline_total_tests", 0)
    log_content = load_log_content(log_path)

    if "Failed to prepare POM for JaCoCo" in log_content or "Opening and ending tag mismatch" in log_content:
        return CAUSE_LOOP_BEHAVIOR

    if "Source option" in log_content and "no longer supported" in log_content:
        return CAUSE_TARGET_SETTINGS

    if "Target option" in log_content and "no longer supported" in log_content:
        return CAUSE_TARGET_SETTINGS

    if any(pattern in log_content for pattern in DEPENDENCY_FAILURE_PATTERNS):
        return CAUSE_DEPENDENCY_REPLACEMENT

    if any(keyword in log_content for keyword in NAMESPACE_KEYWORDS):
        return CAUSE_NAMESPACE

    if any(pattern in log_content for pattern in BREAKING_API_PATTERNS):
        return CAUSE_BREAKING_API

    lowered_log_content = log_content.lower()
    if any(keyword in lowered_log_content for keyword in ("mockito", "junit", "hamcrest")):
        return CAUSE_BREAKING_API

    # Test skipping -> Ineffective Agent Loop Behavior (cheating)
    if comp and passed_tests < baseline_tests and baseline_tests > 0:
        return CAUSE_LOOP_BEHAVIOR

    # Max steps / loop ineffective (fallback)
    if "Max iterations reached" in log_content or step_count >= 50:
        return CAUSE_LOOP_BEHAVIOR

    if not comp:
        return CAUSE_NAMESPACE

    return CAUSE_BREAKING_API


def build_cause_counts():
    return {cause: 0 for cause in CAUSES}


def run():
    root = Path(__file__).resolve().parents[2]
    working_dir = root / "working"

    for model in MODELS:
        eval_path = root / f"eval_{model}.json"
        if not eval_path.exists():
            continue

        with open(eval_path, "r", encoding="utf-8") as handle:
            eval_data = json.load(handle)

        model_working = working_dir / model
        causes = build_cause_counts()
        codebase_mapping = {cause: [] for cause in CAUSES}

        print(f"=== Model: {model} ===")

        for codebase, metrics in sorted(eval_data.items()):
            log_file = model_working / codebase / "artifacts" / "cli_output.log"
            cause = classify_old_cause(codebase, metrics, log_file)
            if cause:
                causes[cause] += 1
                codebase_mapping[cause].append(codebase)

        for cause in CAUSES:
            print(f"  {cause}: {causes[cause]}")
            if codebase_mapping[cause]:
                print(f"    Codebases: {', '.join(codebase_mapping[cause])}")
        print()


if __name__ == "__main__":
    run()
