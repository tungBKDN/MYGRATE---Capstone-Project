from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent, ToolDefinition
from src.tools.maven import MavenRunner


class TranslatorAgent_2(BaseAgent):
    """
    TranslatorAgent_2 — batch-edit migration agent with classpath awareness.

    Workflow:
        1. read_file   →  inspect current source (with line numbers)
        2. check_class →  verify if a class exists in Maven dependencies before removing imports
        3. apply_edits →  submit ALL changes as line-based edits (NO auto-compile)
        4. compile_project →  compile once to verify all changes
        5. (if errors) →  apply_edits again to fix, then compile again
    """

    READ_FILE_KEEP_MESSAGES = 6

    def __init__(self, model_name: str | None = None):
        super().__init__(model_name)
        self.project_path = ""
        self.current_file = ""
        self.MAX_ITERATIONS = 15
        self._log_entries: list[str] = []
        self._last_edit_count = 0  # track edits since last compile
        self._classpath_cache: dict[str, set[str]] = {}  # jar_path -> set of class names

    def get_prompt_file(self) -> str | None:
        return "translator_2.md"

    def run(self, instruction: str) -> str:
        payload = self._parse_instruction(instruction)
        self.project_path = payload.get("project_path", "")
        self._log_entries = []
        self._last_edit_count = 0
        self._classpath_cache = {}
        return super().run(instruction)

    def _log(self, entry: str):
        self._log_entries.append(entry)

    def get_log(self) -> str:
        return "\n".join(self._log_entries)

    # ── Classpath inspection ──

    def _parse_pom_dependencies(self) -> list[dict[str, str]]:
        """Parse pom.xml to extract dependency coordinates (groupId, artifactId, version)."""
        pom_path = Path(self.project_path) / "pom.xml"
        if not pom_path.exists():
            return []

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(pom_path)
            root = tree.getroot()
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}

            # Try with namespace first, then without
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
        """Extract text from an XML child element."""
        if ns:
            child = element.find(f"m:{tag}", ns)
        else:
            child = element.find(tag)
        return child.text.strip() if child is not None and child.text else None

    def _find_jar_in_m2(self, group_id: str, artifact_id: str, version: str) -> Path | None:
        """Find a dependency JAR in the local Maven repository (~/.m2/repository)."""
        m2 = Path.home() / ".m2" / "repository"
        # Convert groupId dots to path segments: org.sonarsource.sonarqube → org/sonarsource/sonarqube
        group_path = group_id.replace(".", "/")
        jar_path = m2 / group_path / artifact_id / version / f"{artifact_id}-{version}.jar"
        if jar_path.exists():
            return jar_path

        # Try with -sources suffix
        sources_path = m2 / group_path / artifact_id / version / f"{artifact_id}-{version}-sources.jar"
        if sources_path.exists():
            return sources_path

        return None

    def _list_classes_in_jar(self, jar_path: Path) -> set[str]:
        """List all fully-qualified class names in a JAR file (caches results)."""
        key = str(jar_path)
        if key in self._classpath_cache:
            return self._classpath_cache[key]

        classes = set()
        try:
            with zipfile.ZipFile(jar_path) as zf:
                for name in zf.namelist():
                    if name.endswith(".class") and "$" not in name:
                        # Convert org/sonar/api/Server.class → org.sonar.api.Server
                        fqn = name[:-6].replace("/", ".")  # strip .class, convert / to .
                        classes.add(fqn)
        except Exception as e:
            self._log(f"[check_class] Error reading JAR {jar_path}: {e}")

        self._classpath_cache[key] = classes
        return classes

    def _resolve_dependency_version(self, group_id: str, artifact_id: str, version: str) -> str:
        """Resolve property placeholders like ${sonar.version} from pom.xml."""
        if not version.startswith("${"):
            return version

        # Extract property name: ${sonar.version} → sonar.version
        prop_name = version[2:-1]
        pom_path = Path(self.project_path) / "pom.xml"
        if not pom_path.exists():
            return version

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(pom_path)
            root = tree.getroot()
            ns = {"m": "http://maven.apache.org/POM/4.0.0"}

            # Search in <properties>
            props = root.find("m:properties", ns)
            if props is None:
                props = root.find("properties")
            if props is not None:
                for child in props:
                    tag = child.tag
                    if "}" in tag:
                        tag = tag.split("}", 1)[1]
                    if tag == prop_name and child.text:
                        return child.text.strip()
        except Exception:
            pass

        return version  # return as-is if can't resolve

    # ── Message history management ──

    def _invoke_with_retry(
        self,
        llm_with_tools: Any,
        messages: list,
        tool_map: dict[str, ToolDefinition],
        payload: dict[str, Any],
        react_tool_results: dict[str, Any],
    ) -> Any | None:
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

    # ── Tools ──

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="read_file",
                description="Read the full content of a file (with line numbers). Use this first to inspect the file's current state.",
                func=self._tool_read_file,
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the Java source file relative to project root",
                        }
                    },
                    "required": ["file_path"]
                }
            ),
            ToolDefinition(
                name="check_class",
                description=(
                    "Check if a class exists in the project's Maven dependencies (classpath). "
                    "Use this BEFORE removing or replacing any import statement. "
                    "Provide the fully-qualified class name (e.g. 'org.sonar.api.batch.postjob.PostJob'). "
                    "Returns whether the class EXISTS in the current classpath, so you know if the import is valid."
                ),
                func=self._tool_check_class,
                parameters={
                    "type": "object",
                    "properties": {
                        "class_name": {
                            "type": "string",
                            "description": "Fully-qualified class name to check (e.g. 'org.sonar.api.platform.Server')",
                        }
                    },
                    "required": ["class_name"]
                }
            ),
            ToolDefinition(
                name="apply_edits",
                description=(
                    "Apply multiple line-based edits to a file in a single call. Does NOT compile. "
                    "Each edit specifies start_line and end_line (1-based, inclusive) and the replacement text. "
                    "Edits are applied bottom-to-top so line numbers stay valid. "
                    "After calling this, you MUST call compile_project to verify your changes."
                ),
                func=self._tool_apply_edits,
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the Java source file relative to project root",
                        },
                        "edits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "start_line": {
                                        "type": "integer",
                                        "description": "Start line number to replace (1-based, inclusive)",
                                    },
                                    "end_line": {
                                        "type": "integer",
                                        "description": "End line number to replace (1-based, inclusive). Same as start_line for single-line edit.",
                                    },
                                    "replacement": {
                                        "type": "string",
                                        "description": "The replacement text for the line range. Use \\n for newlines.",
                                    }
                                },
                                "required": ["start_line", "end_line", "replacement"]
                            },
                            "description": "Array of edits. Each edit replaces lines start_line through end_line (inclusive) with replacement text. Order does not matter — edits are sorted and applied bottom-to-top."
                        }
                    },
                    "required": ["file_path", "edits"]
                }
            ),
            ToolDefinition(
                name="compile_project",
                description=(
                    "Compile the project using Maven under JDK 17. Call this AFTER applying edits to verify your changes. "
                    "Returns ALL compile errors (not filtered by file) so you can see which files need fixing."
                ),
                func=self._tool_compile_project,
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
        ]

    # ── Tool implementations ──

    def _resolve_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if not path.is_absolute():
            path = Path(self.project_path) / path
        return path

    def _tool_check_class(self, class_name: str, **kwargs) -> dict[str, Any]:
        """Check if a class exists in the project's Maven classpath (dependency JARs)."""
        try:
            # Parse pom.xml to get dependencies
            deps = self._parse_pom_dependencies()

            # Convert class name to path: org.sonar.api.Server → org/sonar/api/Server.class
            class_path = class_name.replace(".", "/") + ".class"

            # Check each dependency JAR
            results = []
            for dep in deps:
                if dep.get("scope") == "test":
                    continue  # skip test-scoped deps for main source compilation
                version = self._resolve_dependency_version(dep["groupId"], dep["artifactId"], dep["version"])
                jar_path = self._find_jar_in_m2(dep["groupId"], dep["artifactId"], version)
                if jar_path is None:
                    continue

                classes = self._list_classes_in_jar(jar_path)
                if class_name in classes:
                    results.append({
                        "found": True,
                        "jar": f"{dep['groupId']}:{dep['artifactId']}:{version}",
                        "class_name": class_name,
                    })

            if results:
                self._log(f"[check_class] {class_name} → FOUND in {len(results)} dependency(ies)")
                return {
                    "class_name": class_name,
                    "exists": True,
                    "found_in": results,
                    "message": f"Class '{class_name}' EXISTS in the classpath. Keep the import — it is valid."
                }
            else:
                self._log(f"[check_class] {class_name} → NOT FOUND in any dependency JAR")
                return {
                    "class_name": class_name,
                    "exists": False,
                    "found_in": [],
                    "message": f"Class '{class_name}' does NOT exist in any project dependency JAR. "
                               "The import may need to be replaced or the class may have been removed from the API."
                }
        except Exception as e:
            self._log(f"[check_class] ERROR: {e}")
            return {"error": f"Failed to check class: {e}"}

    def _tool_read_file(self, file_path: str, **kwargs) -> str:
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                self._log(f"[read_file] ERROR: File {file_path} does not exist.")
                return f"Error: File {file_path} does not exist."
            self.current_file = str(path)
            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            self._log(f"[read_file] {file_path} ({len(lines)} lines)")
            return "\n".join(numbered)
        except Exception as e:
            self._log(f"[read_file] ERROR: {e}")
            return f"Error reading file {file_path}: {e}"

    def _tool_apply_edits(self, file_path: str, edits: list, **kwargs) -> str:
        """Apply multiple line-based edits, sorted bottom-to-top. Does NOT compile."""
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return f"Error: File {file_path} does not exist."
            self.current_file = str(path)

            if not edits:
                return "Error: No edits provided."

            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()

            validated = []
            for edit in edits:
                start = int(edit.get("start_line", 0))
                end = int(edit.get("end_line", start))
                replacement = edit.get("replacement", "")
                # Convert literal \n (backslash + n) to actual newlines.
                # LLMs sometimes pass \n as a literal two-char sequence instead of a newline.
                if "\\n" in replacement and "\n" not in replacement:
                    replacement = replacement.replace("\\n", "\n")
                if start < 1 or end < 1 or start > end:
                    return f"Error: Invalid line range start_line={start}, end_line={end}."
                if end > len(lines):
                    return f"Error: end_line={end} exceeds file length ({len(lines)} lines)."
                validated.append((start, end, replacement))

            validated.sort(key=lambda x: x[0], reverse=True)

            results = []
            for start, end, replacement in validated:
                original = "\n".join(lines[start - 1:end])
                new_lines = replacement.splitlines() if replacement else []
                lines[start - 1:end] = new_lines
                results.append(f"Lines {start}-{end}: {len(original)} chars → {len(replacement)} chars")
                self._log(f"[apply_edits] Lines {start}-{end} replaced")

            new_content = "\n".join(lines)
            path.write_text(new_content, encoding="utf-8")
            self._last_edit_count += len(validated)
            self._log(f"[apply_edits] {len(validated)} edit(s) applied to {file_path} (no compile yet)")
            return f"Applied {len(validated)} edit(s) to {file_path}. Call compile_project to verify.\n" + "\n".join(results)

        except Exception as e:
            self._log(f"[apply_edits] ERROR: {e}")
            return f"Error applying edits to {file_path}: {e}"

    def _tool_compile_project(self, **kwargs) -> dict[str, Any]:
        """Compile project under JDK 17 and return ALL compile errors (not filtered by file)."""
        try:
            # Guard: warn if calling compile without having made any edits since last compile
            if self._last_edit_count == 0:
                self._log(f"[compile_project] WARNING: called without any edits since last compile")

            project_path = Path(self.project_path)  # ensure Path, not str
            runner = MavenRunner(target_java_version="17")
            compile_res = runner.compile(project_path, clean=True)
            output = compile_res.stdout + "\n" + compile_res.stderr
            status = compile_res.status

            # Reset edit counter after compile
            self._last_edit_count = 0

            if status == 0:
                self._log(f"[compile_project] exit_code=0, SUCCESS")
                return {
                    "exit_code": 0,
                    "success": True,
                    "errors": "Project compiles successfully! No errors."
                }

            # Extract ALL error lines — don't filter by file
            all_errors = self._extract_all_errors(output)
            self._log(f"[compile_project] exit_code={status}, errors={len(all_errors.splitlines())} line(s)")

            return {
                "exit_code": status,
                "success": False,
                "errors": all_errors if all_errors else "Compilation failed but no specific error lines found. Full output:\n" + output[-2000:]
            }
        except Exception as e:
            self._log(f"[compile_project] ERROR: {e}")
            return {"error": f"Failed to run compilation: {e}"}

    def _extract_all_errors(self, compile_output: str) -> str:
        """Extract ALL error lines from Maven compile output, including detail lines.

        Maven prints errors in blocks like:
            [ERROR] /path/File.java:[25,52] cannot find symbol
            [ERROR]   symbol:   class PostJob
            [ERROR]   location: class org.sonar.plugins.stash.StashIssueReportingPostJob

        We include all [ERROR] lines so the agent sees the full context (symbol name, location, etc.).
        """
        lines = compile_output.split("\n")
        # Include ALL lines that are part of error output:
        # - Lines with [ERROR] (includes both primary errors and detail lines like "symbol:", "location:")
        # - Lines with .java: and error: (for non-[ERROR]-prefixed formats)
        error_lines = []
        for line in lines:
            if "[ERROR]" in line or (".java" in line and "error:" in line.lower()):
                error_lines.append(line)

        if not error_lines:
            return ""
        # Return up to 120 error lines — enough for the LLM to see full context
        return "\n".join(error_lines[:120])