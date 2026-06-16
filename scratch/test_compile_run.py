import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

load_dotenv()

from src.tools.maven import MavenRunner

print("Compiling all sources and test sources under JDK 17...")
PROJECT_PATH = Path("working/sonar-stash").resolve()
runner = MavenRunner(target_java_version="17")

# Running test compile (using test method with skip_tests=True, which compiles tests but skips running them)
res = runner.test(PROJECT_PATH, skip_tests=True, clean=True)
print(f"Test Compile exit code: {res.status}")
print("--- STDOUT ---")
print(res.stdout)
print("--- STDERR ---")
print(res.stderr)
