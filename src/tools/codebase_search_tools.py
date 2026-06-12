import re
import json
import tree_sitter
from pathlib import Path
from typing import Any
from src.core.tree_sitter_engine import UniversalASTReader

def find_code_usages(project_path: str, node_type: str, identifier: str) -> list[dict[str, Any]]:
    """Search for specific Java AST nodes (method invocations, class declarations, etc.) 
    matching the given identifier. Enforces strict allowed node types to keep it lean.
    
    Args:
        project_path: Path to the Java project root directory.
        node_type: Fixed list of allowed AST node types (method_invocation, class_declaration, 
                   import_declaration, variable_declarator).
        identifier: The method, class, or variable name to search for.
        
    Returns:
        List of dictionaries with coordinates and code snippets.
    """
    allowed_types = {"method_invocation", "class_declaration", "import_declaration", "variable_declarator"}
    if node_type not in allowed_types:
        raise ValueError(f"Unsupported node_type: {node_type}. Must be one of {allowed_types}")

    # Build Tree-sitter query string
    if node_type == "method_invocation":
        query_str = '(method_invocation name: (identifier) @id) @match'
    elif node_type == "class_declaration":
        query_str = '(class_declaration name: (identifier) @id) @match'
    elif node_type == "variable_declarator":
        query_str = '(variable_declarator name: (identifier) @id) @match'
    elif node_type == "import_declaration":
        query_str = '(import_declaration) @match'
    else:
        return []

    reader = UniversalASTReader()
    results = []
    path = Path(project_path)
    language = reader.languages["java"]
    ts_query = tree_sitter.Query(language, query_str)

    for p in path.rglob('*.java'):
        # Skip hidden files/directories and build output dirs
        if any(part.startswith('.') or part in ('target', '.venv', 'node_modules') for part in p.parts):
            continue

        try:
            content_bytes = p.read_bytes()
            tree = reader.parse(content_bytes, "java")
            
            cursor = tree_sitter.QueryCursor(ts_query)
            for pattern_index, captures in cursor.matches(tree.root_node):
                match_nodes = captures.get("match", [])
                if not match_nodes:
                    continue
                
                # For nodes with an "id" capture, check if identifier matches
                if node_type in ("method_invocation", "class_declaration", "variable_declarator"):
                    id_nodes = captures.get("id", [])
                    if not id_nodes:
                        continue
                    id_node = id_nodes[0]
                    id_text = content_bytes[id_node.start_byte:id_node.end_byte].decode("utf-8", errors="replace")
                    if id_text != identifier:
                        continue
                
                # For import_declaration, filter by identifier substring in Python
                match_node = match_nodes[0]
                node_text = content_bytes[match_node.start_byte:match_node.end_byte].decode("utf-8", errors="replace")
                if node_type == "import_declaration" and identifier not in node_text:
                    continue

                results.append({
                    "file_path": str(p.relative_to(path)),
                    "start_line": match_node.start_point[0] + 1,
                    "start_column": match_node.start_point[1],
                    "end_line": match_node.end_point[0] + 1,
                    "end_column": match_node.end_point[1],
                    "snippet": node_text,
                })
        except Exception:
            # Ignore file parsing/reading errors
            pass

    # Sort results for deterministic output
    results.sort(key=lambda x: (x["file_path"], x["start_line"], x["start_column"]))
    return results


def search_codebase(project_path: str, regex_pattern: str, file_extensions: list[str]) -> list[dict[str, Any]]:
    """Grep/Regex search text content within specified file extensions in the codebase.
    
    Args:
        project_path: Path to the project root directory.
        regex_pattern: Regular expression pattern to search.
        file_extensions: List of file extensions to search (e.g. ['xml', 'properties']).
        
    Returns:
        List of matching instances with file path, line number, content, and match columns.
    """
    exts = {ext.lower().lstrip('.') for ext in file_extensions}
    results = []
    
    try:
        compiled_regex = re.compile(regex_pattern)
    except re.error as e:
        # Return empty list or error info if regex pattern is invalid
        return [{"error": f"Invalid regex pattern: {e}"}]
        
    path = Path(project_path)
    for p in path.rglob('*'):
        if p.is_file():
            # Skip hidden dirs like .git, .venv, target etc.
            if any(part.startswith('.') or part in ('target', '.venv', 'node_modules') for part in p.parts):
                continue
            
            suffix = p.suffix.lower().lstrip('.')
            if suffix in exts:
                try:
                    lines = p.read_text(encoding='utf-8', errors='ignore').splitlines()
                    for idx, line in enumerate(lines, start=1):
                        for match in compiled_regex.finditer(line):
                            results.append({
                                "file_path": str(p.relative_to(path)),
                                "line_number": idx,
                                "line_content": line,
                                "start_column": match.start(),
                                "end_column": match.end(),
                            })
                except Exception:
                    # Ignore reading errors
                    pass
                    
    return results


def get_file_migration_details(project_path: str, file_path: str) -> dict[str, Any]:
    """Read the jdeprscan and mygrate change plan reports from files, and extract 
    specific details and change candidates for the requested file path.
    
    Args:
        project_path: Path to the project root directory.
        file_path: The target file path relative to project root.
        
    Returns:
        Dict containing deprecations and change candidates.
    """
    path = Path(project_path)
    jdeprscan_file = path / "target" / "jdeprscan_report.json"
    if not jdeprscan_file.exists():
        jdeprscan_file = path / "artifacts" / "jdeprscan_report.json"
        
    mygrate_file = path / "target" / "mygrate_report.json"
    if not mygrate_file.exists():
        mygrate_file = path / "artifacts" / "mygrate_report.json"
    
    details = {
        "file_path": file_path,
        "deprecations": [],
        "change_candidates": [],
    }
    
    # Extract project code deprecations from jdeprscan_report
    if jdeprscan_file.exists():
        try:
            with open(jdeprscan_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Find deprecations in project code matching the file path
            b2 = data.get("steps", {}).get("b2_project_scan", {})
            for_removal = b2.get("for_removal", [])
            deprecated = b2.get("deprecated", [])
            
            # Match by class name
            class_name = None
            if file_path.endswith(".java"):
                # Normalize file path separators to match src/main/java format
                normalized_path = file_path.replace("\\", "/")
                parts = normalized_path.split("src/main/java/")
                if len(parts) > 1:
                    class_name = parts[1][:-5].replace("/", ".")
                    
            for item in for_removal + deprecated:
                if class_name and class_name in item:
                    details["deprecations"].append(item)
                elif Path(file_path).name in item:
                    details["deprecations"].append(item)
        except Exception:
            pass
            
    # Extract change candidates from mygrate_report
    if mygrate_file.exists():
        try:
            with open(mygrate_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            candidates = data.get("change_candidates", [])
            for c in candidates:
                c_path = c.get("file_path", "").replace("\\", "/")
                target_path = file_path.replace("\\", "/")
                if c_path == target_path or Path(c_path).name == Path(file_path).name:
                    details["change_candidates"].append(c)
        except Exception:
            pass
            
    return details

