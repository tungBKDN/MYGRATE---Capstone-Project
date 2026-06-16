import json
from pathlib import Path

notebook_path = Path("translator_simulation_2.ipynb")
if not notebook_path.exists():
    print(f"Error: {notebook_path} does not exist!")
    exit(1)

with open(notebook_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Find the cell defining TranslatorAgent_2
found_cell = False
for cell in data.get("cells", []):
    if cell.get("id") == "define-translator-agent-2" or (
        cell.get("cell_type") == "code" and any("class TranslatorAgent_2" in line for line in cell.get("source", []))
    ):
        print(f"Found TranslatorAgent_2 definition cell (id={cell.get('id')})!")
        cell["source"] = [
            "from src.agents.translator_agent_2 import TranslatorAgent_2\n",
            "print(\"TranslatorAgent_2 class imported successfully from src.agents.translator_agent_2!\")\n"
        ]
        found_cell = True
        break

if found_cell:
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    print("Successfully patched translator_simulation_2.ipynb to import TranslatorAgent_2!")
else:
    print("Could not find the target cell in the notebook!")
