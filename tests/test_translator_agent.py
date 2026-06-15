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
    agent.llm = None
    result = json.loads(agent.run(json.dumps(payload, ensure_ascii=False)))

    assert result["status"] == "ok"
    assert result["project_path"] == str(project_root.resolve())
    assert result["task_count"] == 1
    assert result["change_candidates"]
    assert result["change_candidates"][0]["file_path"].replace("\\", "/") == "src/main/java/demo/Demo.java"
    assert result["target_java_version"] == "17"


def test_search_tools(tmp_path: Path) -> None:
    from src.tools.codebase_search_tools import find_code_usages, search_codebase

    project_root, _, _ = _write_sample_project(tmp_path)

    # Test AST Search (find_code_usages)
    class_usages = find_code_usages(str(project_root), "class_declaration", "Demo")
    assert len(class_usages) == 1
    assert class_usages[0]["file_path"].replace("\\", "/") == "src/main/java/demo/Demo.java"
    assert "class Demo" in class_usages[0]["snippet"]

    method_usages = find_code_usages(str(project_root), "method_invocation", "getLogger")
    assert len(method_usages) == 1
    assert "getLogger(Demo.class)" in method_usages[0]["snippet"]

    var_usages = find_code_usages(str(project_root), "variable_declarator", "LOG")
    assert len(var_usages) == 1
    assert "LOG = LoggerFactory.getLogger(Demo.class)" in var_usages[0]["snippet"]

    import_usages = find_code_usages(str(project_root), "import_declaration", "org.slf4j.Logger")
    assert len(import_usages) >= 1
    assert any("import org.slf4j.Logger;" in u["snippet"] for u in import_usages)

    # Test smart text search (search_codebase)
    text_matches = search_codebase(str(project_root), "getLogger", ["java"])
    assert len(text_matches) == 1
    assert text_matches[0]["file_path"].replace("\\", "/") == "src/main/java/demo/Demo.java"
    assert "getLogger" in text_matches[0]["line_content"]

    # Test file migration details lookup (get_file_migration_details)
    target_dir = project_root / "target"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Write dummy jdeprscan report
    with open(target_dir / "jdeprscan_report.json", "w") as f:
        json.dump({
            "steps": {
                "b2_project_scan": {
                    "for_removal": [
                        "class demo.Demo uses deprecated class org.apache.hadoop.io.Writable (forRemoval=true)"
                    ],
                    "deprecated": []
                }
            }
        }, f)
        
    # Write dummy change plan
    with open(target_dir / "mygrate_report.json", "w") as f:
        json.dump({
            "change_candidates": [
                {
                    "file_path": "src/main/java/demo/Demo.java",
                    "snippet": "dummy snippet info"
                }
            ]
        }, f)
        
    from src.tools.codebase_search_tools import get_file_migration_details
    details = get_file_migration_details(str(project_root), "src/main/java/demo/Demo.java")
    assert len(details["deprecations"]) == 1
    assert "Writable" in details["deprecations"][0]
    assert len(details["change_candidates"]) == 1
    assert details["change_candidates"][0]["snippet"] == "dummy snippet info"

    # Test write_file
    from src.tools import write_file
    write_result = write_file.func(project_path=str(project_root), file_path="test_write.txt", content="test content")
    assert "Successfully wrote" in write_result
    assert (project_root / "test" / "artifacts" / "test_write.txt").read_text() == "test content"

