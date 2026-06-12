import subprocess
import os
from pathlib import Path

repo_path = Path(r"d:\capstone_project\MYGRATE---Capstone-Project\working\sonar-stash")
cmd = ["mvn", "clean", "compile", "-Dmaven.compiler.source=17", "-Dmaven.compiler.target=17"]
result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path), shell=True)

out_file = Path(r"d:\capstone_project\MYGRATE---Capstone-Project\scratch\compile_result.txt")
with open(out_file, "w", encoding="utf-8") as f:
    f.write(f"STATUS: {result.returncode}\n")
    f.write("--- STDOUT ---\n")
    f.write(result.stdout.decode("utf-8", errors="ignore"))
    f.write("\n--- STDERR ---\n")
    f.write(result.stderr.decode("utf-8", errors="ignore"))

print("Done compiling")
