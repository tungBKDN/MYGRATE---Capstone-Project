import os
import re
import json
import requests
from typing import List, Dict, Any
from langchain_core.tools import tool
from packaging.specifiers import SpecifierSet
from packaging.version import Version

@tool
def parse_python_dependencies(requirements_path: str) -> str:
    """
    Parses a requirements.txt file to extract python package names and versions.
    Returns a JSON string containing the list of dependencies.
    """
    if not os.path.exists(requirements_path):
        return json.dumps({"error": f"Requirements file not found at {requirements_path}"})
        
    dependencies = []
    try:
        with open(requirements_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Split at specifiers: ==, >=, <=, !=, ~=, >, <
                parts = re.split(r'(==|>=|<=|!=|~=|p>|<)', line)
                name = parts[0].strip()
                # Remove extras like [security]
                name = re.sub(r'\[.*\]', '', name).strip()
                version = "Any"
                if len(parts) > 2:
                    version = "".join(parts[2:]).strip()
                    # Clean up comments in line
                    if " #" in version:
                        version = version.split(" #")[0].strip()
                dependencies.append({"name": name, "version": version})
        return json.dumps({"dependencies": dependencies})
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_latest_pypi_version(package_name: str) -> str:
    """
    Retrieves the latest stable version of a Python package from PyPI.
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("info", {}).get("version", "Unknown")
    except Exception:
        pass
    return "Unknown"

@tool
def check_python_compatibility(package_name: str, version: str, target_python: str) -> str:
    """
    Checks compatibility of a Python package version with a target Python version (e.g. '3.10').
    Returns a JSON compatibility report.
    """
    url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            requires_python = data.get("info", {}).get("requires_python")
            if not requires_python:
                return json.dumps({
                    "package": package_name,
                    "version": version,
                    "requires_python": "Any",
                    "compatible": "Yes"
                })
            
            try:
                spec = SpecifierSet(requires_python)
                target_v = Version(target_python)
                is_compat = target_v in spec
                status = "Yes" if is_compat else "No"
            except Exception:
                status = "Maybe"  # Parsing failed or invalid specifier
                
            return json.dumps({
                "package": package_name,
                "version": version,
                "requires_python": requires_python,
                "compatible": status
            })
    except Exception as e:
        return json.dumps({
            "package": package_name,
            "version": version,
            "error": str(e),
            "compatible": "Maybe"
        })
    return json.dumps({
        "package": package_name,
        "version": version,
        "compatible": "Maybe"
    })
