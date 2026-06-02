from __future__ import annotations

import json
from pathlib import Path

from src.agents.translator_agent import TranslatorAgent
from src.tools.change_finder import build_translation_report, find_change_candidates


def _write_sample_project(root: Path) -> tuple[Path, Path, Path]:
    project_root = root / "sample_project"
    project_root.mkdir()
    java_dir = project_root / "src" / "main" / "java" / "demo"
    java_dir.mkdir(parents=True)
    source_file = java_dir / "Demo.java"
    source_file.write_text(
        """package demo;

import org.apache.hadoop.io.Writable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class Demo {
    private static final Logger LOG = LoggerFactory.getLogger(Demo.class);
}
""",
        encoding="utf-8",
    )

    affected_scopes = root / "affected_scopes.json"
    affected_scopes.write_text(
        json.dumps(
            [
                {
                    "scope_id": "scope-1",
                    "capture_name": "import",
                    "start_byte": 0,
                    "end_byte": 10,
                    "legacy_hits": ["org.slf4j"],
                    "code_snippet": "import org.slf4j.Logger;",
                    "file_path": "src/main/java/demo/Demo.java",
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    dependency_focus = root / "dependency_focus_scopes.json"
    dependency_focus.write_text(
        json.dumps(
            [
                {
                    "dependency": "org.slf4j:slf4j-api",
                    "current_version": "1.7.5",
                    "target_version": "1.7.36",
                    "file_path": "src/main/java/demo/Demo.java",
                    "start_line": 3,
                    "end_line": 7,
                    "hit_lines": [4, 5],
                    "snippet": "import org.slf4j.Logger;\nimport org.slf4j.LoggerFactory;",
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    return project_root, dependency_focus, affected_scopes


def test_change_finder_builds_candidates_from_reports(tmp_path: Path) -> None:
    project_root, dependency_focus, affected_scopes = _write_sample_project(tmp_path)

    candidates = find_change_candidates(
        project_root,
        focus_report_path=dependency_focus,
        affected_scopes_path=affected_scopes,
    )

    assert len(candidates) >= 1
    first = candidates[0]
    assert first["file_path"] == "src/main/java/demo/Demo.java"
    assert first["start_line"] <= first["end_line"]
    assert "Demo.java" in first["snippet"] or "Logger" in first["snippet"]

    report = build_translation_report(
        project_root,
        migration_tasks=[{"title": "Update Hadoop and SLF4J references"}],
        focus_report_path=dependency_focus,
        affected_scopes_path=affected_scopes,
    )
    assert report["status"] == "ok"
    assert report["task_count"] == 1
    assert report["summary"]["candidate_count"] >= 1


def test_translator_agent_generates_json_plan_without_llm(tmp_path: Path) -> None:
    project_root, dependency_focus, affected_scopes = _write_sample_project(tmp_path)
    payload = {
        "project_path": str(project_root),
        "target_java_version": "17",
        "project_type": "java",
        "current_instruction": "translate migration scope",
        "migration_tasks": [{"title": "Upgrade SLF4J and Hadoop references"}],
        "dependency_focus_report_path": str(dependency_focus),
        "affected_scopes_path": str(affected_scopes),
    }

    agent = TranslatorAgent()
    result = json.loads(agent.run(json.dumps(payload, ensure_ascii=False)))

    assert result["status"] == "ok"
    assert result["project_path"] == str(project_root.resolve())
    assert result["task_count"] == 1
    assert result["change_candidates"]
    assert result["change_candidates"][0]["file_path"] == "src/main/java/demo/Demo.java"
    assert result["target_java_version"] == "17"
