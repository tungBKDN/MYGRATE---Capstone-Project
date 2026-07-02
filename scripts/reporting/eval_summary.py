#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

MODEL_FILES = {
    "DeepSeek v3.2 Cloud": "eval_deepseek-v3.2_cloud.json",
    "Qwen 3.5 Cloud": "eval_qwen3.5_cloud.json",
}

HEADER_WIDTH = 90
MODEL_COL_WIDTH = 26
METRIC_COL_WIDTH = 30


def load_json(path):
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception as exc:
        print(f"Error loading {path.name}: {exc}")
        return None


def average(values):
    return sum(values) / len(values) if values else None


def compute_stats(data, contain_skip):
    total = 0
    gate1_pass = 0
    gate1_2_pass = 0
    overall_pass = 0
    total_steps = 0

    g1_only_drops = []
    g1_2_only_drops = []
    g1_2_3_drops = []

    for metrics in data.values():
        is_skip = metrics.get("is_skip", False)
        if is_skip and not contain_skip:
            continue

        total += 1
        if is_skip:
            continue

        g1 = metrics.get("compilation_success", False)
        g2 = metrics.get("gate2_tests_pass", False)
        g3 = metrics.get("gate3_coverage_ok", False)
        drop = metrics.get("coverage_drop_pp")

        if g1:
            gate1_pass += 1
        if g1 and g2:
            gate1_2_pass += 1
        if g1 and g2 and g3:
            overall_pass += 1

        if drop is not None:
            if g1 and not g2:
                g1_only_drops.append(drop)
            elif g1 and g2 and not g3:
                g1_2_only_drops.append(drop)
            elif g1 and g2 and g3:
                g1_2_3_drops.append(drop)

        total_steps += metrics.get("step_count", 0)

    return {
        "total": total,
        "gate1_pass": gate1_pass,
        "gate1_2_pass": gate1_2_pass,
        "overall_pass": overall_pass,
        "total_steps": total_steps,
        "avg_drop_g1_only": average(g1_only_drops),
        "avg_drop_g1_2_only": average(g1_2_only_drops),
        "avg_drop_g1_2_3": average(g1_2_3_drops),
    }


def format_cell(passed, total):
    if total == 0:
        return "N/A"

    pct = (passed / total) * 100
    return f"{pct:6.2f}% ({passed}/{total})"


def format_drop(val):
    if val is None:
        return "N/A"
    return f"{val:+.3f} pp"


def build_results(root, contain_skip):
    results = {}
    for model_name, filename in MODEL_FILES.items():
        data = load_json(root / "results" / filename)
        if data is not None:
            results[model_name] = compute_stats(data, contain_skip)
    return results


def get_metric_value(results, model, key):
    if model not in results:
        return "N/A"

    stats = results[model]
    if key == "gate1":
        return format_cell(stats["gate1_pass"], stats["total"])
    if key == "gate1_2":
        return format_cell(stats["gate1_2_pass"], stats["total"])
    if key == "gate1_2_3":
        return format_cell(stats["overall_pass"], stats["total"])
    if key == "steps":
        avg_steps = stats["total_steps"] / stats["total"] if stats["total"] > 0 else 0
        return f"{stats['total_steps']} (Avg: {avg_steps:.1f})"
    if key == "drop_g1_only":
        return format_drop(stats["avg_drop_g1_only"])
    if key == "drop_g1_2_only":
        return format_drop(stats["avg_drop_g1_2_only"])
    if key == "drop_g1_2_3":
        return format_drop(stats["avg_drop_g1_2_3"])
    return "N/A"


def main():
    parser = argparse.ArgumentParser(description="Mygrate Evaluation Summary Script")
    parser.add_argument("--contain_skip", action="store_true", help="Include skipped codebases in the statistics")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    results = build_results(root, args.contain_skip)

    if not results:
        print("No evaluation JSON files found or loaded successfully.")
        sys.exit(1)

    mode_str = "CONTAINING SKIPS" if args.contain_skip else "EXCLUDING SKIPS"
    print("=" * HEADER_WIDTH)
    print(f"               MIGRATION EVALUATION REPORT SUMMARY ({mode_str})")
    print("=" * HEADER_WIDTH)

    header_fmt = f"{{:<{METRIC_COL_WIDTH}}} | {{:^{MODEL_COL_WIDTH}}} | {{:^{MODEL_COL_WIDTH}}}"
    row_fmt = header_fmt
    divider = "-" * METRIC_COL_WIDTH + "-+-" + "-" * MODEL_COL_WIDTH + "-+-" + "-" * MODEL_COL_WIDTH

    models = list(results.keys())
    model_col1 = models[0] if len(models) > 0 else "DeepSeek v3.2 Cloud"
    model_col2 = models[1] if len(models) > 1 else "Qwen 3.5 Cloud"

    print(header_fmt.format("Metric", model_col1, model_col2))
    print(divider)
    print(row_fmt.format("Pass Gate 1 (Compile)", get_metric_value(results, model_col1, "gate1"), get_metric_value(results, model_col2, "gate1")))
    print(row_fmt.format("Pass Gate 1 & 2 (Tests)", get_metric_value(results, model_col1, "gate1_2"), get_metric_value(results, model_col2, "gate1_2")))
    print(row_fmt.format("Pass Gate 1 & 2 & 3 (Cov)", get_metric_value(results, model_col1, "gate1_2_3"), get_metric_value(results, model_col2, "gate1_2_3")))
    print(divider)
    print(row_fmt.format("Avg Drop: ONLY Compiled (G1)", get_metric_value(results, model_col1, "drop_g1_only"), get_metric_value(results, model_col2, "drop_g1_only")))
    print(row_fmt.format("Avg Drop: ONLY G1 & G2 Pass", get_metric_value(results, model_col1, "drop_g1_2_only"), get_metric_value(results, model_col2, "drop_g1_2_only")))
    print(row_fmt.format("Avg Drop: G1 & G2 & G3 Pass", get_metric_value(results, model_col1, "drop_g1_2_3"), get_metric_value(results, model_col2, "drop_g1_2_3")))
    print(divider)
    print(row_fmt.format("Translator LLM Calls", get_metric_value(results, model_col1, "steps"), get_metric_value(results, model_col2, "steps")))
    print("=" * HEADER_WIDTH)


if __name__ == "__main__":
    main()
