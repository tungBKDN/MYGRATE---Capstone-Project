import os
from langchain_core.tools import tool

@tool
def write_file(project_path: str, file_path: str, content: str) -> str:
    """
    Writes or overwrites the content of a file.
    All written files are automatically stored under the project's 'artifacts' directory
    to preserve original code and aggregate migrated files.
    """
    try:
        from pathlib import Path
        proj_p = Path(project_path).resolve()
        file_p = Path(file_path)
        
        # Resolve the relative path relative to the project root
        if file_p.is_absolute():
            try:
                rel_path = file_p.relative_to(proj_p)
            except ValueError:
                rel_path = Path(file_p.name)
        else:
            rel_path = file_p
            
        target_path = proj_p / "test" / "artifacts" / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Write to the actual project path so compilation and testing can verify it
        actual_path = proj_p / rel_path
        actual_path.parent.mkdir(parents=True, exist_ok=True)
        with open(actual_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return f"Successfully wrote {len(content)} characters to both {target_path} and {actual_path}."
    except Exception as e:
        return f"Error writing file {file_path}: {str(e)}"


