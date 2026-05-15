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

def resolve_properties(value: str, properties: Dict[str, str]) -> str:
    """Recursively resolves ${...} placeholders in a string."""
    if not value or not isinstance(value, str):
        return value
    
    # Limit recursion to prevent infinite loops from circular properties
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

def parse_maven_dependencies(pom_path: str) -> str:
    """Parses a Maven pom.xml file to extract dependencies and project metadata."""
    if not os.path.exists(pom_path):
        return json.dumps({"error": f"POM file not found at {pom_path}"})
    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
        
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
            
            # Resolve properties
            g = resolve_properties(g, properties)
            a = resolve_properties(a, properties)
            v = resolve_properties(v, properties)
            
            return {"groupId": g, "artifactId": a, "version": v, "scope": scope}

        dependencies = []
        
        # 1. Direct Dependencies
        deps_node = root.find('mvn:dependencies', ns)
        if deps_node is not None:
            for dep in deps_node.findall('mvn:dependency', ns):
                dependencies.append(get_dep_info(dep))
        
        # 2. Dependency Management (BOMs or managed versions)
        managed_dependencies = []
        dm_node = root.find('mvn:dependencyManagement/mvn:dependencies', ns)
        if dm_node is not None:
            for dep in dm_node.findall('mvn:dependency', ns):
                managed_dependencies.append(get_dep_info(dep))

        return json.dumps({
            "project": {
                "groupId": p_group or "Unknown", 
                "artifactId": p_artifact or "Unknown",
                "version": p_version or "Unknown"
            },
            "properties": properties,
            "dependencies": dependencies,
            "managedDependencies": managed_dependencies
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def list_all_versions(group_id: str, artifact_id: str) -> str:
    """Retrieves the latest 50 versions from Maven Central, numerically sorted."""
    url = f"https://search.maven.org/solrsearch/select?q=g:%22{group_id}%22+AND+a:%22{artifact_id}%22&core=gav&rows=50&wt=json"
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
            # Using a more robust regex to handle namespaces and whitespace
            dep_pattern = re.compile(r'<dependency>(.*?)</dependency>', re.DOTALL)
            for dep_block in dep_pattern.findall(content):
                g_match = re.search(r'<groupId>(.*?)</groupId>', dep_block)
                a_match = re.search(r'<artifactId>(.*?)</artifactId>', dep_block)
                v_match = re.search(r'<version>(.*?)</version>', dep_block)
                if g_match and a_match:
                    deps.append({
                        "groupId": g_match.group(1).strip(),
                        "artifactId": a_match.group(1).strip(),
                        "version": v_match.group(1).strip() if v_match else "Managed"
                    })
        return json.dumps(deps)
    except: return json.dumps([])

def check_java_compatibility(group_id: str, artifact_id: str, version: str, target_java: str = "17") -> str:
    """Checks compatibility with heuristics for missing metadata, including parent POM chasing."""
    
    def find_jdk_in_content(xml_content):
        # 1. Check common properties tags
        tags = [
            'maven.compiler.target', 'maven.compiler.release', 'maven.compiler.source',
            'java.version', 'jdk.version', 'target.jdk', 'compiler.target',
            'project.build.targetJdk', 'maven.compile.target'
        ]
        for tag in tags:
            match = re.search(f'<{tag}>(.*?)</{tag}>', xml_content)
            if match:
                val = match.group(1).strip()
                if val and not val.startswith("${"): return val
        
        # 2. Deep scan maven-compiler-plugin configuration
        plugin_match = re.search(r'<artifactId>maven-compiler-plugin</artifactId>.*?<configuration>(.*?)</configuration>', xml_content, re.DOTALL)
        if plugin_match:
            config_content = plugin_match.group(1)
            for subtag in ['target', 'release', 'source']:
                sub_match = re.search(f'<{subtag}>(.*?)</{subtag}>', config_content)
                if sub_match:
                    val = sub_match.group(1).strip()
                    if val and not val.startswith("${"): return val
        return None

    target_jdk = "Unknown"
    current_g, current_a, current_v = group_id, artifact_id, version
    
    # Try up to 5 levels of parents to find the JDK
    for depth in range(6):
        g_path = current_g.replace('.', '/')
        pom_url = f"https://repo1.maven.org/maven2/{g_path}/{current_a}/{current_v}/{current_a}-{current_v}.pom"
        try:
            response = requests.get(pom_url, timeout=10)
            if response.status_code != 200:
                break
            
            content = response.text
            found = find_jdk_in_content(content)
            if found:
                target_jdk = found
                break
            
            # If not found in current POM, look for <parent>
            parent_match = re.search(r'<parent>(.*?)</parent>', content, re.DOTALL)
            if parent_match:
                p_content = parent_match.group(1)
                pg = re.search(r'<groupId>(.*?)</groupId>', p_content)
                pa = re.search(r'<artifactId>(.*?)</artifactId>', p_content)
                pv = re.search(r'<version>(.*?)</version>', p_content)
                if pg and pa and pv:
                    current_g = pg.group(1).strip()
                    current_a = pa.group(1).strip()
                    current_v = pv.group(1).strip()
                else:
                    break
            else:
                break
        except:
            break

    # Heuristics based on version patterns if still unknown
    if target_jdk == "Unknown":
        v_str = str(version)
        if group_id == "org.springframework.boot":
            if v_str.startswith("3."): target_jdk = "17"
            elif v_str.startswith("2."): target_jdk = "8"
        elif "1.7." in v_str or "1.6." in v_str: target_jdk = "1.6"
        elif "1.8." in v_str: target_jdk = "1.8"

    # Compatibility check logic
    is_compatible = "Maybe"
    def norm(v):
        if not v or v == "Unknown": return None
        v_s = str(v)
        # Normalize 1.8 -> 8, etc.
        v_s = v_s.split('.')[-1] if '.' in v_s and v_s.startswith('1.') else v_s
        try:
            m = re.search(r'\d+', v_s)
            return int(m.group()) if m else None
        except:
            return None

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

def detect_transitive_conflicts(dependencies: List[Dict[str, str]]) -> str:
    """
    Analyzes a list of dependencies for potential transitive version conflicts.
    Input: [{"groupId": "...", "artifactId": "...", "version": "..."}, ...]
    """
    all_transitive_deps = {} # (g, a) -> {version -> [requested_by]}
    
    for dep in dependencies:
        g, a, v = dep.get('groupId'), dep.get('artifactId'), dep.get('version')
        if not g or not a or v == "Managed": continue
        
        # Get immediate transitive deps of this dependency
        trans_json = get_transitive_dependencies(g, a, v)
        trans_deps = json.loads(trans_json)
        
        for t_dep in trans_deps:
            tg, ta, tv = t_dep.get('groupId'), t_dep.get('artifactId'), t_dep.get('version')
            key = (tg, ta)
            if key not in all_transitive_deps:
                all_transitive_deps[key] = {}
            if tv not in all_transitive_deps[key]:
                all_transitive_deps[key][tv] = []
            all_transitive_deps[key][tv].append(f"{g}:{a} ({v})")
            
    conflicts = []
    for (g, a), versions in all_transitive_deps.items():
        if len(versions) > 1:
            conflicts.append({
                "dependency": f"{g}:{a}",
                "requested_versions": versions
            })
            
    return json.dumps({
        "conflicts": conflicts,
        "summary": f"Found {len(conflicts)} potential conflicts."
    })

def batch_check_java_compatibility(group_id: str, artifact_id: str, versions: List[str], target_java: str = "17") -> str:
    """Checks compatibility for multiple versions of a library in one call to save tokens."""
    results = []
    for v in versions:
        res = check_java_compatibility(group_id, artifact_id, v, target_java)
        results.append(json.loads(res))
    return json.dumps(results)

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

def get_compatible_versions(group_id: str, artifact_id: str, target_java: str = "17", max_check: int = 10) -> str:
    """
    Finds a list of versions for a library that are compatible with the target JDK.
    Checks the latest 'max_check' versions.
    """
    v_json = list_all_versions(group_id, artifact_id)
    v_data = json.loads(v_json)
    if "error" in v_data: return v_json
    
    versions = v_data.get("versions", [])[:max_check]
    compatible_versions = []
    
    for v in versions:
        comp_json = check_java_compatibility(group_id, artifact_id, v, target_java)
        comp_data = json.loads(comp_json)
        if comp_data.get("is_compatible") in ["Yes", "Yes (Assumed)", "Maybe"]:
            compatible_versions.append({
                "version": v,
                "detected_jdk": comp_data.get("detected_jdk"),
                "status": comp_data.get("is_compatible")
            })
            
    return json.dumps({
        "group_id": group_id,
        "artifact_id": artifact_id,
        "target_java": target_java,
        "compatible_versions": compatible_versions
    })

def resolve_best_combination(root_dependencies: List[Dict[str, str]], target_java: str = "17") -> str:
    """
    Attempts to find the best (highest compatible) versions for a set of root dependencies
    that satisfy all transitive requirements.
    Input: [{"groupId": "...", "artifactId": "..."}] (versions are optional)
    """
    # 1. For each root dep, get candidate versions (top 5)
    candidates = {} # (g, a) -> [v1, v2, v3, v4, v5]
    for dep in root_dependencies:
        g, a = dep['groupId'], dep['artifactId']
        v_json = list_all_versions(g, a)
        v_list = json.loads(v_json).get("versions", [])[:50]
        # Only keep versions compatible with target JDK
        comp_list = []
        for v in v_list:
            res = json.loads(check_java_compatibility(g, a, v, target_java))
            if res['is_compatible'] in ["Yes", "Yes (Assumed)", "Maybe"]:
                comp_list.append(v)
        if comp_list:
            candidates[(g, a)] = comp_list

    # 2. Simple Heuristic: Try to find a combination that minimizes conflicts
    # If no compatible versions found for a root, we can't resolve
    if not candidates:
        return json.dumps({"error": "No compatible versions found for any root dependency.", "recommended_combination": []})

    current_combo = {k: v[0] for k, v in candidates.items()}
    
    def get_conflicts(combo):
        deps_to_test = [{"groupId": k[0], "artifactId": k[1], "version": v} for k, v in combo.items()]
        conflict_json = detect_transitive_conflicts(deps_to_test)
        return json.loads(conflict_json).get("conflicts", [])

    conflicts = get_conflicts(current_combo)
    
    # Simple backtracking / local search (limit steps)
    for _ in range(5):
        if not conflicts: break
        
        # Pick a conflict and try to resolve it by moving candidates
        conflict = conflicts[0]
        # target_lib = conflict['dependency']
        
        # Try downgrading each root that participates in this conflict
        improved = False
        for root_key in current_combo:
            root_v_list = candidates[root_key]
            current_v_idx = root_v_list.index(current_combo[root_key])
            
            if current_v_idx < len(root_v_list) - 1:
                # Try next (older) version
                test_combo = current_combo.copy()
                test_combo[root_key] = root_v_list[current_v_idx + 1]
                new_conflicts = get_conflicts(test_combo)
                if len(new_conflicts) < len(conflicts):
                    current_combo = test_combo
                    conflicts = new_conflicts
                    improved = True
                    break
        if not improved: break

    return json.dumps({
        "recommended_combination": [
            {"groupId": k[0], "artifactId": k[1], "version": v} for k, v in current_combo.items()
        ],
        "remaining_conflicts": conflicts
    })
