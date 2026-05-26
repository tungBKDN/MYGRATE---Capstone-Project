import json
import os
from pathlib import Path
from typing import Dict, List

from src.utils.indexer import ProjectIndexer


def _collect_manifest_files(project_root: Path) -> List[Dict[str, str]]:
    manifest_names = {
        "pom.xml": "maven",
        "build.gradle": "gradle",
        "build.gradle.kts": "gradle",
        "settings.gradle": "gradle",
        "settings.gradle.kts": "gradle",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "setup.py": "python",
    }

    manifests: List[Dict[str, str]] = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for filename in files:
            manifest_type = manifest_names.get(filename)
            if manifest_type:
                full_path = Path(root) / filename
                manifests.append(
                    {
                        "path": str(full_path.relative_to(project_root)),
                        "abs_path": str(full_path.resolve()),
                        "type": manifest_type,
                    }
                )
    manifests.sort(key=lambda item: item["path"])
    return manifests


def _collect_notebooks(project_root: Path) -> List[str]:
    notebooks: List[str] = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for filename in files:
            if filename.endswith('.ipynb'):
                full_path = Path(root) / filename
                notebooks.append(str(full_path.relative_to(project_root)))
    return sorted(notebooks)


def index_codebase(project_path: str) -> str:
    """Index a codebase and classify it as Java or Python."""
    project_root = Path(project_path).expanduser()
    if not project_root.is_absolute():
        project_root = project_root.resolve()

    if not project_root.exists():
        return json.dumps(
            {
                "error": f"Project path not found: {project_root}",
                "project_path": str(project_root),
            },
            ensure_ascii=False,
        )

    indexer = ProjectIndexer(str(project_root))
    source_files = indexer.get_source_files()
    language_counts: Dict[str, int] = {"java": 0, "python": 0, "other": 0}

    for file_info in source_files:
        language = file_info.get("language", "other")
        language_counts[language] = language_counts.get(language, 0) + 1

    project_type = "unknown"
    if language_counts["java"] > language_counts["python"] and language_counts["java"] > 0:
        project_type = "java"
    elif language_counts["python"] > language_counts["java"] and language_counts["python"] > 0:
        project_type = "python"
    elif language_counts["java"] > 0 and language_counts["python"] > 0:
        project_type = "mixed"

    manifests = _collect_manifest_files(project_root)
    notebooks = _collect_notebooks(project_root)

    payload = {
        "project_path": str(project_root),
        "project_type": project_type,
        "language_counts": language_counts,
        "source_files": source_files,
        "manifest_files": manifests,
        "notebooks": notebooks,
        "source_file_count": len(source_files),
        "manifest_count": len(manifests),
        "notebook_count": len(notebooks),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)