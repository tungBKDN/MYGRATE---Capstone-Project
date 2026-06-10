"""Test the recovery of tool calls from Groq schema validation errors."""
import json
from src.agents.base_agent import BaseAgent, ToolDefinition


def make_agent():
    return type("TestAgent", (BaseAgent,), {
        "get_tools": lambda self: [],
        "get_system_prompt": lambda self: "",
    })()


def test_coerce_tool_args():
    agent = make_agent()
    schema = {
        "clean": {"type": "boolean"},
        "skip_tests": {"type": "boolean"},
        "count": {"type": "integer"},
        "name": {"type": "string"},
    }

    # String booleans should be coerced
    args = {"clean": "true", "skip_tests": "false", "count": "5", "name": "test"}
    result = agent._coerce_tool_args(args, schema)
    assert result["clean"] is True
    assert result["skip_tests"] is False
    assert result["count"] == 5
    assert result["name"] == "test"

    # Already correct types should pass through
    args2 = {"clean": True, "skip_tests": False, "count": 5}
    result2 = agent._coerce_tool_args(args2, schema)
    assert result2["clean"] is True
    assert result2["skip_tests"] is False
    assert result2["count"] == 5

    print("test_coerce_tool_args PASSED")


def test_recover_from_groq_error():
    agent = make_agent()

    # Simulate the Groq 400 error with failed_generation
    failed_gen_json = json.dumps([{
        "name": "run_maven_command",
        "parameters": {
            "goal": "compile",
            "project_path": "freshbrew_data/sonar-stash",
            "clean": "true",
            "skip_tests": "false",
            "target_java_version": "17"
        }
    }])

    # Build error message mimicking Groq's format
    error_msg = (
        "Error code: 400 - {'error': {'message': \"tool call validation failed: "
        "parameters for tool run_maven_command did not match schema\", "
        "'type': 'invalid_request_error', 'code': 'tool_use_failed', "
        "'failed_generation': '" + failed_gen_json + "'}}"
    )

    class FakeError(Exception):
        pass

    fake_err = FakeError(error_msg)

    # Build a tool map with a fake run_maven_command
    def fake_maven(project_path="", goal="compile", clean=False, skip_tests=False,
                    target_java_version="17", **kw):
        return {"status": "ok", "clean_was": clean, "skip_tests_was": skip_tests}

    tool_def = ToolDefinition(
        name="run_maven_command",
        description="Test tool",
        func=fake_maven,
        parameters={
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "goal": {"type": "string"},
                "clean": {"type": "boolean"},
                "skip_tests": {"type": "boolean"},
                "target_java_version": {"type": "string"},
            },
            "required": ["goal"],
        },
    )

    tool_map = {"run_maven_command": tool_def}
    results = {}
    messages = []

    recovered = agent._try_recover_tool_calls(fake_err, tool_map, {}, results, messages)

    assert recovered is True, f"Expected True, got {recovered}"
    assert "run_maven_command" in results, "Tool was not recovered"
    r = results["run_maven_command"]
    assert r["clean_was"] is True, f"Expected True, got {r['clean_was']!r}"
    assert r["skip_tests_was"] is False, f"Expected False, got {r['skip_tests_was']!r}"
    assert len(messages) > 0, "No messages were added"

    print("test_recover_from_groq_error PASSED")


def test_non_recoverable_error():
    agent = make_agent()

    class FakeError(Exception):
        pass

    # Non-validation errors should not be recovered
    fake_err = FakeError("Connection timeout")
    result = agent._try_recover_tool_calls(fake_err, {}, {}, {}, [])
    assert result is None

    print("test_non_recoverable_error PASSED")


if __name__ == "__main__":
    test_coerce_tool_args()
    test_recover_from_groq_error()
    test_non_recoverable_error()
    print("\nAll tests PASSED!")