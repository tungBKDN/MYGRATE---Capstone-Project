import logging
import os
import re
import subprocess
from pathlib import Path

from typing import Optional
from pydantic import BaseModel

from .maven_project import MavenProject
from .maven_pom_editor import MavenPomEditor

logger = logging.getLogger(__name__)


class CliResult(BaseModel):
    status: int
    stdout: str
    stderr: str
    total_tests: int = 0
    passed_tests: int = 0


class CoverageResult(BaseModel):
    status: int
    stdout: str
    stderr: str
    jacoco_xml_path: str
    coverage_found: bool
    line_coverage_pct: float
    missed_lines: int
    covered_lines: int
    total_tests: int = 0
    passed_tests: int = 0



class Maven:
    def __init__(self, target_java_version: str):
        self.target_java_version = target_java_version

    def _parse_test_counts(self, stdout: str) -> tuple[int, int]:
        total_tests = 0
        passed_tests = 0
        if not stdout:
            return 0, 0
        for line in stdout.splitlines():
            if "Tests run:" in line and " - in " not in line:
                match = re.search(
                    r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)(?:,\s*Skipped:\s*(\d+))?",
                    line,
                )
                if match:
                    total    = int(match.group(1))
                    failures = int(match.group(2))
                    errors   = int(match.group(3))
                    skipped  = int(match.group(4) or 0)
                    total_tests  += total
                    passed_tests += (total - failures - errors - skipped)
        return total_tests, passed_tests

    def _ensure_mvnw_executable(self, repo_path: Path):
        mvnw_path = repo_path / "mvnw"
        if mvnw_path.exists():
            current_permissions = os.stat(mvnw_path).st_mode
            # Add execute permissions for owner, group, and others
            new_permissions = current_permissions | 0o111
            os.chmod(mvnw_path, new_permissions)

    def _use_wrapper(self, repo_path: Path) -> bool:
        repo_path = Path(repo_path)  # ensure Path, not str
        return (repo_path / "mvnw").exists() and (repo_path / ".mvn" / "wrapper" / "maven-wrapper.properties").exists()

    def _get_base_cmd(self, repo_path: Path) -> str:
        repo_path = Path(repo_path)  # ensure Path, not str
        if self._use_wrapper(repo_path):
            self._ensure_mvnw_executable(repo_path)  # Call this before getting the command
            if os.name == "nt":
                return "mvnw.cmd"
            return "./mvnw"
        else:
            return "mvn"
    def _ensure_testng_version(self, root_editor: MavenPomEditor):
        testng_group_id = "org.testng"
        testng_artifact_id = "testng"
        target_testng_version = "6.14.3"  # Java 8 compatible version

        testng_dep_element = root_editor.get_dependency(testng_group_id, testng_artifact_id)
        if testng_dep_element is not None:
            root_editor.ensure_element(parent=testng_dep_element, tag="m:version", text=target_testng_version)
        else:
            mgmt_xpath = f".//m:dependencyManagement/m:dependencies/m:dependency[m:groupId='{testng_group_id}' and m:artifactId='{testng_artifact_id}']"
            managed_deps = root_editor.root.xpath(mgmt_xpath, namespaces=root_editor.namespaces)
            if managed_deps:
                managed_dep_element = managed_deps[0]
                root_editor.ensure_element(parent=managed_dep_element, tag="m:version", text=target_testng_version)
        root_editor._save()

    def _find_jdk8_home(self) -> Optional[str]:
        if "JAVA8_HOME" in os.environ:
            return os.environ["JAVA8_HOME"]
        import glob
        patterns = [
            os.path.join(os.path.expanduser("~"), "AppData", "Local", "Java", "jdk-8*"),
            r"C:\Program Files\Java\jdk1.8.0_*",
            r"C:\Program Files (x86)\Java\jdk1.8.0_*",
            r"C:\Program Files\Eclipse Adoptium\jdk-8*",
            r"C:\Program Files\AdoptOpenJDK\jdk-8*",
            r"C:\Program Files\Amazon Corretto\jdk1.8.0_*",
            r"C:\Program Files\Zulu\zulu-8*",
            r"C:\Program Files\LibericaJDK-8*",
        ]
        for pattern in patterns:
            matches = glob.glob(pattern)
            if matches:
                return sorted(matches)[-1]
        return None

    def _get_execution_env(self, target_version: str) -> dict:
        env = os.environ.copy()
        if target_version in ["1.6", "6", "1.7", "7", "1.8", "8"]:
            jdk8_home = self._find_jdk8_home()
            if jdk8_home:
                env["JAVA_HOME"] = jdk8_home
                path_sep = ";" if os.name == "nt" else ":"
                env["PATH"] = os.path.join(jdk8_home, "bin") + path_sep + env.get("PATH", "")
                logger.info(f"Auto-selected JDK 8 at {jdk8_home} for target version {target_version}")
                print(f"[MavenRunner] Auto-selected JDK 8 at: {jdk8_home} for target version: {target_version}")
        return env


    def _ensure_jacoco_argline(self, editor: MavenPomEditor) -> bool:
        plugins_to_configure = [
            ("org.apache.maven.plugins", "maven-surefire-plugin"),
            ("org.apache.maven.plugins", "maven-failsafe-plugin"),
        ]
        modified = False
        argline_prop = "${argLine}"

        for group_id, artifact_id in plugins_to_configure:
            plugin_element = editor.get_plugin(group_id, artifact_id)
            if plugin_element is not None:
                config_element = editor.ensure_element(plugin_element, "m:configuration")
                argline_elements = config_element.xpath("m:argLine", namespaces=editor.namespaces)

                if not argline_elements:
                    editor.create_sub_element(config_element, "m:argLine", text=argline_prop)
                    modified = True
                else:
                    argline_element = argline_elements[0]
                    current_text = argline_element.text if argline_element.text else ""
                    if argline_prop not in current_text:
                        separator = " " if current_text.strip() else ""
                        new_text = current_text.strip() + separator + argline_prop
                        argline_element.text = new_text
                        modified = True
        if modified:
            editor._save()
        return modified

    def _ensure_jacoco_plugin_configuration(
        self, editor: MavenPomEditor, prepare_agent: bool = True, report: bool = True, report_aggregate: bool = True
    ):
        group_id = "org.jacoco"
        artifact_id = "jacoco-maven-plugin"
        target_version = "0.8.12"

        desired_executions = []
        if prepare_agent:
            desired_executions.append({"id": "prepare-agent", "goals": ["prepare-agent"], "phase": "initialize"})
        if report:
            desired_executions.append({"id": "report", "goals": ["report"], "phase": "test"})
        if report_aggregate:
            desired_executions.append({"id": "report-aggregate", "goals": ["report-aggregate"], "phase": "test"})

        initial_plugin_exists = editor.plugin_exists(group_id, artifact_id)
        if initial_plugin_exists:
            existing_plugin_element = editor.get_plugin(group_id, artifact_id)
            if existing_plugin_element is not None:
                try:
                    parent = existing_plugin_element.getparent()
                    if parent is not None:
                        parent.remove(existing_plugin_element)
                        editor._save()
                except Exception:
                    pass
        try:
            editor.add_plugin(
                group_id=group_id, artifact_id=artifact_id, version=target_version, executions=desired_executions
            )
        except Exception:
            pass

    def _add_copy_app_classes_to_randoop_pom(self, project: MavenProject):
        editor = project.get_pom_editor("randoop-tests")
        ns = editor.namespaces
        build_elem = editor.ensure_element(".", "m:build")
        plugins_elem = editor.ensure_element(build_elem, "m:plugins")

        plugin_xpath = "m:plugin[m:groupId='org.apache.maven.plugins' and m:artifactId='maven-resources-plugin']"
        existing_plugins = plugins_elem.xpath(plugin_xpath, namespaces=ns)
        if existing_plugins:
            plugin_elem = existing_plugins[0]
        else:
            plugin_elem = editor.create_sub_element(plugins_elem, "m:plugin")
            editor.create_sub_element(plugin_elem, "m:groupId", text="org.apache.maven.plugins")
            editor.create_sub_element(plugin_elem, "m:artifactId", text="maven-resources-plugin")
            editor.create_sub_element(plugin_elem, "m:version", text="3.0.0")

        executions_elem = editor.ensure_element(plugin_elem, "m:executions")
        exec_xpath = "m:execution[m:id='copy-app-classes']"
        if not executions_elem.xpath(exec_xpath, namespaces=ns):
            exec_elem = editor.create_sub_element(executions_elem, "m:execution")
            editor.create_sub_element(exec_elem, "m:id", text="copy-app-classes")
            editor.create_sub_element(exec_elem, "m:phase", text="process-test-classes")
            goals_elem = editor.create_sub_element(exec_elem, "m:goals")
            editor.create_sub_element(goals_elem, "m:goal", text="copy-resources")

            config_elem = editor.create_sub_element(exec_elem, "m:configuration")
            editor.create_sub_element(config_elem, "m:outputDirectory", text="${project.build.outputDirectory}")
            resources_elem = editor.create_sub_element(config_elem, "m:resources")

            modules = project.get_modules()
            for mod in modules:
                res = editor.create_sub_element(resources_elem, "m:resource")
                editor.create_sub_element(res, "m:directory", text=f"${{project.parent.basedir}}/{mod}/target/classes")
                editor.create_sub_element(res, "m:filtering", text="false")
        editor._save()

    def compile(self, repo_path: Path, clean: bool = False) -> CliResult:
        # Uses test-compile which compiles both src/main/java AND src/test/java,
        # matching FreshBrew Gate 1: the full project (main + unit test) must compile.
        repo_path = Path(repo_path)  # ensure Path, not str
        cmd = [
            self._get_base_cmd(repo_path),
            "test-compile",
            "--batch-mode",
            "-U",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
        ]
        if self.target_java_version:
            cmd.extend([
                f"-Dmaven.compiler.source={self.target_java_version}",
                f"-Dmaven.compiler.target={self.target_java_version}"
            ])
        if clean:
            cmd.insert(1, "clean")
        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), env=self._get_execution_env(self.target_java_version), shell=(os.name == "nt"))
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )

    def test(self, repo_path: Path, skip_tests: bool = False, clean: bool = False, ignore_test_failures: bool = False) -> CliResult:
        repo_path = Path(repo_path)  # ensure Path, not str
        cmd = [
            self._get_base_cmd(repo_path),
            "verify",
            "--batch-mode",
            "-U",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
        ]
        if self.target_java_version:
            cmd.extend([
                f"-Dmaven.compiler.source={self.target_java_version}",
                f"-Dmaven.compiler.target={self.target_java_version}"
            ])
        if skip_tests:
            cmd.append("-DskipTests")
        if ignore_test_failures:
            cmd.append("-Dmaven.test.failure.ignore=true")
        if clean:
            cmd.insert(1, "clean")
        try:
            # Timeout increased to 300s to allow integration tests to run
            result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), env=self._get_execution_env(self.target_java_version), shell=(os.name == "nt"), timeout=300)
            stdout = result.stdout.decode("utf-8")
            stderr = result.stderr.decode("utf-8")
            total, passed = self._parse_test_counts(stdout)
            return CliResult(
                status=result.returncode,
                stdout=stdout,
                stderr=stderr,
                total_tests=total,
                passed_tests=passed
            )
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout.decode("utf-8") if e.stdout else ""
            stderr = (e.stderr.decode("utf-8") if e.stderr else "") + "\n[ERROR] Maven test execution timed out after 300 seconds. A test might be hanging or stuck in an infinite loop."
            total, passed = self._parse_test_counts(stdout)
            return CliResult(
                status=-1,
                stdout=stdout,
                stderr=stderr,
                total_tests=total,
                passed_tests=passed
            )

    def coverage(self, repo_path: Path, clean: bool = False) -> CoverageResult:
        repo_path = Path(repo_path)  # ensure Path, not str
        root_pom = repo_path / "pom.xml"

        # Prepare POM configuration if pom.xml exists
        if root_pom.exists():
            try:
                project = MavenProject(str(root_pom))
                root_editor = project.get_pom_editor()
                
                # Downgrade TestNG if found
                self._ensure_testng_version(root_editor)
                
                # Configure JaCoCo argLine and plugins based on multi-module status
                if project.is_multi_module() and "randoop-tests" in project.get_modules():
                    self._ensure_jacoco_argline(project.get_pom_editor("randoop-tests"))
                    self._ensure_jacoco_plugin_configuration(root_editor, prepare_agent=False, report=False, report_aggregate=True)
                    self._add_copy_app_classes_to_randoop_pom(project)
                    for module in project.get_modules():
                        try:
                            self._ensure_jacoco_plugin_configuration(
                                project.get_pom_editor(module), prepare_agent=True, report=True, report_aggregate=False
                            )
                        except Exception:
                            pass
                else:
                    self._ensure_jacoco_argline(root_editor)
                    self._ensure_jacoco_plugin_configuration(root_editor, prepare_agent=True, report=True, report_aggregate=True)
            except Exception as e:
                logger.warning(f"Failed to prepare POM for JaCoCo: {e}")

        # 1) Pre-install modules
        try:
            self.install(repo_path, skip_tests=True, ignore_test_failures=True, skip_its=True, skip_docs=True)
        except Exception as e:
            logger.warning(f"Pre-install step failed: {e}")

        # 2) Run tests to collect coverage
        cmd = [
            self._get_base_cmd(repo_path),
            "test",
            "--batch-mode",
            "-U",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
        ]
        if self.target_java_version:
            cmd.extend([
                f"-Dmaven.compiler.source={self.target_java_version}",
                f"-Dmaven.compiler.target={self.target_java_version}"
            ])
        cmd.append("-Dmaven.test.failure.ignore=true")
        if clean:
            cmd.insert(1, "clean")
        try:
            # Sync timeout to 300s to match test() and allow longer integration tests
            result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), env=self._get_execution_env(self.target_java_version), shell=(os.name == "nt"), timeout=300)
            stdout = result.stdout.decode("utf-8")
            stderr = result.stderr.decode("utf-8")
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout.decode("utf-8") if e.stdout else ""
            stderr = (e.stderr.decode("utf-8") if e.stderr else "") + "\n[ERROR] Maven coverage execution timed out after 300 seconds."
            total, passed = self._parse_test_counts(stdout)
            return CoverageResult(
                status=-1,
                stdout=stdout,
                stderr=stderr,
                jacoco_xml_path="",
                coverage_found=False,
                line_coverage_pct=0.0,
                missed_lines=0,
                covered_lines=0,
                total_tests=total,
                passed_tests=passed
            )
        
        # Now find the jacoco.xml report
        metrics = {
            "status": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "jacoco_xml_path": "",
            "coverage_found": False,
            "line_coverage_pct": 0.0,
            "missed_lines": 0,
            "covered_lines": 0,
        }
        
        total_missed = 0
        total_covered = 0
        coverage_found = False

        # Aggregate coverage across all modules in multi-module projects
        for jacoco_xml in repo_path.rglob("jacoco.xml"):
            # Avoid aggregate reports to prevent double-counting
            parts = [p.lower() for p in jacoco_xml.parts]
            if "jacoco-aggregate" in parts:
                continue
            # Also ensure it is in the target directory of a module
            if "target" not in parts or "site" not in parts or "jacoco" not in parts:
                continue
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(jacoco_xml)
                root = tree.getroot()
                for counter in root.findall("counter"):
                    if counter.get("type") == "LINE":
                        total_missed += int(counter.get("missed", 0))
                        total_covered += int(counter.get("covered", 0))
                        coverage_found = True
                        break
            except Exception as e:
                pass
                
        metrics["missed_lines"] = total_missed
        metrics["covered_lines"] = total_covered
        total_lines = total_missed + total_covered
        
        if coverage_found and total_lines > 0:
            metrics["line_coverage_pct"] = (total_covered / total_lines) * 100.0
            metrics["coverage_found"] = True

        total, passed = self._parse_test_counts(stdout)
        metrics["total_tests"] = total
        metrics["passed_tests"] = passed
                
        return CoverageResult(**metrics)

    def install(
        self,
        repo_path: Path,
        skip_tests: bool = False,
        ignore_test_failures: bool = False,
        skip_its: bool = True,
        skip_docs: bool = True,
    ) -> CliResult:
        cmd = [
            self._get_base_cmd(repo_path),
            "install",
            "--batch-mode",
            "-U",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
        ]
        if self.target_java_version:
            cmd.extend([
                f"-Dmaven.compiler.source={self.target_java_version}",
                f"-Dmaven.compiler.target={self.target_java_version}"
            ])
        if skip_tests:
            cmd.append("-DskipTests")
        if ignore_test_failures:
            cmd.append("-Dmaven.test.failure.ignore=true")
        if skip_its:
            cmd.append("-DskipITs")
        if skip_docs:
            cmd.append("-DskipDocs")
        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), env=self._get_execution_env(self.target_java_version), shell=(os.name == "nt"))
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )

    def deps(self, repo_path: Path, output_path: Path) -> CliResult:
        cmd = [
            self._get_base_cmd(repo_path),
            "--batch-mode",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
            "dependency:build-classpath",
            "-Dmdep.includeScope=test",
            f"-Dmdep.outputFile={str(output_path)}",
        ]
        if self.target_java_version:
            cmd.extend([
                f"-Dmaven.compiler.source={self.target_java_version}",
                f"-Dmaven.compiler.target={self.target_java_version}"
            ])

        logger.info(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), env=self._get_execution_env(self.target_java_version), shell=(os.name == "nt"))
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )

    def copy_deps(self, repo_path: Path) -> CliResult:
        cmd = [
            self._get_base_cmd(repo_path),
            "dependency:copy-dependencies",
            "-DincludeScope=runtime",
            "-DoutputDirectory=target/dependencies",
            "--batch-mode",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
        ]

        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), env=self._get_execution_env(self.target_java_version), shell=(os.name == "nt"))
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )
