import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.tools.maven.maven_pom_editor import MavenPomEditor
from src.tools.maven.maven_project import MavenProject

# Copy freshbrew_data/sonar-stash/pom.xml to working/sonar-stash/pom.xml
original_pom = PROJECT_ROOT / "freshbrew_data" / "sonar-stash" / "pom.xml"
working_dir = PROJECT_ROOT / "working" / "sonar-stash"
working_dir.mkdir(parents=True, exist_ok=True)
working_pom = working_dir / "pom.xml"

import shutil
shutil.copy2(original_pom, working_pom)
print(f"Copied {original_pom} to {working_pom}")

editor = MavenPomEditor(str(working_pom))
# Try to ensure properties and check formatting
editor.ensure_property("maven.compiler.source", "17")
editor.ensure_property("maven.compiler.target", "17")
editor.ensure_property("jdk.version", "17")

print("Updated properties in working pom.xml.")
# Print properties block
with open(working_pom, "r", encoding="utf-8") as f:
    lines = f.readlines()
    for idx, line in enumerate(lines[:65]):
        print(f"{idx+1:03d}: {line}", end="")
