from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agents.translator_agent import TranslatorAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a translator-agent smoke test")
    parser.add_argument("--project-path", type=str, required=True, help="Path to the Java project")
    parser.add_argument("--dependency-focus", type=str, default="dependency_focus_scopes.json", help="Path to dependency focus JSON")
    parser.add_argument("--affected-scopes", type=str, default="affected_scopes_cantor.json", help="Path to affected scopes JSON")
    parser.add_argument("--target-java", type=str, default="17", help="Target Java version")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    payload = {
        "project_path": str(Path(args.project_path).expanduser().resolve()),
        "target_java_version": args.target_java,
        "project_type": "java",
        "current_instruction": "CLI translator smoke run",
        "migration_tasks": [
            {"title": "Review dependency scope changes"},
            {"title": "Prepare migration patch plan"},
        ],
        "dependency_focus_report_path": str(Path(args.dependency_focus).expanduser().resolve()),
        "affected_scopes_path": str(Path(args.affected_scopes).expanduser().resolve()),
    }

    agent = TranslatorAgent()
    result = json.loads(agent.run(json.dumps(payload, ensure_ascii=False)))

    print(json.dumps(
        {
            "status": result.get("status"),
            "project_path": result.get("project_path"),
            "task_count": result.get("task_count"),
            "candidate_count": result.get("summary", {}).get("candidate_count"),
            "files_covered": result.get("summary", {}).get("files_covered"),
            "first_candidate": result.get("change_candidates", [{}])[0] if result.get("change_candidates") else None,
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
