import json

from src.tools.maven_upgrade_tools import run_upgrade_pipeline


class ArchitectAgent:
    """Analysis agent: runs the full 7-step dependency pipeline.

    No LLM needed — this is purely tool-driven.
    """

    def __init__(self, model_name: str = None):
        pass  # no LLM required

    def run(self, instruction: str) -> str:
        print(f"-> [ARCHITECT] Running upgrade pipeline: {instruction[:80]}...")

        # Extract params from instruction
        dependencies_json = self._extract_value(instruction, ["Dependencies", "dependencies"])
        target_java = self._extract_value(instruction, ["Target Java Version", "target_java_version"]) or "17"

        if dependencies_json:
            try:
                dependencies = json.loads(dependencies_json)
            except json.JSONDecodeError:
                return json.dumps({"status": "error", "message": "Invalid dependencies JSON."}, ensure_ascii=False)
        else:
            return json.dumps(
                {"status": "error", "message": "Missing dependencies for architect analysis."},
                ensure_ascii=False,
            )

        result = run_upgrade_pipeline(
            dependencies,
            target_java=target_java,
            logger=lambda message: print(f"-> [ARCHITECT] {message}"),
        )
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)

    def _extract_value(self, instruction: str, labels: list[str]) -> str:
        import re
        for label in labels:
            pattern = rf"{re.escape(label)}\s*:\s*(.+)"
            match = re.search(pattern, instruction, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""