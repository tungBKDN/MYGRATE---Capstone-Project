import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to python path to import src modules
sys.path.append(str(Path(__file__).resolve().parent))

from src.tools.maven_upgrade_tools import index_java_project, run_upgrade_pipeline

def process_project(project_path: Path, target_java: str):
    import shutil
    project_root = Path(__file__).resolve().parent
    prerun_dir = project_root / "prerun_architectures" / project_path.name
    report_path = prerun_dir / "upgrade_report.json"

    if report_path.exists():
        print(f"\n-> [SKIP] Upgrade report already exists for project: '{project_path.name}'. Skipping.")
        return

    print(f"\n=== [PRE-RUN] Starting Pre-upgrade Analysis for: {project_path.name} ===")
    print(f"1. Scanning project structure and dependencies...")
    scan_res = index_java_project(str(project_path))
    if scan_res.get("status") != "ok":
        print(f"   [Error] Scanning project: {scan_res.get('message')}")
        return

    dependencies = scan_res.get("dependencies", [])
    project_type = scan_res.get("project_type", "java")
    print(f"   Found {len(dependencies)} dependencies. Project type: {project_type}")

    print(f"2. Running full 7-step upgrade pipeline (JDK {target_java})...")
    upgrade_report = run_upgrade_pipeline(
        dependencies,
        target_java=target_java,
        logger=lambda msg: print(f"   {msg}")
    )

    # Save to prerun_architectures folder
    prerun_dir.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(upgrade_report, f, ensure_ascii=False, indent=2, default=str)
        
    # Copy any generated scan reports from test/artifacts to prerun_dir, then clean up test/
    local_artifacts_dir = project_path / "test" / "artifacts"
    if local_artifacts_dir.exists():
        for file_path in local_artifacts_dir.iterdir():
            if file_path.is_file():
                shutil.copy2(file_path, prerun_dir / file_path.name)
        shutil.rmtree(project_path / "test", ignore_errors=True)
        
    print(f"   Saved upgrade report and scanner reports to: {prerun_dir}")
    print(f"=== [PRE-RUN] Pre-upgrade Analysis Completed for {project_path.name} ===")


def main():
    project_root = Path(__file__).resolve().parent
    default_freshbrew = project_root / "freshbrew_data"

    parser = argparse.ArgumentParser(description="Pre-calculate MYGRATE upgrade analysis reports to save time.")
    parser.add_argument("--path", type=str, default=str(default_freshbrew), help="Path to the Java project directory or batch folder (default: freshbrew_data)")
    parser.add_argument("--target-java", type=str, default="17", help="Target Java version (default: 17)")
    args = parser.parse_args()

    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Path '{target_path}' does not exist.")
        sys.exit(1)

    is_single = (target_path / "pom.xml").exists()
    
    if is_single:
        process_project(target_path, args.target_java)
    else:
        # Batch folder mode
        print(f"=== [BATCH PRE-RUN] Scanning subprojects in '{target_path.name}' ===")
        subdirs = sorted([d for d in target_path.iterdir() if d.is_dir()])
        valid_subdirs = [d for d in subdirs if (d / "pom.xml").exists()]
        
        if not valid_subdirs:
            print(f"No direct subprojects containing pom.xml found in '{target_path}'.")
            sys.exit(0)
            
        print(f"Found {len(valid_subdirs)} Maven projects to process.")
        import concurrent.futures
        
        def run_task(sub_path):
            try:
                process_project(sub_path, args.target_java)
                return sub_path.name, "SUCCESS"
            except Exception as e:
                return sub_path.name, f"ERROR: {e}"
        
        print(f"Starting parallel execution with 10 workers...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_project = {executor.submit(run_task, sub_path): sub_path for sub_path in valid_subdirs}
            for idx, future in enumerate(concurrent.futures.as_completed(future_to_project), 1):
                project_name = future_to_project[future].name
                try:
                    name, status = future.result()
                    print(f"[{idx}/{len(valid_subdirs)}] Finished: {name} -> {status}")
                except Exception as exc:
                    print(f"[{idx}/{len(valid_subdirs)}] Project {project_name} generated an exception: {exc}")
            
        print("\n=== [BATCH PRE-RUN] Finished processing all projects ===")

if __name__ == "__main__":
    main()
