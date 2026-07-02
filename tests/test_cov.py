import sys
from pathlib import Path
# Add project root to sys.path
project_root = Path(r"D:\capstone_project\MYGRATE---Capstone-Project")
sys.path.insert(0, str(project_root))
from src.tools.maven.maven_runner import Maven
from src.tools.maven_upgrade_tools import _get_project_properties

def test():
    project_path = project_root / "freshbrew_data" / "spark-jobs-rest-client"
    
    # Tự động detect JDK target gốc của dự án
    props = _get_project_properties(project_path)
    original_jdk = props.get("jdk_target", "")
    print(f"Detected original JDK version: {original_jdk}")
    
    runner = Maven(target_java_version="8")
    
    print("Starting coverage run for:", project_path)
    res = runner.coverage(project_path, clean=True)
    
    print("Status:", res.status)
    print("Coverage found:", res.coverage_found)
    print("Line coverage pct:", res.line_coverage_pct)
    print("Total tests:", res.total_tests)
    print("Passed tests:", res.passed_tests)
    print("Covered lines:", res.covered_lines)
    print("Missed lines:", res.missed_lines)
    
    if res.stdout:
        print("\nStdout (last 50 lines):")
        lines = res.stdout.splitlines()
        for line in lines[-50:]:
            print(line)
            
    if res.coverage_found:
        print("SUCCESS: Coverage was found and parsed!")
    else:
        print("FAILED: Coverage was not found.")
        if res.stderr:
            print("Stderr:", res.stderr)
if __name__ == "__main__":
    test()