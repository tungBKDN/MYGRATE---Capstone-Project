import subprocess
import os

jar = r"D:\capstone_project\MYGRATE---Capstone-Project\temp_jars\commons-io-2.22.0.jar"
stub = "MigrationStub.java"
with open(stub, "w") as f:
    f.write("public class MigrationStub { public static void main(String[] args) {} }")

if os.path.exists(jar):
    res = subprocess.run(["javac", "-cp", jar, "--release", "17", stub], capture_output=True, text=True)
    print("EXIT CODE:", res.returncode)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
else:
    print("JAR NOT FOUND")
