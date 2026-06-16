"""Unit tests for TranslatorAgent tools and overlap validation checks."""
import json
import tempfile
import sys
from pathlib import Path
# Add project root to sys.path to allow running from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.translator_agent import TranslatorAgent


def test_list_project_files(tmp_path):
    # Setup temporary directory structure
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    (project_dir / ".git").mkdir()
    (project_dir / "target").mkdir()
    (project_dir / "src" / "main" / "java").mkdir(parents=True)
    
    # Write some files
    (project_dir / "pom.xml").write_text("<project></project>", encoding="utf-8")
    (project_dir / "src" / "main" / "java" / "Main.java").write_text("public class Main {}", encoding="utf-8")
    (project_dir / "target" / "ignored.class").write_text("", encoding="utf-8")
    (project_dir / ".git" / "config").write_text("", encoding="utf-8")
    
    agent = TranslatorAgent()
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
    project_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = project_dir / "App.java"
    # 5 lines
    content = "line1\nline2\nline3\nline4\nline5"
    file_path.write_text(content, encoding="utf-8")
    
    agent = TranslatorAgent()
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
    project_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    agent = TranslatorAgent()
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


def test_reward_hacking_prevention(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Test pom.xml setting skipTests
    pom_file = project_dir / "pom.xml"
    pom_file.write_text("<project></project>", encoding="utf-8")
    
    agent = TranslatorAgent()
    agent.project_path = str(project_dir)
    agent._allow_test_edits = True
    
    edits_pom_hack = [
        {"start_line": 1, "end_line": 1, "replacement": "<project><properties><skipTests>true</skipTests></properties></project>"}
    ]
    res = agent._tool_apply_edits("pom.xml", edits_pom_hack)
    assert "REWARD HACKING DETECTED" in res
    
    # 2. Test Java test file adding @Ignore/@Disabled
    test_file = project_dir / "src" / "test" / "java" / "MyTest.java"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_content = """package org.test;
import org.junit.Test;
import static org.junit.Assert.assertTrue;
public class MyTest {
    @Test
    public void testOne() {
        assertTrue(true);
    }
}
"""
    test_file.write_text(test_content, encoding="utf-8")
    
    # Try adding @Ignore
    edits_ignore_hack = [
        {"start_line": 4, "end_line": 5, "replacement": "public class MyTest {\n    @Ignore\n    @Test"}
    ]
    res_ignore = agent._tool_apply_edits("src/test/java/MyTest.java", edits_ignore_hack)
    assert "REWARD HACKING DETECTED" in res_ignore
    assert "@Ignore or @Disabled" in res_ignore
    
    # Try deleting @Test
    edits_delete_test_hack = [
        {"start_line": 4, "end_line": 5, "replacement": "public class MyTest {\n    // @Test"}
    ]
    res_del_test = agent._tool_apply_edits("src/test/java/MyTest.java", edits_delete_test_hack)
    assert "REWARD HACKING DETECTED" in res_del_test
    assert "Deleting @Test methods" in res_del_test
    
    # Try deleting assertion
    edits_delete_assert_hack = [
        {"start_line": 6, "end_line": 8, "replacement": "    public void testOne() {\n        // deleted\n    }"}
    ]
    res_del_assert = agent._tool_apply_edits("src/test/java/MyTest.java", edits_delete_assert_hack)
    assert "REWARD HACKING DETECTED" in res_del_assert
    assert "Deleting assertions" in res_del_assert
    
    # Try adding early return
    edits_early_return = [
        {"start_line": 6, "end_line": 8, "replacement": "    public void testOne() {\n        return;\n        assertTrue(true);\n    }"}
    ]
    res_return = agent._tool_apply_edits("src/test/java/MyTest.java", edits_early_return)
    assert "REWARD HACKING DETECTED" in res_return
    assert "Adding early return" in res_return
    
    # Verify write_file also blocks reward hacking
    res_write_hack = agent._tool_write_file("src/test/java/MyTest.java", "package org.test; public class MyTest {}")
    assert "REWARD HACKING DETECTED" in res_write_hack

    print("test_reward_hacking_prevention PASSED")


def test_code_lock(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    
    main_file = project_dir / "src" / "main" / "java" / "Main.java"
    main_file.parent.mkdir(parents=True, exist_ok=True)
    main_file.write_text("public class Main {}", encoding="utf-8")
    
    test_file = project_dir / "src" / "test" / "java" / "MainTest.java"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("public class MainTest {}", encoding="utf-8")
    
    agent = TranslatorAgent()
    agent.project_path = str(project_dir)
    agent._allow_test_edits = True
    
    # 1. Main source NOT locked initially -> edit main source should pass
    edits = [{"start_line": 1, "end_line": 1, "replacement": "public class Main { // edit1 }"}]
    res = agent._tool_apply_edits("src/main/java/Main.java", edits)
    assert "Applied 1 edit(s)" in res
    
    # Lock main source
    agent._main_source_locked = True
    
    # 2. Main source locked -> edit main source should be blocked
    res_blocked = agent._tool_apply_edits("src/main/java/Main.java", edits)
    assert "🔒 CODE LOCK" in res_blocked
    
    # 3. Main source locked -> edit test source should pass
    test_edits = [{"start_line": 1, "end_line": 1, "replacement": "public class MainTest { // test edit }"}]
    res_test = agent._tool_apply_edits("src/test/java/MainTest.java", test_edits)
    assert "Applied 1 edit(s)" in res_test
    print("test_code_lock PASSED")


def test_check_class_batch(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    agent = TranslatorAgent()
    agent.project_path = str(project_dir)
    
    # Mocking _find_jar_in_m2 and _list_classes_in_jar to avoid real network/m2 local dependency
    agent._find_jar_in_m2 = lambda g, a, v: "/dummy/jar/path.jar"
    agent._list_classes_in_jar = lambda p: ["org.sonar.api.batch.postjob.PostJob", "org.sonar.api.batch.ScannerSide"]
    
    # Check batch lookup
    res = agent._tool_check_class(class_names=["org.sonar.api.batch.postjob.PostJob", "org.sonar.api.Unknown"])
    assert "org.sonar.api.batch.postjob.PostJob" in res
    assert res["org.sonar.api.batch.postjob.PostJob"]["exists"] is True
    assert "org.sonar.api.Unknown" in res
    assert res["org.sonar.api.Unknown"]["exists"] is False
    
    # Check legacy single lookup fallback
    res_single = agent._tool_check_class(class_name="org.sonar.api.batch.postjob.PostJob")
    assert "org.sonar.api.batch.postjob.PostJob" in res_single
    assert res_single["org.sonar.api.batch.postjob.PostJob"]["exists"] is True
    
    print("test_check_class_batch PASSED")


if __name__ == "__main__":
    # Create a dummy temp directory to run tests in standalone execution
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        test_list_project_files(tdp / "list")
        test_apply_edits_overlap(tdp / "overlap")
        test_apply_edits_pom(tdp / "pom")
        test_reward_hacking_prevention(tdp / "reward_hacking")
        test_code_lock(tdp / "code_lock")
        test_check_class_batch(tdp / "check_class")
    print("\nAll TranslatorAgent tools tests PASSED!")
