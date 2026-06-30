import os
import shutil
import subprocess
import sys
from pathlib import Path

project_root = Path("D:/capstone_project/MYGRATE---Capstone-Project")
freshbrew_dir = project_root / "freshbrew_data"
working_dir = project_root / "working"

# 1. Restore from working copies back to freshbrew_data
print("=== RESTORING FROM WORKING COPIES ===")
for model_dir in working_dir.iterdir():
    if not model_dir.is_dir() or model_dir.name in ("sonar-stash", "temp_jars", "runtime_test_jars"):
        continue
    for cb_dir in model_dir.iterdir():
        if not cb_dir.is_dir():
            continue
        cb_name = cb_dir.name
        src_artifacts = cb_dir / "test" / "artifacts"
        if src_artifacts.exists():
            dest_artifacts = freshbrew_dir / cb_name / "test" / "artifacts"
            dest_artifacts.mkdir(parents=True, exist_ok=True)
            print(f"-> Restoring artifacts for {cb_name} from {model_dir.name} to {dest_artifacts}")
            shutil.copytree(src_artifacts, dest_artifacts, dirs_exist_ok=True)

# 2. Run pre_run_upgrade_analysis.py to regenerate missing ones
print("\n=== REGENERATING MISSING REPORTS ===")
python_exe = sys.executable
# Find venv python if possible
for venv_name in (".venv", "venv"):
    venv_py = project_root / venv_name / "Scripts" / "python.exe"
    if venv_py.exists():
        python_exe = str(venv_py)
        break

cmd = [python_exe, "pre_run_upgrade_analysis.py"]
print(f"Running command: {' '.join(cmd)}")
subprocess.run(cmd, cwd=str(project_root))
print("\n=== DONE RESTORING AND REGENERATING ===")
