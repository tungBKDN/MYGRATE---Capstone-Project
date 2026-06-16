from __future__ import annotations

import json
from unittest.mock import patch
from src.agents.architect_agent import ArchitectAgent


@patch("src.agents.architect_agent.run_upgrade_pipeline")
def test_architect_agent_deterministic_run(mock_pipeline) -> None:
    # Setup mock return value for 7-step upgrade pipeline
    mock_pipeline.return_value = {
        "status": "ok",
        "solutions": [{"org.slf4j:slf4j-api": "1.7.36"}],
        "smoke_test_results": [{"solution": {"org.slf4j:slf4j-api": "1.7.36"}, "result": {"status": "PASS"}}],
        "conflict_edges": []
    }

    dependencies = [{"groupId": "org.slf4j", "artifactId": "slf4j-api", "version": "1.7.5"}]
    payload = {
        "dependencies": dependencies,
        "target_java_version": "17"
    }

    agent = ArchitectAgent()
    
    # Run the ReAct agent (falls back to deterministic tools sequence when no LLM is configured)
    result_str = agent.run(json.dumps(payload))
    result = json.loads(result_str)

    # Validate output structure matches LangGraph expectations
    assert result["status"] == "ok"
    assert "solutions" in result
    assert result["solutions"] == [{"org.slf4j:slf4j-api": "1.7.36"}]
    assert "smoke_test_results" in result
    assert result["smoke_test_results"][0]["result"]["status"] == "PASS"
    assert "conflict_edges" in result
