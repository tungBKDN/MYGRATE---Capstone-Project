import os
from typing import List, Optional
from langchain_core.tools import tool

@tool
def list_project_structure(root_path: str, max_depth: int = 3) -> str:
    """
    Returns a visual tree representation of the project structure.
    Useful for understanding the organization of the codebase.
    """
    output = []
    
    def walk_dir(path: str, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            output.append(f"{prefix}...")
            return

        try:
            items = sorted(os.listdir(path))
        except Exception as e:
            output.append(f"{prefix}[Error reading {os.path.basename(path)}: {e}]")
            return

        # Filter out hidden files/folders
        items = [i for i in items if not i.startswith('.')]

        for i, item in enumerate(items):
            item_path = os.path.join(path, item)
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            
            output.append(f"{prefix}{connector}{item}")
            
            if os.path.isdir(item_path):
                new_prefix = prefix + ("    " if is_last else "│   ")
                walk_dir(item_path, new_prefix, depth + 1)

    output.append(root_path)
    walk_dir(root_path)
    return "\n".join(output)

@tool
def read_source_code(file_path: str) -> str:
    """
    Reads the full content of a source file.
    Use this when you need to analyze the actual implementation details.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return f"--- File: {file_path} ---\n{content}"
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

@tool
def get_file_summary(file_path: str) -> str:
    """
    Returns basic metadata about a file (size, line count).
    """
    try:
        stats = os.stat(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return f"File: {file_path}\nSize: {stats.st_size} bytes\nLines: {len(lines)}"
    except Exception as e:
        return f"Error getting summary for {file_path}: {str(e)}"


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
            
        target_path = proj_p / "artifacts" / rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {target_path}."
    except Exception as e:
        return f"Error writing file {file_path}: {str(e)}"


