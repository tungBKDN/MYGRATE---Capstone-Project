from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from src.agents.reader_agent import ReaderAgent


def test_reader_agent_initialization() -> None:
    agent = ReaderAgent()
    assert agent.model_name is not None
    assert len(agent.get_tools()) == 2


@patch("src.agents.reader_agent.index_java_project")
def test_reader_agent_phase1_lightweight_index(mock_index, tmp_path: Path) -> None:
    mock_index.return_value = {
        "status": "ok",
        "project_type": "java",
        "dependencies": [{"groupId": "org.slf4j", "artifactId": "slf4j-api", "version": "1.7.5"}],
        "project_structure": {
            "is_multi_module": False,
            "modules": [],
            "java_file_count": 5,
            "package_distribution": {"src/main/java": 5}
        }
    }

    agent = ReaderAgent()
    instruction = f"Target Project: {tmp_path}\nTarget Java Version: 17\nNhiệm vụ: Index the codebase."
    
    # Run agent in Phase 1 (Lightweight Indexing)
    result_str = agent.run(instruction)
    result = json.loads(result_str)

    assert result["status"] == "ok"
    assert result["project_type"] == "java"
    assert len(result["dependencies"]) == 1
    assert result["project_structure"]["java_file_count"] == 5


def test_reader_agent_phase2_final_candidate_review() -> None:
    # Set up dummy context payload simulating upgrade solutions and smoke test validation status
    payload = {
        "project_path": "/dummy/project",
        "project_type": "java",
        "target_java": "17",
        "dependencies": [{"groupId": "org.slf4j", "artifactId": "slf4j-api", "version": "1.7.5"}],
        "candidates": {"org.slf4j:slf4j-api": ["1.7.36"]},
        "solutions": [{"org.slf4j:slf4j-api": "1.7.36"}],
        "smoke_test_results": [
            {
                "solution": {"org.slf4j:slf4j-api": "1.7.36"},
                "result": {"status": "PASS", "log": "Smoke test passed successfully"}
            }
        ],
        "solver_method": "z3"
    }

    agent = ReaderAgent()
    instruction = f"JSON context:\n{json.dumps(payload)}\n\nNhiệm vụ: Select the best candidate solutions and output final review."
    
    # Run agent in Phase 2 (Final Candidate Review)
    result_str = agent.run(instruction)
    result = json.loads(result_str)

    assert result["status"] == "ok"
    assert result["selected_solution"] == {"org.slf4j:slf4j-api": "1.7.36"}
    assert result["selected_solution_index"] == 1
    assert "markdown_report" in result
    assert "slf4j-api" in result["markdown_report"]


@patch("src.agents.reader_agent.index_java_project")
def test_reader_agent_phase1_multi_project(mock_index, tmp_path: Path) -> None:
    mock_index.return_value = {
        "status": "ok",
        "project_path": str(tmp_path),
        "project_type": "java",
        "is_multi_project": True,
        "projects": [
            {
                "name": "project-a",
                "path": str(tmp_path / "project-a"),
                "build_system": "Maven",
                "jdk_target": "1.8",
                "java_file_count": 12,
                "framework": "Spring Boot",
                "existing_reports": {},
                "classification": "Red"
            },
            {
                "name": "project-b",
                "path": str(tmp_path / "project-b"),
                "build_system": "Maven",
                "jdk_target": "11",
                "java_file_count": 25,
                "framework": "Standard Java",
                "existing_reports": {
                    "jdeprscan": {
                        "status": "OK",
                        "summary": {
                            "project_code": {"for_removal_count": 0, "deprecated_count": 0}
                        }
                    }
                },
                "classification": "Green"
            }
        ],
        "dependencies": [],
        "markdown_report": "| Project | Build System | JDK Target | Java Files | Framework | Reports Status | Classification |\n| --- | --- | --- | --- | --- | --- | --- |\n| `project-a` | Maven | 1.8 | 12 | Spring Boot | None | **Red** |\n| `project-b` | Maven | 11 | 25 | Standard Java | jdeprscan: OK | **Green** |"
    }

    agent = ReaderAgent()
    instruction = f"Target Project: {tmp_path}\nTarget Java Version: 17\nNhiệm vụ: Index the codebase."
    
    result_str = agent.run(instruction)
    result = json.loads(result_str)

    assert result["status"] == "ok"
    assert result["is_multi_project"] is True
    assert len(result["projects"]) == 2
    assert "project-a" in result["markdown_report"]

