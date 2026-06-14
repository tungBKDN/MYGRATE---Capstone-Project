import logging
import os
import subprocess
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CliResult(BaseModel):
    status: int
    stdout: str
    stderr: str


class CoverageResult(BaseModel):
    status: int
    stdout: str
    stderr: str
    jacoco_xml_path: str
    coverage_found: bool
    line_coverage_pct: float
    missed_lines: int
    covered_lines: int



class Maven:
    def __init__(self, target_java_version: str):
        self.target_java_version = target_java_version

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
            f"-Dmaven.compiler.source={self.target_java_version}",
            f"-Dmaven.compiler.target={self.target_java_version}",
        ]
        if clean:
            cmd.insert(1, "clean")
        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), shell=(os.name == "nt"))
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )

    def test(self, repo_path: Path, skip_tests: bool = False, clean: bool = False) -> CliResult:
        repo_path = Path(repo_path)  # ensure Path, not str
        cmd = [
            self._get_base_cmd(repo_path),
            "verify",
            "--batch-mode",
            "-U",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
            f"-Dmaven.compiler.source={self.target_java_version}",
            f"-Dmaven.compiler.target={self.target_java_version}",
        ]
        if skip_tests:
            cmd.append("-DskipTests")
        if clean:
            cmd.insert(1, "clean")
        try:
            # Timeout increased to 300s to allow integration tests to run
            result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), shell=(os.name == "nt"), timeout=300)
            return CliResult(
                status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
            )
        except subprocess.TimeoutExpired as e:
            return CliResult(
                status=-1,
                stdout=e.stdout.decode("utf-8") if e.stdout else "",
                stderr=(e.stderr.decode("utf-8") if e.stderr else "") + "\n[ERROR] Maven test execution timed out after 300 seconds. A test might be hanging or stuck in an infinite loop."
            )

    def coverage(self, repo_path: Path, clean: bool = False) -> CoverageResult:
        repo_path = Path(repo_path)  # ensure Path, not str
        cmd = [
            self._get_base_cmd(repo_path),
            "org.jacoco:jacoco-maven-plugin:0.8.12:prepare-agent",
            "test",
            "org.jacoco:jacoco-maven-plugin:0.8.12:report",
            "--batch-mode",
            "-U",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
            f"-Dmaven.compiler.source={self.target_java_version}",
            f"-Dmaven.compiler.target={self.target_java_version}",
            "-Dmaven.test.failure.ignore=true",
        ]
        if clean:
            cmd.insert(1, "clean")
        try:
            result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), shell=(os.name == "nt"), timeout=180)
        except subprocess.TimeoutExpired as e:
            return CoverageResult(
                status=-1,
                stdout=e.stdout.decode("utf-8") if e.stdout else "",
                stderr=(e.stderr.decode("utf-8") if e.stderr else "") + "\n[ERROR] Maven coverage execution timed out after 180 seconds.",
                jacoco_xml_path="",
                coverage_found=False,
                line_coverage_pct=0.0,
                missed_lines=0,
                covered_lines=0
            )
        
        # Now find the jacoco.xml report
        metrics = {
            "status": result.returncode,
            "stdout": result.stdout.decode("utf-8"),
            "stderr": result.stderr.decode("utf-8"),
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
            f"-Dmaven.compiler.source={self.target_java_version}",
            f"-Dmaven.compiler.target={self.target_java_version}",
        ]
        if skip_tests:
            cmd.append("-DskipTests")
        if ignore_test_failures:
            cmd.append("-Dmaven.test.failure.ignore=true")
        if skip_its:
            cmd.append("-DskipITs")
        if skip_docs:
            cmd.append("-DskipDocs")
        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), shell=(os.name == "nt"))
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
            f"-Dmaven.compiler.source={self.target_java_version}",
            f"-Dmaven.compiler.target={self.target_java_version}",
        ]

        logger.info(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), shell=(os.name == "nt"))
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

        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), shell=(os.name == "nt"))
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )
