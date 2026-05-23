import os
import re
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Any
from langchain_core.tools import tool

from src.tools.java_dependency_tools import (
    list_all_versions as new_list_all_versions,
    check_java_compatibility as new_check_java_compatibility,
    get_transitive_dependencies as new_get_transitive_dependencies,
    DependencySolver,
    inject_constrained_versions
)

# Helper functions for POM parsing
def resolve_properties(value: str, properties: Dict[str, str]) -> str:
    """Recursively resolves ${...} placeholders in a string."""
    if not value or not isinstance(value, str):
        return value

    for _ in range(5):
        matches = re.findall(r'\$\{([^}]+)\}', value)
        if not matches:
            break
        changed = False
        for prop_name in matches:
            if prop_name in properties:
                value = value.replace(f"${{{prop_name}}}", properties[prop_name])
                changed = True
        if not changed:
            break
    return value

def _parse_pom_xml_content(xml_content: str) -> Dict:
    """Internal helper to parse POM XML content and return structured data."""
    try:
        root = ET.fromstring(xml_content)

        # Handle namespaces robustly
        ns_url = ""
        if root.tag.startswith("{"):
            ns_url = root.tag.split("}")[0][1:]

        ns = {'mvn': ns_url} if ns_url else {}

        def find_text(node, path):
            found = node.find(path, ns)
            return found.text.strip() if found is not None and found.text else None

        # Extract Project Metadata
        p_group = find_text(root, 'mvn:groupId')
        p_artifact = find_text(root, 'mvn:artifactId')
        p_version = find_text(root, 'mvn:version')

        parent = root.find('mvn:parent', ns)
        if parent is not None:
            if not p_group: p_group = find_text(parent, 'mvn:groupId')
            if not p_version: p_version = find_text(parent, 'mvn:version')

        # Extract Properties
        properties = {
            "project.groupId": p_group or "",
            "project.artifactId": p_artifact or "",
            "project.version": p_version or "",
            "pom.groupId": p_group or "",
            "pom.artifactId": p_artifact or "",
            "pom.version": p_version or "",
        }
        props_node = root.find('mvn:properties', ns)
        if props_node is not None:
            for prop in props_node:
                tag = prop.tag.split("}")[-1] if "}" in prop.tag else prop.tag
                if prop.text:
                    properties[tag] = prop.text.strip()

        # Helper to extract dependency info
        def get_dep_info(dep_node):
            g = find_text(dep_node, 'mvn:groupId')
            a = find_text(dep_node, 'mvn:artifactId')
            v = find_text(dep_node, 'mvn:version') or "Managed"
            scope = find_text(dep_node, 'mvn:scope') or "compile"

            g = resolve_properties(g, properties)
            a = resolve_properties(a, properties)
            v = resolve_properties(v, properties)

            return {"groupId": g, "artifactId": a, "version": v, "scope": scope}

        dependencies = []
        deps_node = root.find('mvn:dependencies', ns)
        if deps_node is not None:
            for dep in deps_node.findall('mvn:dependency', ns):
                dependencies.append(get_dep_info(dep))

        managed_dependencies = []
        dm_node = root.find('mvn:dependencyManagement/mvn:dependencies', ns)
        if dm_node is not None:
            for dep in dm_node.findall('mvn:dependency', ns):
                managed_dependencies.append(get_dep_info(dep))

        return {
            "project": {
                "groupId": p_group or "Unknown",
                "artifactId": p_artifact or "Unknown",
                "version": p_version or "Unknown"
            },
            "properties": properties,
            "dependencies": dependencies,
            "managedDependencies": managed_dependencies
        }
    except Exception as e:
        return {"error": str(e)}

