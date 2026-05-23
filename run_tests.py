import subprocess

with open("test_output.txt", "w") as f:
    result = subprocess.run(["python", "-m", "pytest", "tests/new_dependency_analyzer/test_cantor_analysis.py", "-v", "-s"], capture_output=True, text=True)
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\nSTDERR:\n")
    f.write(result.stderr)
