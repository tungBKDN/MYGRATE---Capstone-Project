import os
import shutil
from pathlib import Path

project_root = Path("D:/capstone_project/MYGRATE---Capstone-Project")
freshbrew_dir = project_root / "freshbrew_data"
prerun_root = project_root / "prerun_architectures"

prerun_root.mkdir(parents=True, exist_ok=True)

print("=== MOVING ARTIFACTS TO /prerun_architectures ===")
moved_count = 0
for cb_dir in freshbrew_dir.iterdir():
    if not cb_dir.is_dir():
        continue
    cb_name = cb_dir.name
    artifacts_dir = cb_dir / "test" / "artifacts"
    if artifacts_dir.exists():
        dest_dir = prerun_root / cb_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"Moving artifacts for {cb_name} to {dest_dir}...")
        for item in artifacts_dir.iterdir():
            if item.is_file():
                shutil.move(str(item), str(dest_dir / item.name))
        
        # Clean up the test folder in codebase
        shutil.rmtree(cb_dir / "test", ignore_errors=True)
        moved_count += 1

print(f"\nSuccessfully moved artifacts for {moved_count} codebases. freshbrew_data is now clean.")
