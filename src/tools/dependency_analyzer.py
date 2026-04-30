import os
import xml.etree.ElementTree as ET
import requests
import re
import json
from typing import List, Dict

def version_key(v: str):
    """Helper to sort versions numerically. Handles 4.11, 4.13.2-beta, etc."""
    parts = re.split(r'[-.]', str(v))
    # Convert numeric parts to padded strings to allow safe comparison with letters
    return [part.zfill(8) if part.isdigit() else part for part in parts]

def get_latest_version(group_id: str, artifact_id: str) -> str:
    """Fetches the latest stable version of a library from Maven Central."""
    url = f"https://search.maven.org/solrsearch/select?q=g:%22{group_id}%22+AND+a:%22{artifact_id}%22&rows=1&wt=json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            docs = data.get('response', {}).get('docs', [])
            if docs:
                return docs[0].get('latestVersion', 'Unknown')
    except: pass
    return "Unknown"

def parse_maven_dependencies(pom_path: str) -> str:
    """Parses a Maven pom.xml file to extract dependencies and project metadata."""
    if not os.path.exists(pom_path):
        return json.dumps({"error": f"POM file not found at {pom_path}"})
    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
        ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}
        
        project_group_id = root.find('mvn:groupId', ns)
        project_artifact_id = root.find('mvn:artifactId', ns)
        if project_group_id is None:
            parent = root.find('mvn:parent', ns)
            if parent is not None:
                project_group_id = parent.find('mvn:groupId', ns)
        
        p_group = project_group_id.text if project_group_id is not None else "Unknown"
        p_artifact = project_artifact_id.text if project_artifact_id is not None else "Unknown"

        properties = {}
        props_node = root.find('mvn:properties', ns)
        if props_node is not None:
            for prop in props_node:
                tag = prop.tag.replace('{http://maven.apache.org/POM/4.0.0}', '')
                properties[tag] = prop.text

        dependencies = []
        deps_node = root.find('mvn:dependencies', ns)
        if deps_node is not None:
            for dep in deps_node.findall('mvn:dependency', ns):
                g_node = dep.find('mvn:groupId', ns)
                a_node = dep.find('mvn:artifactId', ns)
                v_node = dep.find('mvn:version', ns)
                if g_node is not None and a_node is not None:
                    g = g_node.text.strip()
                    a = a_node.text.strip()
                    v = v_node.text.strip() if v_node is not None else "Managed"
                    if v.startswith("${") and v.endswith("}"):
                        v = properties.get(v[2:-1], v)
                    dependencies.append({"groupId": g, "artifactId": a, "version": v})
        
        return json.dumps({
            "project": {"groupId": p_group, "artifactId": p_artifact},
            "dependencies": dependencies
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def list_all_versions(group_id: str, artifact_id: str) -> str:
    """Retrieves all versions from Maven Central, numerically sorted."""
    url = f"https://search.maven.org/solrsearch/select?q=g:%22{group_id}%22+AND+a:%22{artifact_id}%22&core=gav&rows=1000&wt=json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            docs = response.json().get('response', {}).get('docs', [])
            if not docs: return json.dumps({"error": f"No versions found for {group_id}:{artifact_id}"})
            versions = [doc['v'] for doc in docs]
            versions.sort(key=version_key, reverse=True)
            return json.dumps({"versions": versions})
    except Exception as e:
        return json.dumps({"error": str(e)})
    return json.dumps({"error": "Lookup failed."})

def get_transitive_dependencies(group_id: str, artifact_id: str, version: str) -> str:
    """Fetches dependencies of a specific library from its remote POM."""
    g_path = group_id.replace('.', '/')
    url = f"https://repo1.maven.org/maven2/{g_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
    deps = []
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            content = response.text
            dep_pattern = re.compile(r'<dependency>(.*?)</dependency>', re.DOTALL)
            for dep_block in dep_pattern.findall(content):
                g = re.search(r'<groupId>(.*?)</groupId>', dep_block)
                a = re.search(r'<artifactId>(.*?)</artifactId>', dep_block)
                v = re.search(r'<version>(.*?)</version>', dep_block)
                if g and a:
                    deps.append({
                        "groupId": g.group(1).strip(),
                        "artifactId": a.group(1).strip(),
                        "version": v.group(1).strip() if v else "Managed"
                    })
        return json.dumps(deps)
    except: return json.dumps([])

def check_java_compatibility(group_id: str, artifact_id: str, version: str, target_java: str = "17") -> str:
    """Checks compatibility with heuristics for missing metadata."""
    g_path = group_id.replace('.', '/')
    pom_url = f"https://repo1.maven.org/maven2/{g_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
    target_jdk = "Unknown"
    try:
        response = requests.get(pom_url, timeout=10)
        if response.status_code == 200:
            content = response.text
            tags = ['maven.compiler.target', 'maven.compiler.release', 'java.version', 'jdk.version', 'target.jdk']
            for tag in tags:
                match = re.search(f'<{tag}>(.*?)</{tag}>', content)
                if match:
                    val = match.group(1).strip()
                    if not val.startswith("${"):
                        target_jdk = val
                        break
            if target_jdk == "Unknown":
                v_str = str(version)
                if "1.7." in v_str or "1.6." in v_str: target_jdk = "1.6"
                elif "1.8." in v_str: target_jdk = "1.8"
    except: pass

    is_compatible = "Maybe"
    def norm(v):
        if not v or v == "Unknown": return None
        v_s = str(v)
        v_s = v_s.split('.')[-1] if '.' in v_s and v_s.startswith('1.') else v_s
        try: return int(re.search(r'\d+', v_s).group())
        except: return None

    nt = norm(target_java)
    nlt = norm(target_jdk)
    if nlt and nt:
        is_compatible = "No" if nlt > nt else "Yes"
    elif nt and nt >= 8:
        is_compatible = "Yes (Assumed)"

    verification_url = f"https://search.maven.org/artifact/{group_id}/{artifact_id}/{version}/jar"

    return json.dumps({
        "dependency": f"{group_id}:{artifact_id}",
        "version": version,
        "detected_jdk": target_jdk,
        "is_compatible": is_compatible,
        "verification_url": verification_url
    })

def parse_python_dependencies(req_path: str) -> str:
    """Parses requirements.txt."""
    if not os.path.exists(req_path): return json.dumps({"error": "File not found"})
    deps = []
    try:
        with open(req_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                parts = re.split(r'[=<>!~]', line)
                name = parts[0].strip()
                v = line[len(name):].strip().lstrip('=<>!~') if len(parts) > 1 else "LATEST"
                deps.append({"name": name, "version": v})
        return json.dumps(deps)
    except Exception as e: return json.dumps({"error": str(e)})

def get_latest_pypi_version(package_name: str) -> str:
    """Fetches latest PyPI version."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get('info', {}).get('version', 'Unknown')
    except: pass
    return "Unknown"

def check_python_compatibility(package_name: str, version: str, target_python: str = "3.11") -> str:
    """Checks Python compatibility."""
    url = f"https://pypi.org/pypi/{package_name}/{version}/json"
    latest = get_latest_pypi_version(package_name)
    req_py = "Unknown"
    is_comp = "Maybe"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            req_py = response.json().get('info', {}).get('requires_python', 'Unknown')
            is_comp = "Yes"
    except: pass
    return json.dumps({
        "dependency": package_name,
        "version": version,
        "latest": latest,
        "requires_python": req_py,
        "is_compatible": is_comp
    })
