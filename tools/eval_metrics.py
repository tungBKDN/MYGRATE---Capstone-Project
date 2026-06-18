"""
Evaluation Metrics Calculator for MYGRATE migration results.

Reads test/artifacts/eval.json and computes:
  Gate 1: compilation_success == True
  Gate 2: Gate 1 OK + passed_tests == total_tests
  Gate 3: Gate 1 OK + Gate 2 OK + (baseline_coverage - line_coverage <= 5)

Usage:
  python tools/eval_metrics.py
  python tools/eval_metrics.py --json_path path/to/eval.json
"""

import json
import sys
import os
from collections import OrderedDict


def load_eval(json_path: str | None = None) -> dict:
    if json_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.normpath(os.path.join(script_dir, "..", "test", "artifacts", "eval-qwen.json"))

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_metrics(data: dict) -> dict:
    total = len(data)

    projects = []
    for name, info in sorted(data.items()):
        compile_ok = info.get("compilation_success", False)
        passed = info.get("passed_tests", 0)
        total_tc = info.get("total_tests", 0)
        baseline_cov = info.get("baseline_coverage", 0.0)
        line_cov = info.get("line_coverage", 0.0)

        tests_ok = (passed == total_tc)
        cov_drop = round(baseline_cov - line_cov, 2)
        coverage_ok = cov_drop <= 5.0

        gate_1 = compile_ok
        gate_1_2 = compile_ok and tests_ok
        gate_1_2_3 = compile_ok and tests_ok and coverage_ok

        projects.append(OrderedDict([
            ("project", name),
            ("compile", compile_ok),
            ("passed_tests", passed),
            ("total_tests", total_tc),
            ("tests_ok", tests_ok),
            ("baseline_coverage", round(baseline_cov, 2)),
            ("line_coverage", round(line_cov, 2)),
            ("cov_drop_pp", cov_drop),
            ("coverage_ok", coverage_ok),
            ("gate_1", gate_1),
            ("gate_1_2", gate_1_2),
            ("gate_1_2_3", gate_1_2_3),
            ("step_count", info.get("step_count", 0)),
        ]))

    g1 = sum(1 for p in projects if p["gate_1"])
    g12 = sum(1 for p in projects if p["gate_1_2"])
    g123 = sum(1 for p in projects if p["gate_1_2_3"])

    summary = OrderedDict([
        ("total_projects", total),
        ("gate1", OrderedDict([
            ("count", g1),
            ("rate", round(g1 / total * 100, 2) if total else 0),
            ("label", "Gate 1: Compilation pass"),
            ("desc", 'compilation_success == True'),
        ])),
        ("gate1_2", OrderedDict([
            ("count", g12),
            ("rate", round(g12 / total * 100, 2) if total else 0),
            ("label", "Gate 1+2: Compile pass + all tests pass"),
            ("desc", 'Gate 1 OK + passed_tests == total_tests'),
        ])),
        ("gate1_2_3", OrderedDict([
            ("count", g123),
            ("rate", round(g123 / total * 100, 2) if total else 0),
            ("label", "Gate 1+2+3: Compile + all tests + coverage drop <= 5pp"),
            ("desc", 'Gate 1+2 OK + (baseline_coverage - line_coverage) <= 5'),
        ])),
    ])

    return OrderedDict([
        ("summary", summary),
        ("projects", projects),
    ])


def print_report(result: dict) -> None:
    s = result["summary"]
    total = s["total_projects"]

    print("=" * 72)
    print("  MYGRATE — Migration Evaluation Metrics")
    print("=" * 72)
    print(f"\n  Total projects: {total}\n")

    for key in ["gate1", "gate1_2", "gate1_2_3"]:
        entry = s[key]
        bar_len = 40
        filled = int(entry["rate"] / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  {entry['label']}")
        print(f"    Criteria: {entry['desc']}")
        print(f"    {entry['count']}/{total}  ({entry['rate']}%)  [{bar}]")
        print()

    # ── Detail table ──
    print("-" * 90)
    hdr = f"  {'Project':<30} {'Compile':>7} {'Tests':>12} {'Baseline':>9} {'Line':>7} {'Drop':>7} {'G1+2+3':>7}"
    print(hdr)
    print("-" * 90)

    for p in result["projects"]:
        c_icon = "✅" if p["compile"] else "❌"
        t_str = f"{p['passed_tests']}/{p['total_tests']}"
        t_icon = "✅" if p["tests_ok"] else "❌"
        g_icon = "✅" if p["gate_1_2_3"] else "❌"
        print(f"  {p['project']:<30} {c_icon:>7} {t_str:>5} {t_icon:>6} "
              f"{p['baseline_coverage']:>8.2f} {p['line_coverage']:>7.2f} "
              f"{p['cov_drop_pp']:>7.2f} {g_icon:>7}")

    print("-" * 90)

    # ── Fail breakdown ──
    fail_g1 = [p for p in result["projects"] if not p["gate_1"]]
    pass_g1_fail_g2 = [p for p in result["projects"] if p["gate_1"] and not p["gate_1_2"]]
    pass_g12_fail_g3 = [p for p in result["projects"] if p["gate_1_2"] and not p["gate_1_2_3"]]

    if fail_g1:
        print(f"\n  ❌ Fail Gate 1 (compile): {len(fail_g1)}")
        for p in fail_g1:
            print(f"     • {p['project']}")

    if pass_g1_fail_g2:
        print(f"\n  ⚠️  Pass Gate 1 but Fail Gate 2 (tests): {len(pass_g1_fail_g2)}")
        for p in pass_g1_fail_g2:
            print(f"     • {p['project']}  ({p['passed_tests']}/{p['total_tests']} tests)")

    if pass_g12_fail_g3:
        print(f"\n  ⚠️  Pass Gate 1+2 but Fail Gate 3 (coverage): {len(pass_g12_fail_g3)}")
        for p in pass_g12_fail_g3:
            print(f"     • {p['project']}  (drop: {p['cov_drop_pp']}pp)")

    print("\n" + "=" * 72)


if __name__ == "__main__":
    json_path = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--json_path" and i + 1 < len(sys.argv) - 1:
            json_path = sys.argv[i + 2]
            break

    data = load_eval(json_path)
    result = compute_metrics(data)
    print_report(result)