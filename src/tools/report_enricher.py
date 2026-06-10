from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def enrich_report_with_llm(
    llm: Any,
    report: dict[str, Any] | str = "{}",
    instruction: str = "",
    project_path: str = "",
) -> dict[str, Any]:
    """Enrich a migration report programmatically without loading the entire JSON into the LLM context.
    Writes a formatted markdown summary to target/migration_report.md and returns the enriched report summary.
    """
    try:
        parsed_report = json.loads(report) if isinstance(report, str) else report
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid report JSON"}

    if not isinstance(parsed_report, dict):
        return {"status": "error", "message": "Report must be a JSON object"}

    # Extract summary info
    jdeprscan = parsed_report.get("jdeprscan", {})
    summary = jdeprscan.get("summary", {})
    proj = summary.get("project_code", {})
    deps = summary.get("dependencies", {})
    pom = summary.get("pom_xml", {})

    task_count = parsed_report.get("task_count", 0)
    candidates = parsed_report.get("change_candidates_summary", [])
    if not candidates and "change_candidates" in parsed_report:
        candidates = [
            {"file_path": c.get("file_path"), "reason": c.get("reason"), "dependency": c.get("dependency")}
            for c in parsed_report["change_candidates"]
        ]

    # Build programmatic markdown report
    lines = [
        "# Mygrate Migration Report Summary",
        "",
        "The codebase migration analysis is complete. Below is the summary of issues detected and the recommended change plan.",
        "",
        "## 1. JDK Compatibility Analysis (jdeprscan)",
        f"- **Target release**: JDK {jdeprscan.get('target_release', '17')}",
        f"- **Pipeline status**: {jdeprscan.get('status', 'OK')}",
        "",
        "### Project Code Issues:",
        f"- Critical `forRemoval=true` API usages (will crash at runtime): **{proj.get('for_removal_count', 0)}**",
        f"- Deprecated API usages (warnings only): **{proj.get('deprecated_count', 0)}**",
        "",
        "### Dependency Issues:",
        f"- Problem dependency JARs: **{deps.get('problem_count', 0)}**",
        f"- Critical dependency JARs (contain forRemoval usages): **{deps.get('critical_count', 0)}**",
    ]

    top_issues = deps.get("top_issues", [])
    if top_issues:
        lines.extend([
            "",
            "#### Top problem dependencies:",
        ])
        for issue in top_issues:
            lines.append(f"- `{issue['jar']}`: {issue['for_removal']} forRemoval, {issue['total']} deprecated")

    critical_deps = pom.get("critical_deps", [])
    if critical_deps:
        lines.extend([
            "",
            "#### Critical pom.xml dependencies:",
        ])
        for dep in critical_deps:
            lines.append(f"- `{dep['jar']}`: {dep['for_removal']} forRemoval, {dep['total']} deprecated")

    lines.extend([
        "",
        "## 2. Codebase Change Plan",
        f"- **Total migration tasks**: {task_count}",
        f"- **Files requiring modification**: {len(candidates)}",
    ])

    if candidates:
        lines.extend([
            "",
            "### Target Files to Migrate:",
        ])
        for c in candidates:
            lines.append(f"- `{c['file_path']}`: {c['reason']} (dependency: {c.get('dependency', 'n/a')})")

    lines.extend([
        "",
        "## 3. Recommended Migration Workflow",
        "1. Inspect detailed deprecation references and change candidates for each file on-demand using the `get_file_migration_details(file_path)` tool.",
        "2. Apply programmatic or manual edits and save the files using the `write_file(file_path, content)` tool.",
        "3. Once all files have been migrated, execute the `submit_final_answer` tool with 'ok' status to finalize.",
    ])

    markdown_content = "\n".join(lines)

    # Save to file target/migration_report.md
    proj_dir = Path(project_path) if project_path else Path(".")
    target_dir = proj_dir / "target"
    target_dir.mkdir(parents=True, exist_ok=True)
    report_md_file = target_dir / "migration_report.md"
    try:
        report_md_file.write_text(markdown_content, encoding="utf-8")
        print(f"-> [ENRICHER] Programmatic markdown summary saved to {report_md_file}")
    except Exception as e:
        print(f"-> [ENRICHER] Error writing markdown report: {e}")

    # Return summary dict
    rel_md_path = str(report_md_file.relative_to(proj_dir)) if project_path else "target/migration_report.md"
    
    enriched = dict(parsed_report)
    enriched.update({
        "status": "ok",
        "markdown_report": (
            f"### Migration Scan & Plan Ready\n"
            f"The codebase scan and change plan reports have been successfully generated and saved:\n"
            f"- Detailed JSON reports are located at `target/jdeprscan_report.json` and `target/mygrate_report.json`.\n"
            f"- A human-readable Markdown summary report has been compiled and saved to `{rel_md_path}`.\n\n"
            f"Please read the markdown summary or fetch details for specific files to begin translation."
        ),
        "migration_notes": (
            "Prioritized next steps:\n"
            f"1. Open and review the markdown summary report at `{rel_md_path}`.\n"
            "2. For each file listed, call `get_file_migration_details(file_path)` to get code snippets.\n"
            "3. Edit and save the files to `artifacts/` using `write_file(file_path, content)`."
        )
    })
    
    return enriched
