from __future__ import annotations

import json
from typing import Any

from src.agents.base_agent import BaseAgent, ToolDefinition
from src.tools.maven_upgrade_tools import run_upgrade_pipeline


class ArchitectAgent(BaseAgent):
    """
    Architect agent that solves dependency compatibility constraints.

    Uses the ReAct pattern: the LLM decides which tools to call
    to solve and verify dependency combinations.

    Available tools:
        - run_upgrade_analysis: Run the full 7-step upgrade pipeline to resolve compatible combinations.
    """

    def get_prompt_file(self) -> str | None:
        """Load the detailed markdown prompt for the Architect Agent."""
        return "architect.md"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="run_upgrade_analysis",
                description=(
                    "Run the full 7-step upgrade pipeline (MavenCentral fetch, filter, static check, compile checks, "
                    "transitive constraints, Z3 solving, runtime smoke testing) to find compatible library version sets."
                ),
                func=self._tool_run_upgrade_analysis,
                parameters={
                    "type": "object",
                    "properties": {
                        "dependencies": {
                            "type": "array",
                            "description": "List of dependencies (each is a dict with groupId, artifactId, and optionally version, scope)",
                        },
                        "target_java_version": {
                            "type": "string",
                            "description": "Target JDK version (e.g., '17')",
                        },
                    },
                    "required": ["dependencies"],
                },
            )
        ]

    def _tool_run_upgrade_analysis(
        self,
        dependencies: list[dict[str, Any]] | str = "",
        target_java_version: str = "17",
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Run dependency upgrade pipeline."""
        try:
            print(f"-> [ARCHITECT] Running compatibility analysis for JDK {target_java_version}...")
            
            # Safely handle string input for dependencies
            deps = dependencies
            if isinstance(dependencies, str):
                try:
                    deps = json.loads(dependencies)
                except json.JSONDecodeError:
                    return {"status": "error", "message": "dependencies argument must be a valid JSON array or list."}

            if not isinstance(deps, list):
                return {"status": "error", "message": "dependencies argument must be a list of dependency dicts."}

            result = run_upgrade_pipeline(
                deps,
                target_java=str(target_java_version),
                logger=lambda msg: print(f"   {msg}"),
            )

            # Save full report to artifacts/ folder
            project_path = kwargs.get("project_path", "")
            if project_path:
                report_root = Path(project_path) / "artifacts"
                report_root.mkdir(parents=True, exist_ok=True)
                report_path = report_root / "upgrade_report.json"
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
                print(f"-> [ARCHITECT] Saved full upgrade report to {report_path}")

            # Return a lean version for the LLM to prevent 413 Request Too Large errors
            if self.llm is not None:
                lean_result = dict(result)
                if "step3_reports" in lean_result:
                    lean_step3 = {}
                    for key, val in lean_result["step3_reports"].items():
                        if isinstance(val, dict):
                            lean_val = dict(val)
                            if "signals" in lean_val and isinstance(lean_val["signals"], dict):
                                signals = dict(lean_val["signals"])
                                if "jdeprscan" in signals and isinstance(signals["jdeprscan"], dict):
                                    jdeprscan = dict(signals["jdeprscan"])
                                    jdeprscan.pop("output", None)
                                    jdeprscan.pop("findings", None)
                                    signals["jdeprscan"] = jdeprscan
                                lean_val["signals"] = signals
                            lean_step3[key] = lean_val
                        else:
                            lean_step3[key] = val
                    lean_result["step3_reports"] = lean_step3
                return lean_result

            return result
        except Exception as e:
            print(f"-> [ARCHITECT] run_upgrade_analysis exception: {e}")
            return {"status": "error", "message": str(e)}

    def _post_process(self, results: dict[str, Any], instruction: str, payload: dict[str, Any]) -> str:
        """Post-process deterministic tool results to extract the compatibility solver outcomes."""
        merged = dict(results)
        
        # If run_upgrade_analysis succeeded and returned a dict, merge its keys (solutions, smoke_test_results, etc.)
        analysis = results.get("run_upgrade_analysis")
        if isinstance(analysis, dict):
            for key, val in analysis.items():
                if key not in merged or not merged[key]:
                    merged[key] = val

        return json.dumps(merged, ensure_ascii=False, indent=2, default=str)