"""
Mock test for build_translation_report — xem no tra ra cai gi voi du lieu that.

Chay:  python -m tests.test_build_translation_report
"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.tools.change_finder import build_translation_report, find_change_candidates


def main():
    cantor_path = str(project_root / "freshbrew_data" / "cantor")
    focus_path = str(project_root / "dependency_focus_scopes.json")
    scopes_path = str(project_root / "affected_scopes_cantor.json")

    print("=" * 70)
    print("MOCK TEST: build_translation_report")
    print("=" * 70)

    # Test 1: file paths
    print("\n-- Test 1: build_translation_report voi file paths --")
    print(f"  Project: {cantor_path}")
    print(f"  Focus report: {focus_path}")
    print(f"  Affected scopes: {scopes_path}")

    report = build_translation_report(
        cantor_path,
        focus_report_path=focus_path,
        affected_scopes_path=scopes_path,
    )

    print(f"\n  Status: {report['status']}")
    print(f"  Project path: {report['project_path']}")
    print(f"  Candidate count: {report['summary']['candidate_count']}")
    print(f"  Files covered: {report['summary']['files_covered']}")

    if report["change_candidates"]:
        print(f"\n  -- Change Candidates ({len(report['change_candidates'])}) --")
        for i, candidate in enumerate(report["change_candidates"][:5], 1):
            print(f"\n  [{i}] {candidate['file_path']}")
            print(f"      Lines: {candidate['start_line']}-{candidate['end_line']}")
            print(f"      Type: {candidate['match_type']}")
            print(f"      Dependency: {candidate['dependency']}")
            print(f"      Reason: {candidate['reason']}")
            snippet_lines = candidate['snippet'].split('\n')[:3]
            for line in snippet_lines:
                print(f"      | {line}")
            if len(candidate['snippet'].split('\n')) > 3:
                print(f"      | ... ({len(candidate['snippet'].split(chr(10)))} lines total)")
    else:
        print("\n  WARNING: No change candidates found!")

    # Test 2: inline data
    print("\n\n-- Test 2: build_translation_report voi inline data --")

    dependency_focus = [
        {
            "dependency": "org.apache.hadoop:hadoop-common",
            "current_version": "2.2.0",
            "target_version": "3.5.0",
            "file_path": "src/main/java/com/adroll/cantor/HLLWritable.java",
            "start_line": 4,
            "end_line": 14,
            "hit_lines": [9],
        },
        {
            "dependency": "org.slf4j:slf4j-api",
            "current_version": "1.7.5",
            "target_version": "1.7.36",
            "file_path": "src/main/java/com/adroll/cantor/HLLWritable.java",
            "start_line": 5,
            "end_line": 27,
            "hit_lines": [10, 11, 22],
        },
    ]

    affected_scopes = [
        {
            "scope_id": "scope-3111a2a9",
            "capture_name": "import",
            "start_byte": 161,
            "end_byte": 198,
            "legacy_hits": ["Writable", "hadoop", "org.apache.hadoop"],
            "code_snippet": "import org.apache.hadoop.io.Writable;",
            "file_path": "src/main/java/com/adroll/cantor/HLLWritable.java",
        },
        {
            "scope_id": "scope-6e74b865",
            "capture_name": "field",
            "start_byte": 488,
            "end_byte": 565,
            "legacy_hits": ["Logger", "LoggerFactory"],
            "code_snippet": "private static final Logger LOG = LoggerFactory.getLogger(HLLWritable.class);",
            "file_path": "src/main/java/com/adroll/cantor/HLLWritable.java",
        },
    ]

    report2 = build_translation_report(
        cantor_path,
        dependency_focus=dependency_focus,
        affected_scopes=affected_scopes,
        migration_tasks=[
            {"title": "Upgrade hadoop-common 2.2.0 -> 3.5.0"},
            {"title": "Upgrade slf4j-api 1.7.5 -> 1.7.36"},
        ],
    )

    print(f"  Status: {report2['status']}")
    print(f"  Task count: {report2['task_count']}")
    print(f"  Task summaries: {report2['task_summaries']}")
    print(f"  Candidate count: {report2['summary']['candidate_count']}")
    print(f"  Files covered: {report2['summary']['files_covered']}")

    for i, candidate in enumerate(report2["change_candidates"], 1):
        print(f"\n  [{i}] {candidate['file_path']}:{candidate['start_line']}-{candidate['end_line']}")
        print(f"      Type: {candidate['match_type']}")
        print(f"      Dependency: {candidate['dependency']}")
        print(f"      Reason: {candidate['reason']}")

    # Test 3: find_change_candidates truc tiep
    print("\n\n-- Test 3: find_change_candidates truc tiep --")

    candidates = find_change_candidates(
        cantor_path,
        dependency_focus=dependency_focus,
        affected_scopes=affected_scopes,
    )

    print(f"  Total candidates: {len(candidates)}")
    for i, c in enumerate(candidates, 1):
        print(f"  [{i}] {c['file_path']} L{c['start_line']}-L{c['end_line']} | "
              f"type={c['match_type']} | dep={c['dependency']}")

    # Full report JSON
    print("\n\n-- Full Report JSON (Test 2) --")
    print(json.dumps(report2, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
