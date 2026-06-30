from __future__ import annotations

import json
from src.agents.supervisor import SupervisorAgent


def test_supervisor_agent_deterministic_routing_no_project_type() -> None:
    # Test case: Unindexed project (no project_type/dependencies)
    state = {
        "project_path": "/dummy/project",
        "project_type": "unknown",
        "target_java_version": "17",
        "dependencies": [],
        "messages": [],
        "completed_tasks_summary": [],
        "last_subagent_result": "",
        "current_instruction": "",
        "next_node": "supervisor",
    }
    
    agent = SupervisorAgent()
    agent.llm = None
    update = agent.process(state)
    
    # Should route to architect to scan project
    assert update["next_node"] == "architect"
    assert "index" in update["current_instruction"].lower()


def test_supervisor_agent_deterministic_routing_indexed_no_solutions() -> None:
    # Test case: Indexed project but no compatibility candidates/solutions yet
    state = {
        "project_path": "/dummy/project",
        "project_type": "java",
        "target_java_version": "17",
        "dependencies": [{"groupId": "org.slf4j", "artifactId": "slf4j-api", "version": "1.7.5"}],
        "messages": [],
        "completed_tasks_summary": [],
        "last_subagent_result": "Index complete",
        "current_instruction": "",
        "next_node": "supervisor",
    }
    
    agent = SupervisorAgent()
    agent.llm = None
    update = agent.process(state)
    
    # Should route to architect to solve constraints
    assert update["next_node"] == "architect"
    assert "solve" in update["current_instruction"].lower()


def test_supervisor_agent_deterministic_routing_solutions_found() -> None:
    # Test case: Solutions found, sequential fallback routes to translator
    state = {
        "project_path": "/dummy/project",
        "project_type": "java",
        "target_java_version": "17",
        "dependencies": [{"groupId": "org.slf4j", "artifactId": "slf4j-api", "version": "1.7.5"}],
        "messages": [],
        "completed_tasks_summary": [],
        "last_subagent_result": '{"status": "ok", "solutions": [{"org.slf4j:slf4j-api": "1.7.36"}]}',
        "current_instruction": "",
        "next_node": "supervisor",
    }
    
    agent = SupervisorAgent()
    agent.llm = None
    update = agent.process(state)
    
    # Should route to translator directly in deterministic sequential mode
    assert update["next_node"] == "translator"
    assert "Translate" in update["current_instruction"]
