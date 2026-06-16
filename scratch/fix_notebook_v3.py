import subprocess
import sys
from pathlib import Path

# Run generate_notebook_2.py to regenerate translator_simulation_2.ipynb
notebook_gen_script = Path("generate_notebook_2.py")
if not notebook_gen_script.exists():
    print(f"Error: {notebook_gen_script} not found.")
    sys.exit(1)

print("Regenerating translator_simulation_2.ipynb...")
res = subprocess.run([sys.executable, str(notebook_gen_script)], capture_output=True, text=True)
if res.returncode == 0:
    print("✓ Successfully regenerated translator_simulation_2.ipynb with the new v3 raw compile-feeding loop cell!")
else:
    print(f"Failed to regenerate notebook: {res.stderr}")
    sys.exit(res.returncode)
