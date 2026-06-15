import subprocess
from pathlib import Path

def debug_mvn():
    project_path = r"D:\capstone_project\MYGRATE---Capstone-Project\freshbrew_data\amazon-kinesis-client"
    # Run maven command: mvn clean test-compile
    cmd = ["mvn", "clean", "test-compile", "--batch-mode", "-U"]
    print(f"Running command: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path, shell=True)
    
    log_file = Path(__file__).parent / "maven_debug_log.txt"
    log_file.write_text(f"Exit code: {res.returncode}\n\nSTDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}", encoding="utf-8")
    print(f"Done. Output saved to {log_file}")

if __name__ == "__main__":
    debug_mvn()
