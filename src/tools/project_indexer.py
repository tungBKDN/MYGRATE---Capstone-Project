import os
from typing import List, Dict

def index_project_structure(root_path: str, max_depth: int = 3) -> str:
    """
    Creates a condensed summary of the project structure.
    Identifies key files like pom.xml, build.gradle, settings.xml, etc.
    """
    summary = []

    def walk(current_path, depth):
        if depth > max_depth:
            return

        try:
            items = os.listdir(current_path)
        except Exception as e:
            return

        for item in items:
            if item.startswith('.') or item == 'target' or item == 'node_modules' or item == 'venv':
                continue

            full_path = os.path.join(current_path, item)
            rel_path = os.path.relpath(full_path, root_path)

            if os.path.isdir(full_path):
                summary.append(f"{'  ' * depth}📁 {rel_path}/")
                walk(full_path, depth + 1)
            else:
                icon = "📄"
                if item == 'pom.xml': icon = "📦 [Maven]"
                elif item == 'build.gradle': icon = "📦 [Gradle]"
                elif item.endswith('.java'): icon = "☕ [Java]"
                elif item.endswith('.py'): icon = "🐍 [Python]"

                summary.append(f"{'  ' * depth}{icon} {rel_path}")

    walk(root_path, 0)
    return "\n".join(summary)

def find_main_build_file(root_path: str) -> str:
    """
    Finds the primary build file in the project.
    """
    priority = ['pom.xml', 'build.gradle', 'package.json', 'requirements.txt']
    for file in priority:
        path = os.path.join(root_path, file)
        if os.path.exists(path):
            return rel_path if (rel_path := os.path.relpath(path, root_path)) else file
    return None
