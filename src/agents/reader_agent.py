from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent, ToolDefinition
from src.tools.maven_upgrade_tools import index_java_project


class ReaderAgent(BaseAgent):
    """Discovery agent: indexes codebase, parses POM, returns project info.

    It also supports a final review mode that synthesizes the best candidate
    solution and explains the selection.
    """

    def get_prompt_file(self) -> str | None:
        """Load the detailed markdown prompt for the Reader Agent."""
        return "reader.md"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="run_lightweight_index",
                description=(
                    "Index the target Java project layout, parse build manifest files (POMs), "
                    "aggregate submodule dependencies, and analyze package structures."
                ),
                func=self._tool_run_lightweight_index,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the Java project root directory",
                        }
                    },
                    "required": ["project_path"],
                },
            ),
            ToolDefinition(
                name="review_upgrade_candidates",
                description=(
                    "Evaluate compatibility solver solutions, compare runtime smoke test outcomes, "
                    "and select the final recommended dependency version configurations."
                ),
                func=self._tool_review_upgrade_candidates,
                parameters={
                    "type": "object",
                    "properties": {
                        "payload_json": {
                            "type": "string",
                            "description": "A JSON string containing the full dependency solving context (solutions, candidates, smoke test results)",
                        }
                    },
                    "required": ["payload_json"],
                },
            ),
        ]

    def _tool_run_lightweight_index(self, project_path: str = "", **kwargs) -> dict[str, Any]:
        """Tool: Run codebase indexer and POM parser."""
        try:
            print(f"-> [READER] Indexing codebase at '{project_path}'...")
            if not project_path:
                return {"status": "error", "message": "Missing project path."}
            result = index_java_project(project_path)
            return result
        except Exception as e:
            print(f"-> [READER] index_java_project exception: {e}")
            return {"status": "error", "message": str(e)}

    def _tool_review_upgrade_candidates(self, payload_json: str | dict = "{}", **kwargs) -> dict[str, Any]:
        """Tool: Run upgrade candidate final review."""
        try:
            print("-> [READER] Reviewing candidate solutions...")
            payload = {}
            if payload_json:
                if isinstance(payload_json, dict):
                    payload = payload_json
                else:
                    try:
                        payload = json.loads(payload_json)
                    except json.JSONDecodeError:
                        return {"status": "error", "message": "payload_json must be valid JSON."}
            
            review = self.review_candidates(payload)
            return review
        except Exception as e:
            print(f"-> [READER] review_upgrade_candidates exception: {e}")
            return {"status": "error", "message": str(e)}

    def review_candidates(self, payload: dict) -> dict:
        summary = self._build_fallback_review(payload)

        if self.llm is None:
            return summary

        system_prompt = (
            "You are the final review agent for a Java dependency migration pipeline. "
            "Use the provided JSON context to reason over every candidate solution, prefer smoke-tested PASS "
            "solutions, and select exactly one final recommendation. Return only valid JSON with keys: "
            "status, selected_solution, selected_solution_index, old_system_state, target_system_state, "
            "candidate_assessment, what_was_done, why_selected, risks, next_steps, markdown_report."
        )
        user_prompt = (
            "JSON context:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}\n\n"
            "Be explicit about what the system already had, what was validated, what the target stack becomes, "
            "which candidates passed, and why the chosen solution is preferred over the other valid candidates. "
            "The markdown_report must be a documented Markdown summary with sections: Current Codebase, "
            "Candidate Solutions, Selected Recommendation, Why This Choice, Remaining Risks, and Next Steps."
        )

        try:
            response = self.llm.invoke([
                ("system", system_prompt),
                ("user", user_prompt),
            ])
            content = getattr(response, "content", "") or ""
            if content.startswith("```"):
                content = re.sub(r"^```[a-zA-Z]*\n|```$", "", content, flags=re.MULTILINE).strip()
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                parsed = self._complete_review(parsed, summary)
                return parsed
        except Exception as e:
            print(f"-> [READER] LLM review fallback: {e}")
            pass

        return summary

    def _looks_like_final_review(self, instruction: str) -> bool:
        lowered = instruction.lower()
        return any(token in lowered for token in ["candidate solutions", "final review", "select the best", "why selected", "smoke_test_results"])

    def _build_fallback_review(self, payload: dict) -> dict:
        solutions = payload.get("solutions", []) or []
        smoke_results = payload.get("smoke_test_results", []) or []
        best_solution = payload.get("best_solution") or {}

        selected_solution = best_solution
        selected_index = self._solution_index(solutions, selected_solution)
        why_selected = "Selected the highest-confidence solution available from the validated pipeline outputs."
        passed = [item for item in smoke_results if item.get("result", {}).get("status") == "PASS"]
        if passed:
            ranked = sorted(
                passed,
                key=lambda item: self._solution_score(item.get("solution", {}), payload),
                reverse=True,
            )
            selected_solution = ranked[0].get("solution", selected_solution)
            selected_index = self._solution_index(solutions, selected_solution)
            why_selected = (
                "Selected a smoke-tested PASS solution with the strongest compatibility score: "
                "it passed runtime class-loading, upgrades further within the validated candidate set, "
                "and has the lowest detected risk among the validated candidates."
            )
        elif solutions:
            ranked = sorted(
                enumerate(solutions, start=1),
                key=lambda item: self._solution_score(item[1], payload),
                reverse=True,
            )
            selected_index, selected_solution = ranked[0]
            why_selected = (
                "No smoke-tested PASS was available, so ReaderAgent selected the solver output with the best "
                "available compatibility profile."
            )

        candidate_assessment = self._assess_candidates(payload, selected_solution)

        review = {
            "status": "ok",
            "selected_solution": selected_solution,
            "selected_solution_index": selected_index,
            "old_system_state": {
                "project_path": payload.get("project_path"),
                "project_type": payload.get("project_type"),
                "target_java": payload.get("target_java"),
                "dependency_count": len(payload.get("dependencies", [])),
                "dependencies": [
                    {
                        "library": f"{dep.get('groupId')}:{dep.get('artifactId')}",
                        "version": dep.get("version"),
                        "scope": dep.get("scope"),
                    }
                    for dep in payload.get("dependencies", [])
                ],
                "candidate_count": len(payload.get("candidates", {})),
                "solution_count": len(solutions),
                "smoke_test_count": len(smoke_results),
                "solver_method": payload.get("solver_method"),
            },
            "target_system_state": {
                "selected_dependencies": selected_solution,
                "target_java": payload.get("target_java"),
                "expected_outcome": f"A Java {payload.get('target_java', 'target')}-compatible dependency set with validated runtime behavior.",
            },
            "candidate_assessment": candidate_assessment,
            "what_was_done": [
                "Indexed the Java project and parsed its manifest.",
                "Fetched candidate versions from Maven Central.",
                "Ran bytecode and compile checks.",
                "Modeled transitive constraints and solved the candidate graph.",
                "Ran runtime smoke tests for the top solutions.",
            ],
            "why_selected": why_selected,
            "risks": [
                "Smaller smoke-test coverage may still miss runtime edge cases.",
                "Transitive dependency drift can still affect downstream consumers.",
            ],
            "next_steps": [
                "Use the selected dependency set as the migration baseline.",
                "If desired, rerun on a broader candidate window for more confidence.",
            ],
        }
        review["markdown_report"] = self._build_markdown_report(review)
        return review

    def _complete_review(self, parsed: dict, fallback: dict) -> dict:
        for key, value in fallback.items():
            if key not in parsed or parsed.get(key) in (None, "", []):
                parsed[key] = value
        if not parsed.get("markdown_report"):
            parsed["markdown_report"] = self._build_markdown_report(parsed)
        return parsed

    def _build_markdown_report(self, review: dict) -> str:
        old_state = review.get("old_system_state", {}) or {}
        target_state = review.get("target_system_state", {}) or {}
        candidates = review.get("candidate_assessment", []) or []
        selected = review.get("selected_solution", {}) or {}
        selected_index = review.get("selected_solution_index")

        lines = [
            "# ReaderAgent Final Migration Review",
            "",
            "## Current Codebase",
            "",
            f"- Project path: `{old_state.get('project_path') or 'n/a'}`",
            f"- Project type: `{old_state.get('project_type') or 'n/a'}`",
            f"- Target Java requested: `{old_state.get('target_java') or target_state.get('target_java') or 'n/a'}`",
            f"- Dependencies found: `{old_state.get('dependency_count', 0)}`",
            f"- Solver method: `{old_state.get('solver_method') or 'n/a'}`",
            f"- Candidate library sets: `{old_state.get('candidate_count', 0)}`",
            f"- Candidate solutions: `{old_state.get('solution_count', 0)}`",
            f"- Smoke tests executed: `{old_state.get('smoke_test_count', 0)}`",
            "",
            "### Existing Dependencies",
            "",
        ]

        dependencies = old_state.get("dependencies", []) or []
        if dependencies:
            lines.extend(["| Library | Current version | Scope |", "| --- | --- | --- |"])
            for dep in dependencies:
                lines.append(
                    f"| `{dep.get('library', 'n/a')}` | `{dep.get('version', 'n/a')}` | `{dep.get('scope', 'n/a')}` |"
                )
        else:
            lines.append("- No dependency details were available in the review payload.")

        lines.extend(["", "## Candidate Solutions", ""])
        lines.extend(
            [
                "Selection policy: prefer runtime `PASS`, then stronger static compatibility, fewer warnings, "
                "more actual upgrades from the current POM, and newer validated versions.",
                "",
            ]
        )
        if candidates:
            lines.extend(["| # | Smoke status | Selected | Dependencies | Assessment |", "| --- | --- | --- | --- | --- |"])
            for candidate in candidates:
                solution_text = self._format_solution_inline(candidate.get("solution", {}))
                selected_text = "yes" if candidate.get("selected") else "no"
                reason = str(candidate.get("reason", "")).replace("|", "\\|")
                lines.append(
                    f"| {candidate.get('index', 'n/a')} | `{candidate.get('smoke_status', 'n/a')}` | "
                    f"{selected_text} | {solution_text} | {reason} |"
                )
        else:
            lines.append("- No solver candidate was available.")

        lines.extend(["", "## Selected Recommendation", ""])
        if selected:
            if selected_index:
                lines.append(f"ReaderAgent selected candidate **#{selected_index}**.")
            lines.append("")
            for lib_key, version in selected.items():
                lines.append(f"- `{lib_key}` -> `{version}`")
        else:
            lines.append("No final dependency recommendation was selected.")

        lines.extend(
            [
                "",
                "## Target System",
                "",
                f"- Target Java: `{target_state.get('target_java') or old_state.get('target_java') or 'n/a'}`",
                f"- Expected outcome: {target_state.get('expected_outcome') or 'n/a'}",
                "",
                "## Why This Choice",
                "",
                review.get("why_selected") or "No rationale was provided.",
                "",
                "## Work Completed",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in review.get("what_was_done", []) or ["No completed work summary was provided."])

        lines.extend(["", "## Remaining Risks", ""])
        lines.extend(f"- {item}" for item in review.get("risks", []) or ["No remaining risks were reported."])

        lines.extend(["", "## Next Steps", ""])
        lines.extend(f"- {item}" for item in review.get("next_steps", []) or ["No next steps were provided."])

        return "\n".join(lines)

    def _format_solution_inline(self, solution: dict) -> str:
        if not isinstance(solution, dict) or not solution:
            return "`n/a`"
        return "<br>".join(f"`{lib}` -> `{version}`" for lib, version in solution.items())

    def _solution_index(self, solutions: list, selected_solution: dict) -> int | None:
        if not selected_solution:
            return None
        normalized_selected = self._normalize_solution(selected_solution)
        for index, solution in enumerate(solutions, start=1):
            if self._normalize_solution(solution) == normalized_selected:
                return index
        return None

    def _normalize_solution(self, solution: dict) -> dict:
        if not isinstance(solution, dict):
            return {}
        return {str(key): str(value) for key, value in solution.items()}

    def _solution_score(self, solution: dict, payload: dict) -> tuple:
        normalized = self._normalize_solution(solution)
        smoke_results = payload.get("smoke_test_results", []) or []
        pass_bonus = 0
        for item in smoke_results:
            if self._normalize_solution(item.get("solution", {})) == normalized:
                status = item.get("result", {}).get("status")
                pass_bonus = 100 if status == "PASS" else 20 if status == "SKIP" else 0
                break

        step3_reports = payload.get("step3_reports", {}) or {}
        current_versions = self._current_version_map(payload)
        warnings = 0
        compatible = 0
        upgrade_count = 0
        freshness_score = 0
        for lib_key, version in normalized.items():
            report = step3_reports.get(f"{lib_key}:{version}", {})
            status = report.get("analysis", {}).get("compatibility_status")
            if status == "Warning":
                warnings += 1
            elif status == "Yes":
                compatible += 1
            if current_versions.get(lib_key) and current_versions.get(lib_key) != version:
                upgrade_count += 1
            freshness_score += self._version_score(version)

        return (pass_bonus, compatible, -warnings, upgrade_count, freshness_score, len(normalized))

    def _current_version_map(self, payload: dict) -> dict:
        current = {}
        for dep in payload.get("dependencies", []) or []:
            group_id = dep.get("groupId")
            artifact_id = dep.get("artifactId")
            version = dep.get("version")
            if group_id and artifact_id and version:
                current[f"{group_id}:{artifact_id}"] = str(version)
        return current

    def _version_score(self, version: str) -> int:
        import re
        parts = [int(part) for part in re.findall(r"\d+", str(version))[:4]]
        while len(parts) < 4:
            parts.append(0)
        major, minor, patch, build = parts
        return major * 1_000_000_000 + minor * 1_000_000 + patch * 1_000 + build

    def _assess_candidates(self, payload: dict, selected_solution: dict) -> list:
        solutions = payload.get("solutions", []) or []
        smoke_results = payload.get("smoke_test_results", []) or []
        assessments = []
        selected = self._normalize_solution(selected_solution)

        for index, solution in enumerate(solutions, start=1):
            normalized = self._normalize_solution(solution)
            smoke_status = "NOT_RUN"
            smoke_reason = ""
            for item in smoke_results:
                if self._normalize_solution(item.get("solution", {})) == normalized:
                    result = item.get("result", {})
                    smoke_status = result.get("status", smoke_status)
                    smoke_reason = result.get("reason") or result.get("stage") or ""
                    break

            assessments.append(
                {
                    "index": index,
                    "solution": solution,
                    "smoke_status": smoke_status,
                    "selected": normalized == selected,
                    "reason": self._candidate_reason(smoke_status, normalized == selected, smoke_reason),
                }
            )
        return assessments

    def _candidate_reason(self, smoke_status: str, selected: bool, smoke_reason: str) -> str:
        if selected and smoke_status == "PASS":
            return "Chosen because it passed runtime smoke testing and ranked highest by compatibility, upgrade coverage, and version freshness."
        if selected:
            return "Chosen as the best available solver output because no PASS candidate was available."
        if smoke_status == "PASS":
            return "Valid candidate, but ranked behind the selected solution by compatibility, upgrade coverage, or version freshness."
        if smoke_status in {"FAIL", "ERROR"}:
            return f"Rejected because smoke testing did not pass{': ' + smoke_reason if smoke_reason else ''}."
        return "Kept as a solver candidate but not selected because it lacks stronger runtime validation."

    def _post_process(self, results: dict[str, Any], instruction: str, payload: dict[str, Any]) -> str:
        """Post-process deterministic tool results."""
        merged = dict(results)
        
        # Merge run_lightweight_index results if present
        index_res = results.get("run_lightweight_index")
        if isinstance(index_res, dict):
            for key, val in index_res.items():
                if key not in merged or not merged[key]:
                    merged[key] = val
                
        # Merge review_upgrade_candidates results if present
        review_res = results.get("review_upgrade_candidates")
        if isinstance(review_res, dict):
            for key, val in review_res.items():
                if key not in merged or not merged[key]:
                    merged[key] = val
                
        return json.dumps(merged, ensure_ascii=False, indent=2, default=str)
