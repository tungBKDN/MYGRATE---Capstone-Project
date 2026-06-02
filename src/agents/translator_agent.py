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

class TranslatorAgent:
    """
    Translator agent that turns migration scope reports into actionable
    change plans.
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
        migration_tasks = self._coerce_tasks(payload.get("migration_tasks"))
        dependency_focus_report_path, affected_scopes_path = self._resolve_default_report_paths(project_path, payload)

        print(f"-> [TRANSLATOR] Building change plan for: {project_path}")

        report = build_translation_report(
            project_path,
            migration_tasks=migration_tasks,
            dependency_focus=payload.get("dependency_focus_scopes"),
            affected_scopes=payload.get("affected_scopes"),
            focus_report_path=dependency_focus_report_path,
            affected_scopes_path=affected_scopes_path,
        )

        report["project_type"] = payload.get("project_type")
        report["target_java_version"] = payload.get("target_java_version")
        report["current_instruction"] = payload.get("current_instruction") or instruction

        if self.llm is not None:
            report = self._enrich_with_llm(report, instruction)

        return json.dumps(report, ensure_ascii=False, indent=2, default=str)

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
        system_prompt = (
            "You are a translator agent for a Java migration assistant. "
            "You receive a deterministic change plan and must refine only the narrative fields. "
            "Return valid JSON with the same structure plus optional markdown_report and migration_notes."
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
