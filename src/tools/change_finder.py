from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class ChangeCandidate:
    file_path: str
    start_line: int
    end_line: int
    match_type: str
    dependency: str | None
    reason: str
    snippet: str


def _load_json_file(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _normalize_relative_path(path_value: str) -> str:
    return str(Path(path_value).as_posix()).replace("\\", "/")


def _safe_lines(text: str) -> list[str]:
    return text.splitlines()


def _cluster_lines(line_numbers: Iterable[int], gap: int = 2) -> list[list[int]]:
    ordered = sorted(set(int(line_no) for line_no in line_numbers if int(line_no) > 0))
    if not ordered:
        return []

    clusters = [[ordered[0]]]
    for line_no in ordered[1:]:
        if line_no - clusters[-1][-1] <= gap:
            clusters[-1].append(line_no)
        else:
            clusters.append([line_no])
    return clusters


def _build_snippet(lines: list[str], start_line: int, end_line: int, highlight_lines: set[int]) -> str:
    snippet_lines: list[str] = []
    for line_no in range(start_line, end_line + 1):
        marker = ">" if line_no in highlight_lines else " "
        if 1 <= line_no <= len(lines):
            snippet_lines.append(f"{line_no:5d} {marker} {lines[line_no - 1]}")
    return "\n".join(snippet_lines)


def _merge_candidates(candidates: list[ChangeCandidate]) -> list[ChangeCandidate]:
    deduped: dict[tuple[str, int, int, str, str | None], ChangeCandidate] = {}
    for candidate in candidates:
        key = (candidate.file_path, candidate.start_line, candidate.end_line, candidate.match_type, candidate.dependency)
        if key not in deduped:
            deduped[key] = candidate
    return sorted(deduped.values(), key=lambda item: (item.file_path, item.start_line, item.end_line, item.match_type))


def find_change_candidates(
    project_root: str | Path,
    *,
    focus_report_path: str | Path | None = None,
    affected_scopes_path: str | Path | None = None,
    dependency_focus: dict[str, Any] | list[dict[str, Any]] | None = None,
    affected_scopes: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build a deterministic list of migration targets from report artifacts."""

    project_root = Path(project_root).expanduser().resolve()

    if dependency_focus is None and focus_report_path is not None:
        focus_report = _load_json_file(Path(focus_report_path))
        if isinstance(focus_report, list):
            dependency_focus = focus_report

    if affected_scopes is None and affected_scopes_path is not None:
        scope_report = _load_json_file(Path(affected_scopes_path))
        if isinstance(scope_report, list):
            affected_scopes = scope_report

    candidates: list[ChangeCandidate] = []

    if isinstance(dependency_focus, list):
        for item in dependency_focus:
            if not isinstance(item, dict):
                continue
            rel_path = item.get("file_path") or item.get("path")
            if not rel_path:
                continue
            abs_path = project_root / str(rel_path)
            if not abs_path.exists():
                continue

            lines = _safe_lines(abs_path.read_text(encoding="utf-8", errors="replace"))
            start_line = int(item.get("start_line") or 1)
            end_line = int(item.get("end_line") or start_line)
            hit_lines = {int(line_no) for line_no in item.get("hit_lines", []) if str(line_no).isdigit()}
            snippet = item.get("snippet") or _build_snippet(lines, start_line, end_line, hit_lines)
            dependency = item.get("dependency")
            reason = f"Update references for {dependency}" if dependency else "Update dependency-related code references"
            candidates.append(
                ChangeCandidate(
                    file_path=_normalize_relative_path(str(rel_path)),
                    start_line=start_line,
                    end_line=end_line,
                    match_type=str(item.get("match_type") or item.get("capture_name") or "reference"),
                    dependency=str(dependency) if dependency else None,
                    reason=reason,
                    snippet=str(snippet),
                )
            )

    if isinstance(affected_scopes, list):
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in affected_scopes:
            if not isinstance(item, dict):
                continue
            rel_path = item.get("file_path")
            if not rel_path:
                continue
            grouped.setdefault(str(rel_path), []).append(item)

        for rel_path, items in grouped.items():
            abs_path = project_root / rel_path
            if not abs_path.exists():
                continue

            lines = _safe_lines(abs_path.read_text(encoding="utf-8", errors="replace"))
            hit_lines = [line_no for item in items for line_no in item.get("hit_lines", []) if str(line_no).isdigit()]
            for cluster in _cluster_lines(hit_lines):
                start_line = max(1, cluster[0] - 4)
                end_line = min(len(lines), cluster[-1] + 4)
                first_item = items[0]
                candidates.append(
                    ChangeCandidate(
                        file_path=_normalize_relative_path(rel_path),
                        start_line=start_line,
                        end_line=end_line,
                        match_type=str(first_item.get("capture_name") or "scope"),
                        dependency=first_item.get("dependency"),
                        reason="Refactor code around detected migration scope",
                        snippet=_build_snippet(lines, start_line, end_line, set(cluster)),
                    )
                )

    merged = _merge_candidates(candidates)
    return [asdict(candidate) for candidate in merged]


def build_translation_report(
    project_root: str | Path,
    *,
    migration_tasks: list[dict[str, Any]] | None = None,
    dependency_focus: dict[str, Any] | list[dict[str, Any]] | None = None,
    affected_scopes: list[dict[str, Any]] | None = None,
    focus_report_path: str | Path | None = None,
    affected_scopes_path: str | Path | None = None,
) -> dict[str, Any]:
    candidates = find_change_candidates(
        project_root,
        focus_report_path=focus_report_path,
        affected_scopes_path=affected_scopes_path,
        dependency_focus=dependency_focus,
        affected_scopes=affected_scopes,
    )

    tasks = migration_tasks or []
    task_summaries = [str(task.get("title") or task.get("summary") or task) for task in tasks]

    return {
        "status": "ok",
        "project_path": str(Path(project_root).expanduser().resolve()),
        "task_count": len(tasks),
        "migration_tasks": tasks,
        "task_summaries": task_summaries,
        "change_candidates": candidates,
        "summary": {
            "candidate_count": len(candidates),
            "files_covered": len({candidate["file_path"] for candidate in candidates}),
        },
    }
