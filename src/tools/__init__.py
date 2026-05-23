from .file_system import list_project_structure, read_source_code, get_file_summary
from .project_indexer import index_project_structure, find_main_build_file
from .dependency_analyzer import (
    parse_maven_dependencies,
    list_all_versions,
    get_transitive_dependencies,
    check_java_compatibility,
    get_latest_version,
    detect_transitive_conflicts,
    resolve_best_combination,
    batch_check_java_compatibility,
    get_compatible_versions
)
from .python_dependency_tools import (
    parse_python_dependencies,
    get_latest_pypi_version,
    check_python_compatibility
)
from .visualization_engine import generate_dashboard, generate_cross_matrix

__all__ = [
    "list_project_structure",
    "read_source_code",
    "get_file_summary",
    "index_project_structure",
    "find_main_build_file",
    "parse_maven_dependencies",
    "list_all_versions",
    "get_transitive_dependencies",
    "check_java_compatibility",
    "get_latest_version",
    "detect_transitive_conflicts",
    "resolve_best_combination",
    "batch_check_java_compatibility",
    "get_compatible_versions",
    "parse_python_dependencies",
    "get_latest_pypi_version",
    "check_python_compatibility",
    "generate_dashboard",
    "generate_cross_matrix"
]
