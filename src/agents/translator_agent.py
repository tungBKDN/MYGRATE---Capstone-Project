from __future__ import annotations

import json
import os
import re
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent, ToolDefinition
from src.tools.maven import MavenRunner, MavenProject, MavenPomEditor
from src.tools.change_finder import build_translation_report, resolve_default_report_paths, coerce_tasks
from src.tools.jdeprscan_pipeline import run_jdeprscan_pipeline
from src.tools.report_enricher import enrich_report_with_llm
from src.tools.codebase_search_tools import find_code_usages, search_codebase, get_file_migration_details
from src.tools import write_file


class TranslatorAgent(BaseAgent):
    """
    Unified TranslatorAgent combining POM migration (Phase 1), batch source-code editing (Phase 2),
    and evaluation report generation (Phase 3).
    """

    READ_FILE_KEEP_MESSAGES = 10

    def __init__(self, model_name: str | None = None):
        super().__init__(model_name)
        self.project_path = ""
        self.current_file = ""
        try:
            self.MAX_ITERATIONS = int(os.getenv("TEST_MAX_ITER", 50))
        except (ValueError, TypeError):
            self.MAX_ITERATIONS = 50
        self.step_count = 0  # Track number of agent calls
        self._log_entries: list[str] = []
        self._last_edit_count = 0  # track edits since last compile
        self._classpath_cache: dict[str, set[str]] = {}  # jar_path -> set of class names
        self._maven_plugin_cache: dict[str, bool] = {}  # "groupId:artifactId:version" -> exists
        self._main_source_locked = False  # Code Lock: once main compiles, block edits to src/main
        self.MAX_TEST_FAIL_LOOPS = 15
        self._test_fail_loop_count = 0
        self._last_test_failure_count = None
        self._last_failure_signature = None

    def get_prompt_file(self) -> str | None:
        """Load the combined prompt for Translator Agent (Phase 1 + Phase 2)."""
        return "translator.md"

    def run(self, instruction: str) -> str:
        payload = self._parse_instruction(instruction)
        self.project_path = payload.get("project_path", "")
        self._log_entries = []
        self._last_edit_count = 0
        self._classpath_cache = {}
        self._maven_plugin_cache = {}
        self._main_source_locked = False  # Reset code lock on each new run
        self._test_fail_loop_count = 0
        self._last_test_failure_count = None
        self._last_failure_signature = None

        # Run ReAct loop
        result = super().run(instruction)

        # Post-execution Phase: Generate evaluation report
        try:
            self.generate_evaluation_report()
        except Exception as e:
            print(f"Warning: Failed to generate evaluation report: {e}")

        return result

    def _invoke_with_retry(
        self,
        llm_with_tools: Any,
        messages: list,
        tool_map: dict[str, ToolDefinition],
        payload: dict[str, Any],
        react_tool_results: dict[str, Any],
    ) -> Any | None:
        # Increment step count for every LLM call
        self.step_count += 1

        # Keep messages history clean from large read_file contents
        from langchain_core.messages import ToolMessage
        keep = self.READ_FILE_KEEP_MESSAGES
        for i, msg in enumerate(messages):
            if not isinstance(msg, ToolMessage):
                continue
            messages_after = len(messages) - i - 1
            if messages_after <= keep:
                continue
            if i == 0:
                continue
            prev_msg = messages[i - 1]
            tool_calls = getattr(prev_msg, "tool_calls", [])
            is_read_file = False
            for tc in tool_calls:
                if tc.get("id") == msg.tool_call_id and tc.get("name") == "read_file":
                    is_read_file = True
                    break
            if is_read_file:
                messages[i] = ToolMessage(
                    content="[File content was shown earlier. Re-call read_file if you need to see it again.]",
                    tool_call_id=msg.tool_call_id,
                )
        return super()._invoke_with_retry(llm_with_tools, messages, tool_map, payload, react_tool_results)

    def _log(self, entry: str):
        self._log_entries.append(entry)

    def get_log(self) -> str:
        return "\n".join(self._log_entries)

    # ── Helper methods for verify classpath ──

    def _parse_pom_dependencies(self) -> list[dict[str, str]]:
        """Parse pom.xml to extract dependency coordinates."""
        pom_path = Path(self.project_path) / "pom.xml"
        if not pom_path.exists():
            return []

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(pom_path)
            root = tree.getroot()
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}

            deps = root.findall(".//m:dependency", ns)
            if not deps:
                deps = root.findall(".//dependency")

            result = []
            for dep in deps:
                gid = self._xml_text(dep, "groupId", ns) or self._xml_text(dep, "groupId")
                aid = self._xml_text(dep, "artifactId", ns) or self._xml_text(dep, "artifactId")
                ver = self._xml_text(dep, "version", ns) or self._xml_text(dep, "version")
                scope = self._xml_text(dep, "scope", ns) or self._xml_text(dep, "scope") or "compile"
                if gid and aid and ver:
                    result.append({"groupId": gid, "artifactId": aid, "version": ver, "scope": scope})
            return result
        except Exception as e:
            self._log(f"[check_class] Failed to parse pom.xml: {e}")
            return []

    @staticmethod
    def _xml_text(element, tag: str, ns: dict | None = None) -> str | None:
        if ns:
            child = element.find(f"m:{tag}", ns)
        else:
            child = element.find(tag)
        return child.text.strip() if child is not None and child.text else None

    def _find_jar_in_m2(self, group_id: str, artifact_id: str, version: str) -> Path | None:
        m2 = Path.home() / ".m2" / "repository"
        group_path = group_id.replace(".", "/")
        jar_path = m2 / group_path / artifact_id / version / f"{artifact_id}-{version}.jar"
        if jar_path.exists():
            return jar_path
        sources_path = m2 / group_path / artifact_id / version / f"{artifact_id}-{version}-sources.jar"
        if sources_path.exists():
            return sources_path
        return None

    def _list_classes_in_jar(self, jar_path: Path) -> set[str]:
        key = str(jar_path)
        if key in self._classpath_cache:
            return self._classpath_cache[key]

        classes = set()
        try:
            with zipfile.ZipFile(jar_path) as zf:
                for name in zf.namelist():
                    if name.endswith(".class") and "$" not in name:
                        fqn = name[:-6].replace("/", ".")
                        classes.add(fqn)
        except Exception as e:
            self._log(f"[check_class] Error reading JAR {jar_path}: {e}")

        self._classpath_cache[key] = classes
        return classes

    def _resolve_dependency_version(self, group_id: str, artifact_id: str, version: str) -> str:
        if not version.startswith("${"):
            return version
        prop_name = version[2:-1]
        pom_path = Path(self.project_path) / "pom.xml"
        if not pom_path.exists():
            return version
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(pom_path)
            root = tree.getroot()
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}
            props = root.find("m:properties", ns) or root.find("properties")
            if props is not None:
                for child in props:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if tag == prop_name and child.text:
                        return child.text.strip()
        except Exception:
            pass
        return version

    def _check_maven_plugin_exists(self, group_id: str, artifact_id: str, version: str) -> dict[str, Any]:
        cache_key = f"{group_id}:{artifact_id}:{version}"
        if cache_key in self._maven_plugin_cache:
            exists = self._maven_plugin_cache[cache_key]
            return {
                "group_id": group_id,
                "artifact_id": artifact_id,
                "version": version,
                "exists": exists,
                "message": f"Plugin {cache_key} {'EXISTS' if exists else 'DOES NOT EXIST'} (cached)."
            }

        local_jar = self._find_jar_in_m2(group_id, artifact_id, version)
        if local_jar is not None:
            self._maven_plugin_cache[cache_key] = True
            return {
                "group_id": group_id,
                "artifact_id": artifact_id,
                "version": version,
                "exists": True,
                "message": f"Plugin {cache_key} EXISTS in local Maven repository. Safe to use."
            }

        try:
            url = f"https://search.maven.org/solrsearch/select?q=g:{group_id}+AND+a:{artifact_id}+AND+v:{version}&rows=5&wt=json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mygrate-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                num_found = data.get("response", {}).get("numFound", 0)
                exists = num_found > 0
        except Exception:
            try:
                group_path = group_id.replace(".", "/")
                pom_url = f"https://repo1.maven.org/maven2/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
                req = urllib.request.Request(pom_url, headers={"User-Agent": "Mygrate-Agent/1.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    exists = response.status == 200
            except Exception:
                exists = False

        self._maven_plugin_cache[cache_key] = exists
        return {
            "group_id": group_id,
            "artifact_id": artifact_id,
            "version": version,
            "exists": exists,
            "message": f"Plugin {cache_key} {'EXISTS' if exists else 'DOES NOT EXIST'}."
        }

    # ── Evaluation Report Generation ──

    def generate_evaluation_report(self):
        """Run Maven coverage and export metrics to eval.json in the current working directory."""
        if not self.project_path:
            return

        p_path = Path(self.project_path)
        codebase_name = p_path.name

        print(f"-> [EVAL] Starting final evaluation for codebase: {codebase_name}...")
        runner = MavenRunner(target_java_version="17")
        cov_res = runner.coverage(p_path, clean=True)

        compilation_success = (cov_res.status == 0)

        # Parse test results
        total_tests = 0
        passed_tests = 0
        stdout_to_parse = cov_res.stdout or ""

        # regex search for Tests run:, Failures:, Errors:
        for line in stdout_to_parse.splitlines():
            if "Tests run:" in line and " - in " not in line:
                match = re.search(r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)", line)
                if match:
                    total = int(match.group(1))
                    failures = int(match.group(2))
                    errors = int(match.group(3))
                    total_tests += total
                    passed_tests += (total - failures - errors)

        line_coverage = cov_res.line_coverage_pct if cov_res.coverage_found else 0.0
        covered_lines = cov_res.covered_lines if cov_res.coverage_found else 0
        missed_lines = cov_res.missed_lines if cov_res.coverage_found else 0

        eval_data = {
            "compilation_success": compilation_success,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "line_coverage": line_coverage,
            "covered_lines": covered_lines,
            "missed_lines": missed_lines,
            "step_count": self.step_count
        }

        eval_file = Path.cwd() / "eval.json"
        existing_data = {}
        if eval_file.exists():
            try:
                with open(eval_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                pass

        # Update report with key as codebase name
        existing_data[codebase_name] = eval_data

        with open(eval_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)

        print(f"-> [EVAL] Saved evaluation report for {codebase_name} to {eval_file}")

    # ── Tool Definitions ──

    def get_tools(self) -> list[ToolDefinition]:
        return [
            # Discovery / Scanning tools
            ToolDefinition(
                name="run_jdeprscan",
                description=(
                    "Run the jdeprscan pipeline (B0-B3) to discover deprecated API usage "
                    "in both project code and dependencies."
                ),
                func=self._tool_run_jdeprscan,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Path to the Java project root"},
                        "target_java_version": {"type": "string", "description": "Target Java version (e.g. '17')"},
                    },
                    "required": ["project_path"],
                },
            ),
            ToolDefinition(
                name="build_change_plan",
                description="Build a translation report from change candidates.",
                func=self._tool_build_change_plan,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "migration_tasks": {"type": "array"},
                    },
                    "required": ["project_path"],
                },
            ),
            ToolDefinition(
                name="enrich_report",
                description="Enrich migration report with LLM-generated recommendations.",
                func=self._tool_enrich_report,
                parameters={
                    "type": "object",
                    "properties": {
                        "report_json": {"type": "object"},
                        "instruction": {"type": "string"},
                    },
                    "required": ["report_json"],
                },
            ),

            # AST & Codebase Search tools
            ToolDefinition(
                name="find_code_usages",
                description="Find semantic Java code usages using tree-sitter.",
                func=self._tool_find_code_usages,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "node_type": {"type": "string", "enum": ["method_invocation", "class_declaration", "import_declaration", "variable_declarator"]},
                        "identifier": {"type": "string"},
                    },
                    "required": ["node_type", "identifier"],
                },
            ),
            ToolDefinition(
                name="search_codebase",
                description="Grep/Regex search text content within codebase.",
                func=self._tool_search_codebase,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "regex_pattern": {"type": "string"},
                        "file_extensions": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["regex_pattern", "file_extensions"],
                },
            ),
            ToolDefinition(
                name="get_file_migration_details",
                description="Retrieve detailed deprecation references for a specific file.",
                func=self._tool_get_file_migration_details,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "file_path": {"type": "string"},
                    },
                    "required": ["file_path"],
                },
            ),

            # Source Editing / Operations tools
            ToolDefinition(
                name="read_file",
                description="Read the full content of a file (with line numbers) relative to project root.",
                func=self._tool_read_file,
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"}
                    },
                    "required": ["file_path"]
                }
            ),
            ToolDefinition(
                name="check_class",
                description="Check if class(es) exist in current classpath.",
                func=self._tool_check_class,
                parameters={
                    "type": "object",
                    "properties": {
                        "class_names": {"type": "array", "items": {"type": "string"}},
                        "class_name": {"type": "string"}
                    }
                }
            ),
            ToolDefinition(
                name="check_maven_plugin",
                description="Check if a Maven plugin version exists on Maven Central.",
                func=self._tool_check_maven_plugin,
                parameters={
                    "type": "object",
                    "properties": {
                        "group_id": {"type": "string"},
                        "artifact_id": {"type": "string"},
                        "version": {"type": "string"}
                    },
                    "required": ["group_id", "artifact_id", "version"]
                }
            ),
            ToolDefinition(
                name="apply_edits",
                description="Apply multiple line-based edits to a file. Does NOT compile.",
                func=self._tool_apply_edits,
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "edits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "start_line": {"type": "integer"},
                                    "end_line": {"type": "integer"},
                                    "replacement": {"type": "string"}
                                },
                                "required": ["start_line", "end_line", "replacement"]
                            }
                        }
                    },
                    "required": ["file_path", "edits"]
                }
            ),
            ToolDefinition(
                name="compile_project",
                description="Compile the project using Maven under JDK 17. Verify compile and test suites.",
                func=self._tool_compile_project,
                parameters={
                    "type": "object",
                    "properties": {
                        "run_tests": {"type": "boolean"}
                    }
                }
            ),
            ToolDefinition(
                name="write_file",
                description="Writes or overwrites the content of a file.",
                func=self._tool_write_file,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "file_path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["file_path", "content"],
                },
            ),
            ToolDefinition(
                name="list_project_files",
                description="Recursively list all directories and files under the project path.",
                func=self._tool_list_project_files,
                parameters={
                    "type": "object",
                    "properties": {
                        "relative_path": {"type": "string"}
                    }
                }
            ),
            ToolDefinition(
                name="fetch_migration_rule",
                description="Retrieve migration recipes and rules from migration_rules.json.",
                func=self._tool_fetch_migration_rule,
                parameters={
                    "type": "object",
                    "properties": {
                        "keywords": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["keywords"]
                }
            ),
            ToolDefinition(
                name="edit_pom_dependency",
                description="Modify properties, elements, dependencies, or plugins in a pom.xml.",
                func=self._tool_edit_pom_dependency,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "module": {"type": "string"},
                        "action": {"type": "string", "enum": ["add_dependency", "update_dependency", "ensure_property", "update_element_text"]},
                        "group_id": {"type": "string"},
                        "artifact_id": {"type": "string"},
                        "version": {"type": "string"},
                        "scope": {"type": "string"},
                        "property_name": {"type": "string"},
                        "xpath": {"type": "string"},
                    },
                    "required": ["action"],
                },
            ),
            ToolDefinition(
                name="run_maven_command",
                description="Execute Maven compilation, tests, or goals.",
                func=self._tool_run_maven_command,
                parameters={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "goal": {"type": "string", "enum": ["compile", "test", "install", "deps", "copy_deps"]},
                        "clean": {"type": "boolean"},
                        "skip_tests": {"type": "boolean"},
                        "target_java_version": {"type": "string"},
                    },
                    "required": ["goal"],
                },
            ),
        ]

    # ── Tool Implementations ──

    def _tool_run_jdeprscan(
        self,
        project_path: str = "",
        target_java_version: str = "17",
        **kwargs,
    ) -> dict[str, Any]:
        target_java = str(target_java_version).replace("JDK ", "").replace("jdk ", "") or "17"
        try:
            print(f"-> [TRANSLATOR] Running jdeprscan pipeline for JDK {target_java}...")
            result = run_jdeprscan_pipeline(
                project_path=project_path,
                target_release=target_java,
                logger=lambda msg: print(f"   {msg}"),
            )
            return {"status": result.get("status", "FAIL"), "summary": result.get("summary", {})}
        except Exception as e:
            return {"status": "FAIL", "error": str(e)}

    def _tool_build_change_plan(
        self,
        project_path: str = "",
        migration_tasks: list | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        resolved_dep, resolved_aff = resolve_default_report_paths(project_path, kwargs)
        tasks = coerce_tasks(migration_tasks)
        report = build_translation_report(
            project_path,
            migration_tasks=tasks,
            focus_report_path=resolved_dep,
            affected_scopes_path=resolved_aff,
        )
        return {"status": "ok", "task_count": report.get("task_count", 0)}

    def _tool_enrich_report(
        self,
        report_json: dict | str = "{}",
        instruction: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        project_path = kwargs.get("project_path", "")
        return enrich_report_with_llm(self.llm, report_json, instruction, project_path=project_path)

    def _tool_find_code_usages(
        self,
        project_path: str = "",
        node_type: str = "",
        identifier: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        try:
            results = find_code_usages(project_path, node_type, identifier)
            return {"status": "ok", "usages": results, "count": len(results)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _tool_search_codebase(
        self,
        project_path: str = "",
        regex_pattern: str = "",
        file_extensions: list | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        try:
            results = search_codebase(project_path, regex_pattern, file_extensions or [])
            return {"status": "ok", "matches": results, "count": len(results)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _tool_get_file_migration_details(
        self,
        project_path: str = "",
        file_path: str = "",
        **kwargs,
    ) -> dict[str, Any]:
        try:
            results = get_file_migration_details(project_path, file_path)
            return {"status": "ok", "details": results}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _tool_read_file(self, file_path: str, **kwargs) -> str:
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return f"Error: File {file_path} does not exist."
            self.current_file = str(path)
            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            return "\n".join(numbered)
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

    def _tool_check_class(self, class_names: list[str] = None, class_name: str = None, **kwargs) -> dict[str, Any]:
        try:
            deps = self._parse_pom_dependencies()
            target_classes = list(class_names) if class_names else ([class_name] if class_name else [])
            if not target_classes:
                return {"error": "Must provide 'class_names' (array) or 'class_name' (string)."}

            search_deps = []
            for dep in deps:
                if dep.get("scope") == "test":
                    continue
                version = self._resolve_dependency_version(dep["groupId"], dep["artifactId"], dep["version"])
                jar_path = self._find_jar_in_m2(dep["groupId"], dep["artifactId"], version)
                if jar_path is not None:
                    search_deps.append((dep, jar_path))

            jar_classes = {}
            for dep, jar_path in search_deps:
                try:
                    jar_classes[f"{dep['groupId']}:{dep['artifactId']}:{dep['version']}"] = self._list_classes_in_jar(jar_path)
                except Exception:
                    pass

            results = {}
            for c_name in target_classes:
                found_in = []
                for dep_id, classes in jar_classes.items():
                    if c_name in classes:
                        found_in.append({"found": True, "jar": dep_id, "class_name": c_name})
                if found_in:
                    results[c_name] = {"exists": True, "found_in": found_in, "message": f"Class '{c_name}' EXISTS."}
                else:
                    results[c_name] = {"exists": False, "found_in": [], "message": f"Class '{c_name}' does NOT exist."}
            return results
        except Exception as e:
            return {"error": f"Failed to check classes: {e}"}

    def _tool_check_maven_plugin(self, group_id: str, artifact_id: str, version: str, **kwargs) -> dict[str, Any]:
        try:
            return self._check_maven_plugin_exists(group_id, artifact_id, version)
        except Exception as e:
            return {"error": f"Failed to check Maven plugin: {e}"}

    def _tool_apply_edits(self, file_path: str, edits: list, **kwargs) -> str:
        try:
            lock_err = self._check_main_source_lock(file_path)
            if lock_err:
                return lock_err

            path = self._resolve_path(file_path)
            if not path.exists():
                return f"Error: File {file_path} does not exist."
            self.current_file = str(path)

            if not edits:
                return "Error: No edits provided."

            # POM.XML plugin validation check
            if path.name == "pom.xml":
                content_before = path.read_text(encoding="utf-8")
                lines_before = content_before.splitlines()
                unverified_plugins = []
                for edit in edits:
                    start = int(edit.get("start_line", 0))
                    end = int(edit.get("end_line", start))
                    replacement = edit.get("replacement", "")
                    if "<version>" in replacement:
                        version_matches = re.findall(r"<version>([^<]+)</version>", replacement)
                        for ver in version_matches:
                            if ver.startswith("${"):
                                continue
                            old_lines = "\n".join(lines_before[max(0, start-1):end])
                            if f"<version>{ver}</version>" in old_lines:
                                continue
                            context = "\n".join(lines_before[max(0, start-10):min(len(lines_before), end+10)]) + "\n" + replacement
                            gid_match = re.search(r"<groupId>([^<]+)</groupId>", context)
                            aid_match = re.search(r"<artifactId>([^<]+)</artifactId>", context)
                            if gid_match and aid_match:
                                gid = gid_match.group(1).strip()
                                aid = aid_match.group(1).strip()
                                line_char_idx = sum(len(l) + 1 for l in lines_before[:start - 1])
                                is_plugin = content_before.rfind("<plugin>", 0, line_char_idx) > content_before.rfind("<dependency>", 0, line_char_idx)
                                if is_plugin:
                                    cache_key = f"{gid}:{aid}:{ver}"
                                    if cache_key not in self._maven_plugin_cache:
                                        unverified_plugins.append({"group_id": gid, "artifact_id": aid, "version": ver, "line_range": f"{start}-{end}"})

                if unverified_plugins:
                    plugin_list = "\n".join([f"  - {p['group_id']}:{p['artifact_id']}:{p['version']} (lines {p['line_range']})" for p in unverified_plugins])
                    return f"⚠️ BLOCKED: Unverified Maven plugin versions:\n{plugin_list}\nCall check_maven_plugin first."

            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()

            validated = []
            for edit in edits:
                start = int(edit.get("start_line", 0))
                end = int(edit.get("end_line", start))
                replacement = edit.get("replacement", "")
                if "\\n" in replacement and "\n" not in replacement:
                    replacement = replacement.replace("\\n", "\n")
                if start < 1 or end < 1 or start > end:
                    return f"Error: Invalid line range {start}-{end}."
                if end > len(lines):
                    return f"Error: end_line={end} exceeds file length ({len(lines)})."
                validated.append((start, end, replacement))

            # Overlap check
            validated_sorted = sorted(validated, key=lambda x: x[0])
            for i in range(len(validated_sorted) - 1):
                if validated_sorted[i][1] >= validated_sorted[i+1][0]:
                    return "Error: Overlapping edits detected."

            validated.sort(key=lambda x: x[0], reverse=True)
            for start, end, replacement in validated:
                lines[start - 1:end] = replacement.splitlines() if replacement else []

            new_content = "\n".join(lines)
            hacking_err = self._validate_reward_hacking(file_path, content, new_content)
            if hacking_err:
                return hacking_err

            path.write_text(new_content, encoding="utf-8")
            self._last_edit_count += len(validated)
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            return f"Applied {len(validated)} edit(s) to {file_path}.\nNew content:\n" + "\n".join(numbered)
        except Exception as e:
            return f"Error applying edits: {e}"

    def _tool_compile_project(self, run_tests: bool = False, **kwargs) -> dict[str, Any]:
        try:
            project_path = Path(self.project_path)
            runner = MavenRunner(target_java_version="17")
            
            # Check git status for modified tests
            import subprocess
            git_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=str(project_path))
            if "src/test/" in git_status.stdout.replace("\\", "/"):
                run_tests = True

            if run_tests:
                compile_res = runner.test(project_path, skip_tests=False, clean=True)
            else:
                compile_res = runner.compile(project_path, clean=True)

            output = compile_res.stdout + "\n" + compile_res.stderr
            status = compile_res.status
            self._last_edit_count = 0

            if status == 0:
                self._test_fail_loop_count = 0
                self._last_test_failure_count = None
                self._last_failure_signature = None
                if not run_tests and not self._main_source_locked:
                    self._main_source_locked = True
                return {"exit_code": 0, "success": True, "errors": "Project compiles successfully!"}

            # Extract errors
            compiler_errors = []
            test_failures = []
            in_error = False
            in_fail = False
            for line in output.splitlines():
                if "COMPILATION ERROR :" in line:
                    in_error = True
                    continue
                if in_error:
                    if line.startswith("[INFO]") and "error" in line.lower():
                        in_error = False
                    elif line.startswith("[ERROR]"):
                        compiler_errors.append(line)
                if "Results:" in line or "Failures:" in line or "Tests run:" in line:
                    in_fail = True
                if in_fail:
                    if line.startswith("[INFO]") and "Build" in line:
                        in_fail = False
                    elif line.startswith("[ERROR]") and "Run " not in line:
                        test_failures.append(line)

            if self._main_source_locked and any("src/main/java" in err.replace("\\", "/") for err in compiler_errors):
                self._main_source_locked = False  # Dynamic Unlock

            # ── Deadlock / stall detection ─────────────────────────────────────
            # Two tiers:
            #  Tier 1 (Signature): if the *exact same* error fingerprint appears
            #    STUCK_SIG_LIMIT rounds in a row, there is no way the agent can fix
            #    it — force early exit.
            #  Tier 2 (Count):  if the *number* of failures doesn't decrease for
            #    MAX_TEST_FAIL_LOOPS consecutive compile calls, also force exit.
            # Both tiers are only active when we actually ran the test suite.
            STUCK_SIG_LIMIT = 5  # identical signature rounds before giving up
            if run_tests:
                failures_cnt = len(test_failures) + len(compiler_errors)

                # --- Tier 1: error-signature check ---
                # Build a compact fingerprint from the first 5 error lines so small
                # surrounding context changes don't reset the clock.
                all_errors = compiler_errors + test_failures
                sig_lines = sorted(set(l.strip()[:120] for l in all_errors[:20]))
                current_sig = "|".join(sig_lines)

                if self._last_failure_signature is not None and current_sig == self._last_failure_signature and current_sig != "":
                    self._test_fail_loop_count += 1
                elif self._last_test_failure_count is not None and failures_cnt >= self._last_test_failure_count:
                    # Tier 2: count didn't decrease either
                    self._test_fail_loop_count += 1
                else:
                    # Genuine progress — reset both counters
                    self._test_fail_loop_count = 0

                self._last_failure_signature = current_sig
                self._last_test_failure_count = failures_cnt

                # --- Check thresholds ---
                sig_deadlock = (
                    current_sig == self._last_failure_signature
                    and self._test_fail_loop_count >= STUCK_SIG_LIMIT
                )
                count_deadlock = self._test_fail_loop_count >= self.MAX_TEST_FAIL_LOOPS

                if sig_deadlock or count_deadlock:
                    reason = (
                        f"identical error signature repeated {self._test_fail_loop_count} times"
                        if sig_deadlock
                        else f"no error-count reduction for {self._test_fail_loop_count} consecutive compile attempts"
                    )
                    print(
                        f"-> [{self.__class__.__name__}] 🛑 DEADLOCK DETECTED ({reason}). "
                        "Forcing early exit so iterations are not wasted."
                    )
                    return {
                        "exit_code": status,
                        "success": False,
                        "DEADLOCK_DETECTED": True,
                        "errors": (
                            f"🛑 DEADLOCK DETECTED: Agent is stuck — {reason}.\n"
                            "The remaining errors cannot be resolved through further edits.\n"
                            "Calling submit_final_answer now with current migration state.\n\n"
                            + "\n".join(all_errors[:30])
                        ),
                    }
            # ── End deadlock detection ─────────────────────────────────────────

            filtered = [line for line in output.splitlines() if len(line) <= 800 and "-classpath" not in line]
            truncated = "\n".join(filtered[:75]) + "\n... [TRUNCATED] ...\n" + "\n".join(filtered[-75:]) if len(filtered) > 150 else "\n".join(filtered)

            errors_str = ("\n".join(compiler_errors) if compiler_errors else "\n".join(test_failures)) + "\n\nLog:\n" + truncated
            return {"exit_code": status, "success": False, "errors": errors_str}
        except Exception as e:
            return {"error": f"Failed to compile: {e}"}


    def _tool_write_file(self, file_path: str, content: str, **kwargs) -> str:
        try:
            lock_err = self._check_main_source_lock(file_path)
            if lock_err:
                return lock_err
            path = self._resolve_path(file_path)
            old_content = path.read_text(encoding="utf-8") if path.exists() else ""
            hacking_err = self._validate_reward_hacking(file_path, old_content, content)
            if hacking_err:
                return hacking_err

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            self._last_edit_count += 1
            lines = content.splitlines()
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            return f"Overwrote {file_path} content successfully.\nNew content:\n" + "\n".join(numbered)
        except Exception as e:
            return f"Error writing file: {e}"

    def _tool_list_project_files(self, relative_path: str = "", **kwargs) -> str:
        try:
            root = Path(self.project_path)
            if relative_path:
                root = root / relative_path
            if not root.exists():
                return f"Path {relative_path} does not exist."

            def build_tree(path: Path, prefix: str = "") -> list[str]:
                if path.name in (".git", "target", ".idea", ".vscode", "__pycache__"):
                    return []
                lines = []
                try:
                    entries = sorted(list(path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
                except Exception:
                    return []
                for i, entry in enumerate(entries):
                    if entry.name in (".git", "target", ".idea", ".vscode", "__pycache__"):
                        continue
                    is_last = (i == len(entries) - 1)
                    connector = "└── " if is_last else "├── "
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    if entry.is_dir():
                        lines.append(f"{prefix}{connector}{entry.name}/")
                        lines.extend(build_tree(entry, next_prefix))
                    else:
                        lines.append(f"{prefix}{connector}{entry.name}")
                return lines

            tree = build_tree(root)
            return "\n".join(tree) if tree else "No files found."
        except Exception as e:
            return f"Error listing directory: {e}"

    def _tool_fetch_migration_rule(self, keywords: list[str], **kwargs) -> dict[str, Any]:
        try:
            rule_file = Path("D:/capstone_project/MYGRATE---Capstone-Project/migration_rules.json")
            if not rule_file.exists():
                rule_file = Path(self.project_path).parent / "migration_rules.json"
            if not rule_file.exists():
                rule_file = Path(__file__).resolve().parent.parent.parent / "migration_rules.json"
            if not rule_file.exists():
                return {"error": "migration_rules.json file not found."}

            data = json.loads(rule_file.read_text(encoding="utf-8"))
            rules = data.get("rules", [])
            matched = []
            for rule in rules:
                rule_id = rule.get("rule_id", "").lower()
                target = rule.get("target", "").lower()
                reason = rule.get("reason", "").lower()
                if any(kw.lower().strip() in rule_id or kw.lower().strip() in target or kw.lower().strip() in reason for kw in keywords):
                    matched.append(rule)
            return {"keywords": keywords, "found_rules": matched}
        except Exception as e:
            return {"error": f"Failed to query migration rules: {e}"}

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
        try:
            # Bug fix: fall back to self.project_path when caller omits the arg
            p_path = Path(project_path or self.project_path)
            root_pom = p_path / "pom.xml"
            if not root_pom.exists():
                return {"status": "error", "error": f"No root pom.xml found"}
            project = MavenProject(str(root_pom))
            editor = project.get_pom_editor(module)

            if action == "add_dependency":
                editor.add_dependency(group_id, artifact_id, version, scope=scope)
                return {"status": "ok", "message": f"Added dependency {group_id}:{artifact_id}:{version}"}
            elif action == "update_dependency":
                if editor.dependency_exists(group_id, artifact_id):
                    def update_func(dep_elem):
                        version_elem = editor.ensure_element(dep_elem, "m:version")
                        version_elem.text = version
                        if scope:
                            scope_elem = editor.ensure_element(dep_elem, "m:scope")
                            scope_elem.text = scope
                    editor.update_dependency(group_id, artifact_id, update_func)
                    return {"status": "ok", "message": f"Updated dependency {group_id}:{artifact_id} to version {version}"}
                else:
                    editor.add_dependency(group_id, artifact_id, version, scope=scope)
                    return {"status": "ok", "message": f"Added dependency {group_id}:{artifact_id}:{version}"}
            elif action == "ensure_property":
                # Anti-reward-hacking: block test-skip properties being set to true
                _SKIP_TEST_PROPS = {"skiptests", "skipits", "maven.test.skip", "maven.test.failure.ignore"}
                if property_name and property_name.lower() in _SKIP_TEST_PROPS:
                    if str(version or "").strip().lower() == "true":
                        return {"status": "error", "error": "⚠️ REWARD HACKING BLOCKED: Setting test-skip property to 'true' in pom.xml is forbidden."}
                editor.ensure_property(property_name, version)
                return {"status": "ok", "message": f"Property {property_name} set to {version}"}
            elif action == "update_element_text":
                # Anti-reward-hacking: block skipTests/maven.test.skip element updates to true
                _SKIP_XPATHS = ("skiptests", "skipits", "maven.test.skip", "maven.test.failure.ignore")
                if xpath and any(s in xpath.lower() for s in _SKIP_XPATHS):
                    if str(version or "").strip().lower() == "true":
                        return {"status": "error", "error": "⚠️ REWARD HACKING BLOCKED: Setting test-skip element to 'true' in pom.xml is forbidden."}
                editor.update_element_text(xpath, version)
                return {"status": "ok", "message": f"Updated elements at xpath '{xpath}' to '{version}'"}
            else:
                return {"status": "error", "error": f"Unknown action: {action}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _tool_run_maven_command(
        self,
        project_path: str = "",
        goal: str = "compile",
        clean: bool = False,
        skip_tests: bool = False,
        target_java_version: str = "17",
        **kwargs,
    ) -> dict[str, Any]:
        try:
            # Bug fix: fall back to self.project_path when caller omits the arg
            resolved_path = project_path or self.project_path
            if not resolved_path:
                return {"status": "error", "error": "project_path is not set. Cannot run Maven command."}
            p_path = Path(resolved_path)
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
            return {"status": "ok" if res.status == 0 else "fail", "exit_code": res.status, "stdout": res.stdout, "stderr": res.stderr}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Utility Helpers ──

    def _resolve_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if not path.is_absolute():
            path = Path(self.project_path) / path
        return path

    def _check_main_source_lock(self, file_path: str) -> str | None:
        normalized = str(Path(file_path)).replace("\\", "/")
        if "src/test/" in normalized:
            return f"🔒 TEST LOCK: File {file_path} is under src/test/ which is strictly forbidden from being modified."
        if not self._main_source_locked:
            return None
        if "src/main/java" in normalized and normalized.endswith(".java"):
            return f"🔒 CODE LOCK: File {file_path} is under src/main/java which is locked (compiled successfully)."
        return None

    def _validate_reward_hacking(self, file_path: str, old_content: str, new_content: str) -> str | None:
        path = Path(file_path)
        if path.name == "pom.xml":
            old_skips = re.findall(r"<(skipTests|skipITs|maven\.test\.skip)>\s*true\s*</\1>", old_content)
            new_skips = re.findall(r"<(skipTests|skipITs|maven\.test\.skip)>\s*true\s*</\1>", new_content)
            if len(new_skips) > len(old_skips):
                return "⚠️ REWARD HACKING DETECTED: Setting test skipping to true in pom.xml is forbidden."
        normalized_path = str(path).replace("\\", "/")
        if "src/test/java" in normalized_path and normalized_path.endswith(".java"):
            def strip_comments(text: str) -> str:
                text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
                return re.sub(r'//.*', '', text)
            old_stripped = strip_comments(old_content)
            new_stripped = strip_comments(new_content)
            if len(re.findall(r'@(?:Ignore|Disabled)\b', new_stripped)) > len(re.findall(r'@(?:Ignore|Disabled)\b', old_stripped)):
                return "⚠️ REWARD HACKING DETECTED: Adding @Ignore or @Disabled is forbidden."
            if len(re.findall(r'@Test\b', new_stripped)) < len(re.findall(r'@Test\b', old_stripped)):
                return "⚠️ REWARD HACKING DETECTED: Deleting @Test methods is forbidden."
            assertion_pattern = r'\b(?:assert[A-Z]\w*|fail|verify|verifyNoMoreInteractions|verifyZeroInteractions)\s*\('
            old_asserts = len(re.findall(assertion_pattern, old_stripped)) + len(re.findall(r'\bassert\s+[^;]+;', old_stripped))
            new_asserts = len(re.findall(assertion_pattern, new_stripped)) + len(re.findall(r'\bassert\s+[^;]+;', new_stripped))
            if new_asserts < old_asserts:
                return "⚠️ REWARD HACKING DETECTED: Deleting assertions is forbidden."
            if len(re.findall(r'\breturn\s*;', new_stripped)) > len(re.findall(r'\breturn\s*;', old_stripped)):
                return "⚠️ REWARD HACKING DETECTED: Adding early return to test method is forbidden."
        return None

    def _post_process(self, results: dict[str, Any], instruction: str, payload: dict[str, Any]) -> str:
        merged = dict(results)
        jdeprscan = results.get("run_jdeprscan")
        if isinstance(jdeprscan, dict) and ("jdeprscan" not in merged or not merged["jdeprscan"]):
            merged["jdeprscan"] = jdeprscan
        change_plan = results.get("build_change_plan")
        if isinstance(change_plan, dict):
            for k, v in change_plan.items():
                if k not in merged:
                    merged[k] = v
        enrich = results.get("enrich_report")
        if isinstance(enrich, dict) and enrich.get("status") != "skipped":
            for k, v in enrich.items():
                if k not in merged:
                    merged[k] = v
        return json.dumps(merged, ensure_ascii=False, indent=2, default=str)
