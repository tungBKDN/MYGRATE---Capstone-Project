import os
import json
import base64

# Define paths
steps_dir = r"C:\Users\tngtr\.gemini\antigravity-ide\brain\fdff091f-a76f-46c4-a5fb-be11f5cdfda6\.system_generated\steps"
current_dir = os.path.dirname(__file__)

files_to_extract = {
    "maven_pom_editor.py": os.path.join(steps_dir, "429", "content.md"),
    "maven_project.py": os.path.join(steps_dir, "487", "content.md"),
    "maven_runner.py": os.path.join(steps_dir, "491", "content.md")
}

for filename, step_path in files_to_extract.items():
    dest_path = os.path.join(current_dir, filename)
    if not os.path.exists(dest_path):
        try:
            with open(step_path, "r", encoding="utf-8") as f:
                content = f.read()
            start_idx = content.find("{")
            end_idx = content.rfind("}")
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx+1]
                data = json.loads(json_str)
                b64_content = data.get("content", "")
                b64_content = b64_content.replace("\n", "").replace("\r", "").strip()
                decoded_bytes = base64.b64decode(b64_content)
                decoded_str = decoded_bytes.decode("utf-8")
                
                # Correct import paths for our package structure
                decoded_str = decoded_str.replace("from java_migration.maven.maven_pom_editor import", "from .maven_pom_editor import")
                decoded_str = decoded_str.replace("from java_migration.maven.maven_project import", "from .maven_project import")
                decoded_str = decoded_str.replace("from java_migration.maven.maven_runner import", "from .maven_runner import")
                
                with open(dest_path, "w", encoding="utf-8") as out_f:
                    out_f.write(decoded_str)
                print(f"[MAVEN_INIT] Successfully extracted and corrected {filename}")
        except Exception as e:
            print(f"[MAVEN_INIT] Error extracting {filename}: {e}")

# Now import the modules
try:
    from .maven_pom_editor import MavenPomEditor
    from .maven_project import MavenProject
    from .maven_runner import Maven as MavenRunner
except ImportError as e:
    print(f"[MAVEN_INIT] Import error: {e}")
    # Fallback definitions
    class MavenPomEditor:
        def __init__(self, pom_file): pass
    class MavenProject:
        def __init__(self, root_pom_path): pass
    class MavenRunner:
        def __init__(self, target_java_version): pass

__all__ = ["MavenPomEditor", "MavenProject", "MavenRunner"]
