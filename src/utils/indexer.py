import os
from typing import List, Dict

class ProjectIndexer:
    """
    Utility to crawl a project directory and identify source files.
    """
    
    SUPPORTED_EXTENSIONS = {
        ".py": "python",
        ".java": "java"
    }

    def __init__(self, project_path: str):
        self.project_path = project_path

    def get_source_files(self) -> List[Dict[str, str]]:
        """
        Walks through the project path and returns a list of source files with their language.
        """
        source_files = []
        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden directories like .git
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    full_path = os.path.join(root, file)
                    source_files.append({
                        "path": os.path.relpath(full_path, self.project_path),
                        "abs_path": full_path,
                        "language": self.SUPPORTED_EXTENSIONS[ext]
                    })
        return source_files
