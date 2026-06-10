from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent, ToolDefinition
from src.tools.change_finder import build_translation_report, resolve_default_report_paths, coerce_tasks
from src.tools.jdeprscan_pipeline import run_jdeprscan_pipeline
from src.tools.report_enricher import enrich_report_with_llm
from src.tools.codebase_search_tools import find_code_usages, search_codebase, get_file_migration_details
from src.tools import write_file, MavenPomEditor, MavenProject, MavenRunner


class TranslatorAgent(BaseAgent):
    """
    Translator agent that turns migration scope reports into actionable change plans.

    Uses the ReAct pattern: the LLM autonomously decides which tools to call
    (jdeprscan, change_finder, enrich) and in what order, based on the instruction.

    Available tools:
        - run_jdeprscan: Discover deprecated API usage in project code and dependencies.
        - build_change_plan: Build a translation report from change candidates.
        - enrich_report: Enrich the report with LLM-generated recommendations.

    The jdeprscan report is the primary data source for deciding what code needs to change. It provides:
        - Layer 1 (project code): forRemoval and deprecated API calls
        - Layer 2 (dependencies): which JARs use deprecated APIs
        - Layer 3 (pom.xml): which dependencies have forRemoval=true
    """

    def get_prompt_file(self) -> str | None:
        """Load the detailed markdown prompt for the Translator Agent."""
        return "translator.md"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="run_jdeprscan",
                description=(
                    "Run the jdeprscan pipeline (B0-B3) to discover deprecated API usage "
                    "in both project code and dependencies. This is the primary data source "
                    "for migration decisions. Returns a structured report with 3 layers: "
                    "project code (forRemoval/deprecated), dependency JARs, and pom.xml critical deps."
                ),
                func=self._tool_run_jdeprscan,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the Java project root directory",
                        },
                        "target_java_version": {
                            "type": "string",
                            "description": "Target JDK version (e.g., '17')",
                        },
                        "jdk8_home": {
                            "type": "string",
                            "description": "Optional path to JDK 8 home directory",
                        },
                        "jdk17_home": {
                            "type": "string",
                            "description": "Optional path to JDK 17 home directory",
                        },
                    },
                    "required": ["project_path"],
                },
            ),
            ToolDefinition(
                name="build_change_plan",
                description=(
                    "Build a translation report from change candidates. This scans the project "
                    "for code patterns that need updating based on dependency focus scopes "
                    "and affected scopes. Returns a structured report with change candidates, "
                    "file locations, and migration task summaries."
                ),
                func=self._tool_build_change_plan,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the Java project root directory",
                        },
                        "migration_tasks": {
                            "type": "array",
                            "description": "List of migration tasks to include in the report",
                        },
                        "dependency_focus_scopes": {
                            "type": "object",
                            "description": "Dependency focus scopes for change detection",
                        },
                        "affected_scopes": {
                            "type": "array",
                            "description": "Affected scope data for change detection",
                        },
                        "dependency_focus_report_path": {
                            "type": "string",
                            "description": "Path to dependency_focus_scopes.json",
                        },
                        "affected_scopes_path": {
                            "type": "string",
                            "description": "Path to affected_scopes.json",
                        },
                    },
                    "required": ["project_path"],
                },
            ),
            ToolDefinition(
                name="enrich_report",
                description=(
                    "Enrich a migration report with LLM-generated recommendations. "
                    "Takes the existing report (with optional jdeprscan data) and adds "
                    "prioritized migration recommendations, focusing on forRemoval=true items "
                    "and critical dependencies. Returns the enriched report as JSON."
                ),
                func=self._tool_enrich_report,
                parameters={
                    "type": "object",
                    "properties": {
                        "report_json": {
                            "type": "object",
                            "description": "The current report as a JSON object to enrich",
                        },
                        "instruction": {
                            "type": "string",
                            "description": "The original instruction for context",
                        },
                    },
                    "required": ["report_json"],
                },
            ),
            ToolDefinition(
                name="find_code_usages",
                description=(
                    "Find semantic Java code usages using tree-sitter. Searches for method calls, "
                    "class declarations, imports, or variable declarations matching a specific identifier."
                ),
                func=self._tool_find_code_usages,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the Java project root directory",
                        },
                        "node_type": {
                            "type": "string",
                            "enum": [
                                "method_invocation",
                                "class_declaration",
                                "import_declaration",
                                "variable_declarator",
                            ],
                            "description": "The AST node type to search for",
                        },
                        "identifier": {
                            "type": "string",
                            "description": "The class, method, or variable name to match",
                        },
                    },
                    "required": ["node_type", "identifier"],
                },
            ),
            ToolDefinition(
                name="search_codebase",
                description=(
                    "Grep/Regex search text content within specified file extensions in the codebase. "
                    "Use this to find configuration keys, properties, or hardcoded strings."
                ),
                func=self._tool_search_codebase,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project root directory",
                        },
                        "regex_pattern": {
                            "type": "string",
                            "description": "The regular expression pattern to search for",
                        },
                        "file_extensions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file extensions to search (e.g. ['xml', 'properties'])",
                        },
                    },
                    "required": ["regex_pattern", "file_extensions"],
                },
            ),
            ToolDefinition(
                name="get_file_migration_details",
                description=(
                    "Retrieve the detailed deprecation references and change candidates for a specific file path "
                    "from the generated reports. Use this to obtain exact code snippets and migration details "
                    "for the file you are currently working on."
                ),
                func=self._tool_get_file_migration_details,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project root directory",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "The relative file path to get migration details for (e.g. src/main/java/...)",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            ToolDefinition(
                name="write_file",
                description=(
                    "Writes or overwrites the content of a file. "
                    "All written files are automatically stored under the project's 'artifacts' directory "
                    "to preserve original code and aggregate migrated files."
                ),
                func=self._tool_write_file,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the project root directory",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to write (relative to project root)",
                        },
                        "content": {
                            "type": "string",
                            "description": "The complete source code/text to write to the file",
                        },
                    },
                    "required": ["file_path", "content"],
                },
            ),
            ToolDefinition(
                name="edit_pom_dependency",
                description=(
                    "Programmatically update or insert dependencies, properties, plugins, or configurations "
                    "in a pom.xml file. Preserves namespaces and XML formatting."
                ),
                func=self._tool_edit_pom_dependency,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the Java project root directory",
                        },
                        "module": {
                            "type": "string",
                            "description": "Optional module folder name if this is a multi-module project (e.g. 'sonar-stash')",
                        },
                        "action": {
                            "type": "string",
                            "enum": ["add_dependency", "update_dependency", "ensure_property", "update_element_text"],
                            "description": "The pom modification action to perform",
                        },
                        "group_id": {
                            "type": "string",
                            "description": "Group ID of the dependency or plugin (required for add_dependency, update_dependency)",
                        },
                        "artifact_id": {
                            "type": "string",
                            "description": "Artifact ID of the dependency or plugin (required for add_dependency, update_dependency)",
                        },
                        "version": {
                            "type": "string",
                            "description": "Version of the dependency, property value, or element text",
                        },
                        "scope": {
                            "type": "string",
                            "description": "Optional scope for dependency (e.g. 'test', 'provided')",
                        },
                        "property_name": {
                            "type": "string",
                            "description": "Name of the property (required for ensure_property)",
                        },
                        "xpath": {
                            "type": "string",
                            "description": "XPath expression (required for update_element_text, e.g. './m:version' or './/m:properties/m:java.version')",
                        },
                    },
                    "required": ["action"],
                },
            ),
            ToolDefinition(
                name="run_maven_command",
                description=(
                    "Execute Maven compilation, tests, or dependency resolution on the target project. "
                    "Use this to verify whether changes compile and pass smoke tests/unit tests."
                ),
                func=self._tool_run_maven_command,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Path to the Java project root directory",
                        },
                        "goal": {
                            "type": "string",
                            "enum": ["compile", "test", "install", "deps", "copy_deps"],
                            "description": "The Maven goal to execute (compile: compile project, test: run verify/test suite, install: build and install to local repo, deps: list classpath, copy_deps: copy dependencies)",
                        },
                        "clean": {
                            "type": "boolean",
                            "description": "Whether to run clean before the goal (default: False)",
                        },
                        "skip_tests": {
                            "type": "boolean",
                            "description": "Whether to skip test execution during verification (default: False)",
                        },
                        "target_java_version": {
                            "type": "string",
                            "description": "Optional target Java version to pass to Maven compiler (default: '17')",
                        },
                    },
                    "required": ["goal"],
                },
            ),
        ]

    # ── Tool implementations ──

    def _tool_run_jdeprscan(
        self,
        project_path: str = "",
        target_java_version: str = "17",
        jdk8_home: str | None = None,
        jdk17_home: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Run jdeprscan pipeline B0-B3."""
        target_java = str(target_java_version).replace("JDK ", "").replace("jdk ", "") or "17"

        try:
            print(f"-> [TRANSLATOR] Running jdeprscan pipeline for JDK {target_java}...")

            result = run_jdeprscan_pipeline(
                project_path=project_path,
                target_release=target_java,
                jdk8_home=jdk8_home or None,
                jdk17_home=jdk17_home or None,
                logger=lambda msg: print(f"   {msg}"),
            )

            status = result.get("status", "FAIL")
            print(f"-> [TRANSLATOR] jdeprscan pipeline: {status}")

            # Save full report to file
            target_dir = Path(project_path) / "target"
            target_dir.mkdir(parents=True, exist_ok=True)
            report_file = target_dir / "jdeprscan_report.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print(f"-> [TRANSLATOR] Saved full jdeprscan report to {report_file}")

            if self.llm is None:
                # Strip only the verbose lines from dependency jar scans to prevent excessive payload
                if "steps" in result and "b3_dep_scan" in result["steps"]:
                    b3_dep = result["steps"]["b3_dep_scan"]
                    if isinstance(b3_dep, dict):
                        for p_jar in b3_dep.get("problem_jars", []):
                            if isinstance(p_jar, dict):
                                p_jar.pop("lines", None)
                        for t_jar in b3_dep.get("timeout_jars", []):
                            if isinstance(t_jar, dict):
                                t_jar.pop("lines", None)
                return result

            # Return a lean summary to the LLM context
            lean_result = {
                "status": status,
                "report_file": str(report_file.relative_to(Path(project_path))),
                "summary": result.get("summary", {}),
                "project_path": result.get("project_path"),
                "target_release": result.get("target_release"),
            }
            return lean_result

        except Exception as e:
            print(f"-> [TRANSLATOR] jdeprscan pipeline exception: {e}")
            return {"status": "FAIL", "error": str(e)}

    def _tool_build_change_plan(
        self,
        project_path: str = "",
        migration_tasks: list | None = None,
        dependency_focus_scopes: dict | None = None,
        affected_scopes: list | None = None,
        dependency_focus_report_path: str | None = None,
        affected_scopes_path: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Build translation report from change candidates."""
        # Resolve default report paths if not provided
        if not dependency_focus_report_path or not affected_scopes_path:
            resolved_dep, resolved_aff = resolve_default_report_paths(project_path, kwargs)
            if not dependency_focus_report_path:
                dependency_focus_report_path = resolved_dep
            if not affected_scopes_path:
                affected_scopes_path = resolved_aff

        # Coerce migration tasks
        tasks = coerce_tasks(migration_tasks)

        report = build_translation_report(
            project_path,
            migration_tasks=tasks,
            dependency_focus=dependency_focus_scopes,
            affected_scopes=affected_scopes,
            focus_report_path=dependency_focus_report_path,
            affected_scopes_path=affected_scopes_path,
        )

        # Add metadata
        report["project_type"] = kwargs.get("project_type")
        report["target_java_version"] = kwargs.get("target_java_version", "17")
        report["current_instruction"] = kwargs.get("current_instruction", "")

        # Save full change plan report to file
        target_dir = Path(project_path) / "target"
        target_dir.mkdir(parents=True, exist_ok=True)
        report_file = target_dir / "mygrate_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"-> [TRANSLATOR] Saved full change plan to {report_file}")

        if self.llm is None:
            return report

        # Return a lean summary to the LLM context
        lean_report = {
            "status": report.get("status", "ok"),
            "report_file": str(report_file.relative_to(Path(project_path))),
            "task_count": report.get("task_count", 0),
            "change_candidates_summary": [
                {
                    "file_path": c.get("file_path"),
                    "reason": c.get("reason"),
                    "match_type": c.get("match_type"),
                    "dependency": c.get("dependency")
                }
                for c in report.get("change_candidates", [])
            ]
        }
        return lean_report

    # def _tool_get_lines_to_change(self, file_path: str, start_line: int, end_line: int, 

    def _tool_enrich_report(
        self,
        report_json: dict | str = "{}",
        instruction: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Enrich report with LLM-generated recommendations."""
        project_path = kwargs.get("project_path", "")
        return enrich_report_with_llm(self.llm, report_json, instruction, project_path=project_path)

    def _tool_get_file_migration_details(
        self,
        project_path: str = "",
        file_path: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Get detailed migration information for a specific file path."""
        try:
            from src.tools.codebase_search_tools import get_file_migration_details
            print(f"-> [TRANSLATOR] Fetching migration details for file '{file_path}'...")
            results = get_file_migration_details(project_path, file_path)
            return {"status": "ok", "details": results}
        except Exception as e:
            print(f"-> [TRANSLATOR] Get file migration details exception: {e}")
            return {"status": "error", "error": str(e)}

    def _tool_write_file(
        self,
        project_path: str = "",
        file_path: str = "",
        content: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Write content to a file, storing it under the artifacts directory."""
        try:
            print(f"-> [TRANSLATOR] Writing file to artifacts/ for '{file_path}'...")
            result = write_file.func(project_path=project_path, file_path=file_path, content=content)
            return {"status": "ok", "message": result}
        except Exception as e:
            print(f"-> [TRANSLATOR] Write file exception: {e}")
            return {"status": "error", "error": str(e)}

    def _tool_find_code_usages(
        self,
        project_path: str = "",
        node_type: str = "",
        identifier: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Search Java AST for usages of an identifier."""
        try:
            print(f"-> [TRANSLATOR] Finding code usages: {node_type} matching '{identifier}'...")
            results = find_code_usages(project_path, node_type, identifier)
            return {"status": "ok", "usages": results, "count": len(results)}
        except Exception as e:
            print(f"-> [TRANSLATOR] Find code usages exception: {e}")
            return {"status": "error", "error": str(e)}

    def _tool_search_codebase(
        self,
        project_path: str = "",
        regex_pattern: str = "",
        file_extensions: list | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Regex grep search in codebase."""
        try:
            extensions = file_extensions or []
            print(f"-> [TRANSLATOR] Searching codebase with regex '{regex_pattern}' in {extensions}...")
            results = search_codebase(project_path, regex_pattern, extensions)
            return {"status": "ok", "matches": results, "count": len(results)}
        except Exception as e:
            print(f"-> [TRANSLATOR] Search codebase exception: {e}")
            return {"status": "error", "error": str(e)}

    def _tool_edit_pom_dependency(
        self,
        project_path: str = "",
        module: str | None = None,
        action: str = "",
        group_id: str | None = None,
        artifact_id: str | None = None,
        version: str | None = None,
        scope: str | None = None,
        property_name: str | None = None,
        xpath: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Modify pom.xml using MavenPomEditor."""
        try:
            print(f"-> [TRANSLATOR] Editing POM: action={action}, module={module}...")
            p_path = Path(project_path)
            root_pom = p_path / "pom.xml"
            if not root_pom.exists():
                return {"status": "error", "error": f"No root pom.xml found at {root_pom}"}
                
            project = MavenProject(str(root_pom))
            
            try:
                editor = project.get_pom_editor(module)
            except Exception as e:
                return {"status": "error", "error": f"Failed to get POM editor for module '{module}': {e}"}
            
            if action == "add_dependency":
                if not group_id or not artifact_id or not version:
                    return {"status": "error", "error": "group_id, artifact_id, and version are required for add_dependency"}
                editor.add_dependency(group_id, artifact_id, version, scope=scope)
                return {"status": "ok", "message": f"Added dependency {group_id}:{artifact_id}:{version} (scope: {scope})"}
                
            elif action == "update_dependency":
                if not group_id or not artifact_id or not version:
                    return {"status": "error", "error": "group_id, artifact_id, and version are required for update_dependency"}
                
                if editor.dependency_exists(group_id, artifact_id):
                    def update_func(dep_elem):
                        version_elem = editor.ensure_element(dep_elem, "m:version")
                        version_elem.text = version
                        if scope:
                            scope_elem = editor.ensure_element(dep_elem, "m:scope")
                            scope_elem.text = scope
                    editor.update_dependency(group_id, artifact_id, update_func)
                    return {"status": "ok", "message": f"Updated dependency {group_id}:{artifact_id} to version {version} (scope: {scope})"}
                else:
                    editor.add_dependency(group_id, artifact_id, version, scope=scope)
                    return {"status": "ok", "message": f"Dependency {group_id}:{artifact_id} did not exist, added it with version {version} (scope: {scope})"}
                    
            elif action == "ensure_property":
                if not property_name or not version:
                    return {"status": "error", "error": "property_name and version are required for ensure_property"}
                editor.ensure_property(property_name, version)
                return {"status": "ok", "message": f"Property {property_name} set to {version}"}
                
            elif action == "update_element_text":
                if not xpath or not version:
                    return {"status": "error", "error": "xpath and version are required for update_element_text"}
                editor.update_element_text(xpath, version)
                return {"status": "ok", "message": f"Updated elements at xpath '{xpath}' to '{version}'"}
                
            else:
                return {"status": "error", "error": f"Unknown action: {action}"}
                
        except Exception as e:
            print(f"-> [TRANSLATOR] edit_pom_dependency exception: {e}")
            return {"status": "error", "error": f"Exception in edit_pom_dependency: {e}"}

    def _tool_run_maven_command(
        self,
        project_path: str = "",
        goal: str = "compile",
        clean: bool = False,
        skip_tests: bool = False,
        target_java_version: str = "17",
        **kwargs,
    ) -> dict[str, Any]:
        """Tool: Run Maven command on the project using MavenRunner."""
        try:
            print(f"-> [TRANSLATOR] Running Maven goal: goal={goal}, clean={clean}...")
            p_path = Path(project_path)
            if not p_path.exists():
                return {"status": "error", "error": f"Project path does not exist: {project_path}"}
                
            runner = MavenRunner(target_java_version)
            
            if goal == "compile":
                res = runner.compile(p_path, clean=clean)
            elif goal == "test":
                res = runner.test(p_path, skip_tests=skip_tests, clean=clean)
            elif goal == "install":
                res = runner.install(p_path, skip_tests=skip_tests)
            elif goal == "deps":
                output_path = p_path / "target" / "classpath.txt"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                res = runner.deps(p_path, output_path)
            elif goal == "copy_deps":
                res = runner.copy_deps(p_path)
            else:
                return {"status": "error", "error": f"Unknown goal: {goal}"}
                
            return {
                "status": "ok" if res.status == 0 else "fail",
                "exit_code": res.status,
                "stdout": res.stdout,
                "stderr": res.stderr
            }
        except Exception as e:
            print(f"-> [TRANSLATOR] run_maven_command exception: {e}")
            return {"status": "error", "error": f"Exception in run_maven_command: {e}"}

    def _post_process(self, results: dict[str, Any], instruction: str, payload: dict[str, Any]) -> str:
        """Post-process deterministic tool results to merge them into a single plan."""
        merged = dict(results)

        # Elevate jdeprscan results
        jdeprscan = results.get("run_jdeprscan")
        if isinstance(jdeprscan, dict):
            merged["jdeprscan"] = jdeprscan

        # Elevate change plan results (project_path, task_count, change_candidates, etc.)
        change_plan = results.get("build_change_plan")
        if isinstance(change_plan, dict):
            for key, val in change_plan.items():
                merged.setdefault(key, val)

        # If enrich_report succeeded and returned a dict, merge its keys
        enrich = results.get("enrich_report")
        if isinstance(enrich, dict) and enrich.get("status") != "skipped":
            for key, val in enrich.items():
                merged[key] = val

        return json.dumps(merged, ensure_ascii=False, indent=2, default=str)

