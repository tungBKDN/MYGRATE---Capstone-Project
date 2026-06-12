"""Unit tests for TranslatorAgent_2 new tools and overlap validation checks."""
import json
import tempfile
from pathlib import Path
from src.agents.translator_agent_2 import TranslatorAgent_2


def test_list_project_files(tmp_path):
    # Setup temporary directory structure
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    (project_dir / ".git").mkdir()
    (project_dir / "target").mkdir()
    (project_dir / "src" / "main" / "java").mkdir(parents=True)
    
    # Write some files
    (project_dir / "pom.xml").write_text("<project></project>", encoding="utf-8")
    (project_dir / "src" / "main" / "java" / "Main.java").write_text("public class Main {}", encoding="utf-8")
    (project_dir / "target" / "ignored.class").write_text("", encoding="utf-8")
    (project_dir / ".git" / "config").write_text("", encoding="utf-8")
    
    agent = TranslatorAgent_2()
    agent.project_path = str(project_dir)
    
    # Check project-wide listing
    result = agent._tool_list_project_files("")
    
    # Verification
    assert "pom.xml" in result
    assert "src/" in result
    assert "Main.java" in result
    
    # Excluded folders check
    assert "target/" not in result
    assert "ignored.class" not in result
    assert ".git/" not in result
    
    # Check relative path listing
    result_sub = agent._tool_list_project_files("src/main/java")
    assert "Main.java" in result_sub
    print("test_list_project_files PASSED")


def test_apply_edits_overlap(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    file_path = project_dir / "App.java"
    # 5 lines
    content = "line1\nline2\nline3\nline4\nline5"
    file_path.write_text(content, encoding="utf-8")
    
    agent = TranslatorAgent_2()
    agent.project_path = str(project_dir)
    
    # 1. Non-overlapping edits should succeed
    edits_non_overlap = [
        {"start_line": 2, "end_line": 2, "replacement": "new_line2"},
        {"start_line": 4, "end_line": 4, "replacement": "new_line4"},
    ]
    res = agent._tool_apply_edits("App.java", edits_non_overlap)
    assert "Applied 2 edit(s)" in res
    
    # Verify file content
    updated = file_path.read_text(encoding="utf-8")
    assert updated == "line1\nnew_line2\nline3\nnew_line4\nline5"
    
    # 2. Overlapping edits should fail validation
    edits_overlap = [
        {"start_line": 2, "end_line": 3, "replacement": "overlap_chunk1"},
        {"start_line": 3, "end_line": 4, "replacement": "overlap_chunk2"},
    ]
    res_err = agent._tool_apply_edits("App.java", edits_overlap)
    assert "Error: Overlapping edits detected" in res_err
    print("test_apply_edits_overlap PASSED")


def test_apply_edits_pom(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    
    pom_file = project_dir / "pom.xml"
    pom_content = """<?xml version='1.0' encoding='UTF-8'?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <dependencies>
    <dependency>
      <groupId>org.sonarsource.sonarqube</groupId>
      <artifactId>sonar-plugin-api</artifactId>
      <version>9.3.0.51899</version>
    </dependency>
  </dependencies>
</project>
"""
    pom_file.write_text(pom_content, encoding="utf-8")
    
    agent = TranslatorAgent_2()
    agent.project_path = str(project_dir)
    
    # Try editing version
    edits = [
        {"start_line": 7, "end_line": 7, "replacement": "      <version>8.9.10.61524</version>"},
    ]
    res = agent._tool_apply_edits("pom.xml", edits)
    print("test_apply_edits_pom result:", res)
    assert "Applied 1 edit(s)" in res
    
    # Check that it actually changed
    updated = pom_file.read_text(encoding="utf-8")
    assert "8.9.10.61524" in updated
    print("test_apply_edits_pom PASSED")


if __name__ == "__main__":
    import sys
    # Create a dummy temp directory to run tests in standalone execution
    with tempfile.TemporaryDirectory() as td:
        test_list_project_files(Path(td))
        test_apply_edits_overlap(Path(td))
        test_apply_edits_pom(Path(td))
    print("\nAll TranslatorAgent_2 tools tests PASSED!")

