import subprocess
import os

repo_path = r"D:\capstone_project\MYGRATE---Capstone-Project\working\rome"
cmd = [
    r"mvn",
    "clean",
    "test",
    "--batch-mode",
    "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn"
]

print("Running command:", " ".join(cmd))
res = subprocess.run(cmd, capture_output=True, cwd=repo_path, shell=True)
print("Return code:", res.returncode)

stdout_decoded = res.stdout.decode("utf-8", errors="ignore")
stderr_decoded = res.stderr.decode("utf-8", errors="ignore")

# Write to log
with open("mvn_scratch.log", "w", encoding="utf-8") as f:
    f.write("=== STDOUT ===\n")
    f.write(stdout_decoded)
    f.write("\n=== STDERR ===\n")
    f.write(stderr_decoded)

print("Saved output to mvn_scratch.log")
