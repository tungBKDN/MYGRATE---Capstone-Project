import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.tools.maven import MavenRunner

runner = MavenRunner(target_java_version="")
repo_path = Path(r"D:\capstone_project\MYGRATE---Capstone-Project\working\default\log4j2-elasticsearch")
print(f"Running coverage on {repo_path}...")
res = runner.coverage(repo_path, clean=True)

print("----- STATUS -----")
print(res.status)
print("----- TOTAL TESTS -----")
print(res.total_tests)
print("----- PASSED TESTS -----")
print(res.passed_tests)
print("----- COVERAGE FOUND -----")
print(res.coverage_found)
print("----- LINE COVERAGE % -----")
print(res.line_coverage_pct)
print("----- STDERR (LAST 50 LINES) -----")
print("\n".join(res.stderr.splitlines()[-50:]))
print("----- STDOUT (LAST 50 LINES) -----")
print("\n".join(res.stdout.splitlines()[-50:]))
