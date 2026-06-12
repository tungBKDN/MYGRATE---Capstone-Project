from __future__ import annotations

import json
import re
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from src.agents.base_agent import BaseAgent, ToolDefinition
from src.tools.maven import MavenRunner


class TranslatorAgent_2(BaseAgent):
    """
    TranslatorAgent_2 — batch-edit migration agent with classpath & Maven plugin awareness.

    Workflow:
        1. read_file   →  inspect current source (with line numbers)
        2. check_class →  verify if a class exists in Maven dependencies before removing imports
        3. check_maven_plugin →  verify if a Maven plugin version exists on Maven Central
        4. apply_edits →  submit ALL changes as line-based edits (NO auto-compile)
        5. compile_project →  compile once to verify all changes
        6. (if errors) →  apply_edits again to fix, then compile again
    """

    READ_FILE_KEEP_MESSAGES = 10

    def __init__(self, model_name: str | None = None):
        super().__init__(model_name)
        self.project_path = ""
        self.current_file = ""
        self.MAX_ITERATIONS = 30
        self._log_entries: list[str] = []
        self._last_edit_count = 0  # track edits since last compile
        self._classpath_cache: dict[str, set[str]] = {}  # jar_path -> set of class names
        self._maven_plugin_cache: dict[str, bool] = {}  # "groupId:artifactId:version" -> exists

    def get_prompt_file(self) -> str | None:
        return "translator_2.md"

    def run(self, instruction: str) -> str:
        payload = self._parse_instruction(instruction)
        self.project_path = payload.get("project_path", "")
        self._log_entries = []
        self._last_edit_count = 0
        self._classpath_cache = {}
        self._maven_plugin_cache = {}
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

    # ── Maven plugin verification ──

    def _check_maven_plugin_exists(self, group_id: str, artifact_id: str, version: str) -> dict[str, Any]:
        """Check if a Maven plugin version exists on Maven Central.

        Uses the Maven Central Search API to verify the plugin exists
        before the agent tries to add or uncomment it in pom.xml.
        """
        cache_key = f"{group_id}:{artifact_id}:{version}"
        if cache_key in self._maven_plugin_cache:
            exists = self._maven_plugin_cache[cache_key]
            if exists:
                self._log(f"[check_maven_plugin] {cache_key} → EXISTS (cached)")
                return {
                    "group_id": group_id,
                    "artifact_id": artifact_id,
                    "version": version,
                    "exists": True,
                    "message": f"Plugin {group_id}:{artifact_id}:{version} EXISTS on Maven Central. Safe to use."
                }
            else:
                self._log(f"[check_maven_plugin] {cache_key} → NOT FOUND (cached)")
                return {
                    "group_id": group_id,
                    "artifact_id": artifact_id,
                    "version": version,
                    "exists": False,
                    "message": f"Plugin {group_id}:{artifact_id}:{version} DOES NOT EXIST on Maven Central. "
                               f"Do NOT use this version. Comment out the plugin or find a valid version."
                }

        # First check local .m2 repository
        local_jar = self._find_jar_in_m2(group_id, artifact_id, version)
        if local_jar is not None:
            self._maven_plugin_cache[cache_key] = True
            self._log(f"[check_maven_plugin] {cache_key} → EXISTS (local .m2)")
            return {
                "group_id": group_id,
                "artifact_id": artifact_id,
                "version": version,
                "exists": True,
                "message": f"Plugin {group_id}:{artifact_id}:{version} EXISTS in local Maven repository. Safe to use."
            }

        # Then check Maven Central Search API
        try:
            url = (
                f"https://search.maven.org/solrsearch/select?"
                f"q=g:{group_id}+AND+a:{artifact_id}+AND+v:{version}"
                f"&rows=5&wt=json"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mygrate-Agent/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                num_found = data.get("response", {}).get("numFound", 0)
                exists = num_found > 0
        except Exception as e:
            # If Maven Central API is unreachable, try a direct POM check
            self._log(f"[check_maven_plugin] Maven Central API error: {e}")
            try:
                group_path = group_id.replace(".", "/")
                pom_url = f"https://repo1.maven.org/maven2/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
                req = urllib.request.Request(pom_url, headers={"User-Agent": "Mygrate-Agent/1.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    exists = response.status == 200
            except Exception:
                exists = False  # Assume not found if we can't verify

        self._maven_plugin_cache[cache_key] = exists

        if exists:
            self._log(f"[check_maven_plugin] {cache_key} → EXISTS")
            return {
                "group_id": group_id,
                "artifact_id": artifact_id,
                "version": version,
                "exists": True,
                "message": f"Plugin {group_id}:{artifact_id}:{version} EXISTS on Maven Central. Safe to use."
            }
        else:
            self._log(f"[check_maven_plugin] {cache_key} → NOT FOUND")
            return {
                "group_id": group_id,
                "artifact_id": artifact_id,
                "version": version,
                "exists": False,
                "message": f"Plugin {group_id}:{artifact_id}:{version} DOES NOT EXIST on Maven Central. "
                           f"Do NOT use this version. Comment out the plugin or find a valid version."
            }

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
                name="check_maven_plugin",
                description=(
                    "Check if a Maven plugin version exists on Maven Central. "
                    "MUST call this BEFORE adding, uncommenting, or changing any Maven plugin in pom.xml. "
                    "If the plugin version does NOT exist, you MUST comment it out or use a valid version. "
                    "Provide groupId, artifactId, and version (e.g. 'org.apache.maven.plugins', 'maven-jdeprscan-plugin', '3.1.2')."
                ),
                func=self._tool_check_maven_plugin,
                parameters={
                    "type": "object",
                    "properties": {
                        "group_id": {
                            "type": "string",
                            "description": "Maven groupId (e.g. 'org.apache.maven.plugins')",
                        },
                        "artifact_id": {
                            "type": "string",
                            "description": "Maven artifactId (e.g. 'maven-jdeprscan-plugin')",
                        },
                        "version": {
                            "type": "string",
                            "description": "Plugin version to check (e.g. '3.1.2')",
                        }
                    },
                    "required": ["group_id", "artifact_id", "version"]
                }
            ),
            ToolDefinition(
                name="apply_edits",
                description=(
                    "Apply multiple line-based edits to a file in a single call. Does NOT compile. "
                    "Each edit specifies start_line and end_line (1-based, inclusive) and the replacement text. "
                    "Edits are applied bottom-to-top so line numbers stay valid. "
                    "After calling this, you MUST call compile_project to verify your changes.\n\n"
                    "WARNING: When editing pom.xml, do NOT uncomment or add Maven plugins without first "
                    "calling check_maven_plugin to verify the version exists. If a plugin version is not "
                    "found on Maven Central, keep it commented out."
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
            ToolDefinition(
                name="write_file",
                description="Overwrite the entire content of a file with new code. Use this if incremental edits fail repeatedly and you need to rewrite the whole file.",
                func=self._tool_write_file,
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the Java source file relative to project root",
                        },
                        "content": {
                            "type": "string",
                            "description": "The complete new content of the file",
                        }
                    },
                    "required": ["file_path", "content"]
                }
            ),
            ToolDefinition(
                name="list_project_files",
                description=(
                    "Recursively list all directories and files under the project path. "
                    "Use this tool to index the codebase, see the directory structure, and find where java classes, "
                    "packages, and files are located to know how they should be imported."
                ),
                func=self._tool_list_project_files,
                parameters={
                    "type": "object",
                    "properties": {
                        "relative_path": {
                            "type": "string",
                            "description": "Optional relative path under the project root to list files from (e.g. 'src/main/java')",
                        }
                    },
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

    def _tool_check_maven_plugin(self, group_id: str, artifact_id: str, version: str, **kwargs) -> dict[str, Any]:
        """Check if a Maven plugin version exists on Maven Central."""
        try:
            return self._check_maven_plugin_exists(group_id, artifact_id, version)
        except Exception as e:
            self._log(f"[check_maven_plugin] ERROR: {e}")
            return {"error": f"Failed to check Maven plugin: {e}"}

    def _tool_write_file(self, file_path: str, content: str, **kwargs) -> str:
        try:
            path = self._resolve_path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            self._log(f"[write_file] Overwrote entire file {file_path}")
            self._last_edit_count += 1
            
            # Format and return the entire updated file content with line numbers
            lines = content.splitlines()
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            numbered_content = "\n".join(numbered)
            
            return (
                f"Successfully overwrote {file_path} with new content.\n"
                f"New File Content of {file_path}:\n"
                f"--------------------------------------------------\n"
                f"{numbered_content}\n"
                f"--------------------------------------------------\n"
                f"Please call compile_project now to verify your changes."
            )
        except Exception as e:
            self._log(f"[write_file] ERROR: {e}")
            return f"Error writing file {file_path}: {e}"

    def _tool_list_project_files(self, relative_path: str = "", **kwargs) -> str:
        """Recursively list all directories and files in the project path, skipping build and git directories."""
        try:
            root = Path(self.project_path)
            if relative_path:
                root = root / relative_path
            
            if not root.exists():
                return f"Error: Path {relative_path} does not exist."
            
            # Simple recursive tree builder
            def build_tree(path: Path, prefix: str = "") -> list[str]:
                # Skip build and version control directories
                if path.name in (".git", "target", ".idea", ".vscode", "__pycache__"):
                    return []
                
                lines = []
                try:
                    entries = [
                        x for x in list(path.iterdir())
                        if x.name not in (".git", "target", ".idea", ".vscode", "__pycache__")
                    ]
                    entries = sorted(entries, key=lambda x: (not x.is_dir(), x.name.lower()))
                except Exception as e:
                    return [f"{prefix}└── [Error reading directory: {e}]"]

                for i, entry in enumerate(entries):
                    is_last = (i == len(entries) - 1)
                    connector = "└── " if is_last else "├── "
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    
                    if entry.is_dir():
                        lines.append(f"{prefix}{connector}{entry.name}/")
                        lines.extend(build_tree(entry, next_prefix))
                    else:
                        lines.append(f"{prefix}{connector}{entry.name}")
                return lines

            tree_lines = build_tree(root)
            self._log(f"[list_project_files] Listed directory tree for {relative_path or 'root'}")
            if not tree_lines:
                return f"No files found in {relative_path or 'project root'}."
            return "\n".join(tree_lines)
        except Exception as e:
            self._log(f"[list_project_files] ERROR: {e}")
            return f"Error listing directory: {e}"

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
        """Apply multiple line-based edits, sorted bottom-to-top. Does NOT compile.

        Includes pom.xml protection: warns if edits modify Maven plugin versions
        without prior verification via check_maven_plugin.
        """
        try:
            path = self._resolve_path(file_path)
            if not path.exists():
                return f"Error: File {file_path} does not exist."
            self.current_file = str(path)

            if not edits:
                return "Error: No edits provided."

            # ── POM.XML PROTECTION ──
            # If editing pom.xml, check for plugin version changes that haven't been verified
            if path.name == "pom.xml":
                content_before = path.read_text(encoding="utf-8")
                lines_before = content_before.splitlines()

                unverified_plugins = []
                for edit in edits:
                    start = int(edit.get("start_line", 0))
                    end = int(edit.get("end_line", start))
                    replacement = edit.get("replacement", "")

                    # Check if the replacement contains a plugin version that's being uncommented or added
                    # Look for patterns like <version>X.Y.Z</version> inside <plugin> blocks
                    if "<version>" in replacement:
                        # Extract version numbers from the replacement
                        version_matches = re.findall(r"<version>([^<]+)</version>", replacement)
                        for ver in version_matches:
                            # Skip property references like ${something}
                            if ver.startswith("${"):
                                continue
                            # Check if this version was already in the file (existing plugin)
                            # by looking at the lines being replaced
                            old_lines = "\n".join(lines_before[max(0, start-1):end])
                            if f"<version>{ver}</version>" in old_lines:
                                continue  # Version already existed, just moving it

                            # Try to extract groupId/artifactId from context
                            context_start = max(0, start - 10)
                            context_end = min(len(lines_before), end + 10)
                            context = "\n".join(lines_before[context_start:context_end]) + "\n" + replacement

                            gid_match = re.search(r"<groupId>([^<]+)</groupId>", context)
                            aid_match = re.search(r"<artifactId>([^<]+)</artifactId>", context)

                            if gid_match and aid_match:
                                gid = gid_match.group(1).strip()
                                aid = aid_match.group(1).strip()
                                
                                # Check if this version is actually inside a <plugin> block in the entire file
                                line_char_idx = sum(len(l) + 1 for l in lines_before[:start - 1])
                                last_dep = content_before.rfind("<dependency>", 0, line_char_idx)
                                last_plugin = content_before.rfind("<plugin>", 0, line_char_idx)
                                is_plugin = (last_plugin > last_dep)
                                
                                if is_plugin:
                                    cache_key = f"{gid}:{aid}:{ver}"
                                    if cache_key not in self._maven_plugin_cache:
                                        unverified_plugins.append({
                                            "group_id": gid,
                                            "artifact_id": aid,
                                            "version": ver,
                                            "line_range": f"{start}-{end}"
                                        })

                if unverified_plugins:
                    plugin_list = "\n".join([
                        f"  - {p['group_id']}:{p['artifact_id']}:{p['version']} (lines {p['line_range']})"
                        for p in unverified_plugins
                    ])
                    self._log(f"[apply_edits] WARNING: Unverified Maven plugin versions in pom.xml edit:\n{plugin_list}")
                    return (
                        f"⚠️ BLOCKED: You are editing pom.xml and the following Maven plugin versions "
                        f"have NOT been verified with check_maven_plugin:\n{plugin_list}\n\n"
                        f"Call check_maven_plugin for EACH plugin version before editing pom.xml. "
                        f"If a plugin version does not exist on Maven Central, keep the plugin commented out."
                    )

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

            # Overlap check
            validated_sorted = sorted(validated, key=lambda x: x[0])
            for i in range(len(validated_sorted) - 1):
                current_end = validated_sorted[i][1]
                next_start = validated_sorted[i+1][0]
                if current_end >= next_start:
                    return (
                        f"Error: Overlapping edits detected. "
                        f"Edit {i} ends at line {current_end}, but Edit {i+1} starts at line {next_start}. "
                        f"Please consolidate overlapping edits into a single replacement chunk or separate them."
                    )

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
            
            # Format and return the entire updated file content with line numbers
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            numbered_content = "\n".join(numbered)
            
            return (
                f"Applied {len(validated)} edit(s) to {file_path}.\n"
                f"New File Content of {file_path}:\n"
                f"--------------------------------------------------\n"
                f"{numbered_content}\n"
                f"--------------------------------------------------\n"
                f"Please call compile_project now to verify your changes."
            )

        except Exception as e:
            self._log(f"[apply_edits] ERROR: {e}")
            return f"Error applying edits to {file_path}: {e}"

    def _tool_compile_project(self, **kwargs) -> dict[str, Any]:
        """Compile project under JDK 17 and return ALL compile errors."""
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

            self._log(f"[compile_project] exit_code={status}, failed compilation")

            # Extract java compiler errors cleanly
            compiler_errors = []
            in_error_block = False
            for line in output.splitlines():
                if "COMPILATION ERROR :" in line:
                    in_error_block = True
                    continue
                if in_error_block:
                    if line.startswith("[INFO]") and "error" in line.lower() and ("errors" in line.lower() or line.strip().endswith("error")):
                        in_error_block = False
                    elif line.startswith("[ERROR]"):
                        compiler_errors.append(line)

            # Clean and truncate full output to avoid context window blowup and hangs
            filtered_lines = []
            for line in output.splitlines():
                if len(line) > 800 or "-classpath" in line or " -d " in line or "-bootclasspath" in line:
                    continue
                filtered_lines.append(line)
            
            if len(filtered_lines) > 150:
                truncated_output = (
                    "\n".join(filtered_lines[:75]) + 
                    "\n... [TRUNCATED IN-BETWEEN LINES / CLASS PATH / DEBUG INFOS TO SAVE CONTEXT] ...\n" + 
                    "\n".join(filtered_lines[-75:])
                )
            else:
                truncated_output = "\n".join(filtered_lines)

            if compiler_errors:
                cleaned_errors = "\n".join(compiler_errors)
                errors_str = (
                    f"Maven compilation failed with the following JAVA COMPILER ERRORS:\n"
                    f"--------------------------------------------------\n"
                    f"{cleaned_errors}\n"
                    f"--------------------------------------------------\n\n"
                    f"Truncated maven output (cleaned log):\n"
                    f"{truncated_output}"
                )
            else:
                errors_str = truncated_output

            return {
                "exit_code": status,
                "success": False,
                "errors": errors_str
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