def parse_maven_dependencies(pom_path: str) -> str:
    """Parses a Maven pom.xml file to extract dependencies and project metadata."""
    if not os.path.exists(pom_path):
        return json.dumps({"error": f"POM file not found at {pom_path}"})
    try:
        with open(pom_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return json.dumps(_parse_pom_xml_content(content))
    except Exception as e:
        return json.dumps({"error": str(e)})

def list_all_versions(group_id: str, artifact_id: str) -> str:
    """Retrieves the latest 50 versions from Maven Central, numerically sorted."""
    return new_list_all_versions(group_id, artifact_id)

def get_transitive_dependencies(group_id: str, artifact_id: str, version: str) -> str:
    """Uses deps.dev API to retrieve resolved dependencies."""
    return new_get_transitive_dependencies(group_id, artifact_id, version)

def check_java_compatibility(group_id: str, artifact_id: str, version: str, target_java: str = "17") -> str:
    """Quets JAR from Maven to check compatibility with target JDK."""
    res = new_check_java_compatibility(group_id, artifact_id, version, target_java)
    status = res["analysis"]["compatibility_status"]
    
    is_compatible = "Maybe"
    if status == "Yes":
        is_compatible = "Yes"
    elif status == "No":
        is_compatible = "No"
    elif status == "Warning":
        is_compatible = "Maybe"
        
    return json.dumps({
        "is_compatible": is_compatible,
        "dependency": f"{group_id}:{artifact_id}",
        "version": version,
        "signals": res["signals"]
    })

def get_latest_version(group_id: str, artifact_id: str) -> str:
    """Gets the latest version of a Maven library."""
    v_json = new_list_all_versions(group_id, artifact_id)
    try:
        data = json.loads(v_json)
        versions = data.get("versions", [])
        if versions:
            return versions[0]
    except Exception:
        pass
    return "Unknown"

def detect_transitive_conflicts(dependencies: List[Dict[str, Any]]) -> str:
    """Detects version conflicts in transitive dependencies."""
    requested = {}
    for dep in dependencies:
        g = dep.get("groupId") or dep.get("group_id")
        a = dep.get("artifactId") or dep.get("artifact_id")
        v = dep.get("version")
        if not g or not a or not v:
            continue
        key = (g, a)
        if key not in requested:
            requested[key] = set()
        requested[key].add(v)
        
        # Get transitive dependencies
        trans_json = new_get_transitive_dependencies(g, a, v)
        try:
            trans_list = json.loads(trans_json)
            for t in trans_list:
                tg = t.get("groupId")
                ta = t.get("artifactId")
                tv = t.get("version")
                if tg and ta and tv and tv != "Managed":
                    tkey = (tg, ta)
                    if tkey not in requested:
                        requested[tkey] = set()
                    requested[tkey].add(tv)
        except Exception:
            pass

    conflicts = []
    for (g, a), versions in requested.items():
        if len(versions) > 1:
            conflicts.append({
                "groupId": g,
                "artifactId": a,
                "versions": list(versions)
            })
            
    return json.dumps({"conflicts": conflicts})

def resolve_best_combination(dependencies: List[Dict[str, Any]], target_java: str = "17") -> str:
    """Resolves the best version combination of Java dependencies without conflict."""
    solver = DependencySolver(target_java=target_java)
    for dep in dependencies:
        g = dep.get("groupId") or dep.get("group_id")
        a = dep.get("artifactId") or dep.get("artifact_id")
        if g and a:
            solver.add_library(g, a, max_versions=5)
            
    inject_constrained_versions(solver)
    solver.solve()
    
    if solver.solutions:
        best = solver.solutions[0]
        recommended = []
        for (g, a), v in best.items():
            recommended.append({"groupId": g, "artifactId": a, "version": v})
        return json.dumps({"recommended_combination": recommended})
    else:
        return json.dumps({"error": "No compatible versions found"})

def get_compatible_versions(group_id: str, artifact_id: str, target_java: str = "17") -> str:
    """Retrieves all versions of a library compatible with target Java version."""
    v_json = list_all_versions(group_id, artifact_id)
    try:
        data = json.loads(v_json)
        versions = data.get("versions", [])
        compatible = []
        for v in versions[:15]:
            comp_str = check_java_compatibility(group_id, artifact_id, v, target_java)
            comp = json.loads(comp_str)
            if comp.get("is_compatible") in ["Yes", "Maybe"]:
                compatible.append(v)
        return json.dumps({"compatible_versions": compatible})
    except Exception as e:
        return json.dumps({"error": str(e)})

def batch_check_java_compatibility(group_id: str, artifact_id: str, versions: List[str], target_java: str = "17") -> str:
    """Checks compatibility for multiple versions of a Java library at once."""
    results = []
    for v in versions:
        res_str = check_java_compatibility(group_id, artifact_id, v, target_java)
        results.append(json.loads(res_str))
    return json.dumps(results)
