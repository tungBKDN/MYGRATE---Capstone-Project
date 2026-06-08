from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None

from src.tools.change_finder import build_translation_report
from src.tools.jdeprscan_pipeline import run_jdeprscan_pipeline

class TranslatorAgent:
    """
    Translator agent that turns migration scope reports into actionable change plans.

    Workflow:
        1. ROI searching: Run jdeprscan pipeline to discover deprecated API usage in both project code and dependencies.
        2. Build translation report from change candidates.
        3. Enrich with LLM if available.

    The jdeprscan report is the primary data source for deciding what code needs to change. It provides:
        - Layer 1 (project code): forRemoval and deprecated API calls
        - Layer 2 (dependencies): which JARs use deprecated APIs
        - Layer 3 (pom.xml): which dependencies have forRemoval=true
    """
    def __init__(self, model_name: str = None):
        load_dotenv()
        if model_name is None:
            model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        api_key = os.getenv("GROQ_API_KEY")
        self.llm = None
        if api_key and ChatGroq is not None:
            try:
                self.llm = ChatGroq(model_name=model_name, groq_api_key=api_key, temperature=0)
            except Exception:
                self.llm = None

    def run(self, instruction: str) -> str:
        payload = self._parse_instruction(instruction)
        project_path = self._resolve_project_path(payload, instruction)
        target_java = payload.get("target_java_version") or payload.get("target_java") or "17"
        migration_tasks = self._coerce_tasks(payload.get("migration_tasks"))
        dependency_focus_report_path, affected_scopes_path = self._resolve_default_report_paths(project_path, payload)

        print(f"-> [TRANSLATOR] Building change plan for: {project_path}")

        # ── Step 1: Run jdeprscan pipeline (B0-B3) ──
        # This is the primary data source for migration decisions.
        # It discovers deprecated API usage in project code and dependencies.
        jdeprscan_report = self._run_jdeprscan(project_path, target_java, payload)

        # ── Step 2: Build translation report from change candidates ──
        report = build_translation_report(
            project_path,
            migration_tasks=migration_tasks,
            dependency_focus=payload.get("dependency_focus_scopes"),
            affected_scopes=payload.get("affected_scopes"),
            focus_report_path=dependency_focus_report_path,
            affected_scopes_path=affected_scopes_path,
        )

        report["project_type"] = payload.get("project_type")
        report["target_java_version"] = target_java
        report["current_instruction"] = payload.get("current_instruction") or instruction

        # ── Step 3: Attach jdeprscan data to the report ──
        # This gives the LLM and downstream consumers full visibility into
        # what deprecated APIs exist in project code vs dependencies.
        if jdeprscan_report:
            report["jdeprscan"] = jdeprscan_report

        if self.llm is not None:
            report = self._enrich_with_llm(report, instruction)

        # Step 4: From ROI to Action Plan - find and use LLM to translate the raw data into specific code change recommendations, prioritizing forRemoval=true items and critical dependencies.
        

        return json.dumps(report, ensure_ascii=False, indent=2, default=str)

    def _run_jdeprscan(self, project_path: str, target_java: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Run the jdeprscan pipeline B0-B3 and return structured results.

        This is the first step in the translator workflow because it tells us
        exactly which APIs are deprecated (forRemoval=true) vs merely deprecated,
        in both the project's own code and its dependencies.

        Returns None if the pipeline fails, so the translator can still proceed
        with change_finder data alone.
        """
        try:
            print(f"-> [TRANSLATOR] Running jdeprscan pipeline for JDK {target_java}...")

            # Extract JDK paths from payload if provided
            jdk8_home = payload.get("jdk8_home")
            jdk17_home = payload.get("jdk17_home")

            result = run_jdeprscan_pipeline(
                project_path=project_path,
                target_release=str(target_java).replace("JDK ", "").replace("jdk ", ""),
                jdk8_home=jdk8_home,
                jdk17_home=jdk17_home,
                logger=lambda msg: print(f"   {msg}"),
            )

            status = result.get("status", "FAIL")
            print(f"-> [TRANSLATOR] jdeprscan pipeline: {status}")

            if status == "FAIL" and not result.get("steps", {}).get("b2_project_scan", {}).get("for_removal_count"):
                # Pipeline failed completely — return the error info but don't block
                print(f"-> [TRANSLATOR] jdeprscan errors: {result.get('errors', [])}")

            # Return the full structured report regardless of status
            # Even partial data (e.g., B3 dependency scan only) is valuable
            return result

        except Exception as e:
            print(f"-> [TRANSLATOR] jdeprscan pipeline exception: {e}")
            return None

    def _parse_instruction(self, instruction: str) -> dict[str, Any]:
        try:
            parsed = json.loads(instruction)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        payload: dict[str, Any] = {}
        for label in ["Project Path", "project_path", "Target Java Version", "target_java_version", "current_instruction"]:
            value = self._extract_value(instruction, [label])
            if value:
                payload[label.lower().replace(" ", "_")] = value
        return payload

    def _resolve_project_path(self, payload: dict[str, Any], instruction: str) -> str:
        for key in ["project_path", "project root", "project_root"]:
            value = payload.get(key)
            if value:
                return str(value)

        extracted = self._extract_value(instruction, ["Project Path", "project_path", "path"])
        if extracted:
            return extracted

        return str(Path.cwd())

    def _coerce_tasks(self, tasks: Any) -> list[dict[str, Any]]:
        if not isinstance(tasks, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in tasks:
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, str) and item.strip():
                normalized.append({"title": item.strip()})
        return normalized

    def _resolve_default_report_paths(self, project_path: str, payload: dict[str, Any]) -> tuple[str | None, str | None]:
        dependency_focus = payload.get("dependency_focus_report_path")
        affected_scopes = payload.get("affected_scopes_path")

        if dependency_focus and affected_scopes:
            return str(dependency_focus), str(affected_scopes)

        workspace_candidates = [Path.cwd(), Path(project_path).resolve().parent, Path(project_path).resolve()]

        if not dependency_focus:
            for base_dir in workspace_candidates:
                candidate = base_dir / "dependency_focus_scopes.json"
                if candidate.exists():
                    dependency_focus = candidate
                    break

        if not affected_scopes:
            for base_dir in workspace_candidates:
                for filename in ["affected_scopes_cantor.json", "affected_scopes.json"]:
                    candidate = base_dir / filename
                    if candidate.exists():
                        affected_scopes = candidate
                        break
                if affected_scopes:
                    break

        return (
            str(dependency_focus) if dependency_focus else None,
            str(affected_scopes) if affected_scopes else None,
        )

    def _enrich_with_llm(self, report: dict[str, Any], instruction: str) -> dict[str, Any]:
        # Build context-aware system prompt based on available data
        jdeprscan = report.get("jdeprscan")
        jdeprscan_context = ""
        if jdeprscan:
            summary = jdeprscan.get("summary", {})
            proj = summary.get("project_code", {})
            deps = summary.get("dependencies", {})
            pom = summary.get("pom_xml", {})
            jdeprscan_context = (
                "\n\n## jdeprscan Pipeline Results (B0-B3)\n"
                f"Pipeline status: {jdeprscan.get('status', 'unknown')}\n"
                f"Target JDK: {jdeprscan.get('target_release', 'unknown')}\n\n"
                "### Layer 1 — Project Code\n"
                f"- forRemoval APIs (will crash at runtime): {proj.get('for_removal_count', 0)}\n"
                f"- Deprecated APIs (warnings only): {proj.get('deprecated_count', 0)}\n"
                f"- Clean: {proj.get('clean', False)}\n\n"
                "### Layer 2 — Dependencies\n"
                f"- Problem JARs: {deps.get('problem_count', 0)}\n"
                f"- Critical (forRemoval>0): {deps.get('critical_count', 0)}\n"
                f"- Top issues: {json.dumps(deps.get('top_issues', []), default=str)}\n\n"
                "### Layer 3 — pom.xml (Critical Dependencies)\n"
                f"- Critical count: {pom.get('critical_count', 0)}\n"
                f"- Critical deps: {json.dumps(pom.get('critical_deps', []), default=str)}\n"
            )

        system_prompt = (
            "You are a translator agent for a Java migration assistant. "
            "You receive a deterministic change plan and jdeprscan pipeline results, "
            "and must refine the narrative fields to produce an actionable migration plan.\n\n"
            "The jdeprscan data tells you exactly which APIs are deprecated or forRemoval=true "
            "in both the project's own code and its dependencies. Use this to:\n"
            "1. Prioritize forRemoval=true items — these WILL crash at runtime if not fixed.\n"
            "2. Identify which dependencies need version upgrades or replacements.\n"
            "3. Generate specific code change recommendations for each deprecated API.\n\n"
            "Return valid JSON with the same structure plus optional markdown_report and migration_notes."
            f"{jdeprscan_context}"
        )
        user_prompt = (
            "Instruction:\n"
            f"{instruction}\n\n"
            "Existing change plan JSON:\n"
            f"{json.dumps(report, ensure_ascii=False, indent=2, default=str)}"
        )

        try:
            response = self.llm.invoke([
                ("system", system_prompt),
                ("user", user_prompt),
            ])
            content = getattr(response, "content", "") or ""
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                for key, value in report.items():
                    parsed.setdefault(key, value)
                return parsed
        except Exception:
            pass

        return report


    def _extract_value(self, instruction: str, labels: list[str]) -> str:
        import re

        for label in labels:
            pattern = rf"{re.escape(label)}\s*:\s*(.+)"
            match = re.search(pattern, instruction, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""
