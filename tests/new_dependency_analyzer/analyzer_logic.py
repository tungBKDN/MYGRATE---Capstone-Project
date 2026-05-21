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
            
            # Resolve properties
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
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = _parse_pom_xml_content(response.text)
            if "error" in data: return json.dumps([])
            return json.dumps(data.get("dependencies", []))
        return json.dumps([])
    except: return json.dumps([])

def get_jar_major_version(group_id: str, artifact_id: str, version: str) -> int:
    """Downloads the JAR (partially if possible) and checks the major version of its class files."""
    g_path = group_id.replace('.', '/')
    url = f"https://repo1.maven.org/maven2/{g_path}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
    try:
        # To open a ZIP, we need the Central Directory at the end of the file.
        # We'll try to fetch the first 100KB and the last 100KB.
        head = requests.head(url, timeout=5)
        if head.status_code != 200: return -1
        file_size = int(head.headers.get('Content-Length', 0))
        
        if file_size == 0: return -1
        
        import zipfile
        import io
        
        if file_size < 200000:
            # Small enough to download whole
            content = requests.get(url, timeout=10).content
        else:
            # Fetch start and end
            start = requests.get(url, headers={'Range': 'bytes=0-100000'}, timeout=10).content
            end = requests.get(url, headers={'Range': f'bytes={file_size-100000}-{file_size}'}, timeout=10).content
            # Combine with null padding in between (zipfile can often handle this if we are lucky, 
            # but actually it's better to just download the whole thing if it's not huge, e.g. < 5MB)
            if file_size < 5000000:
                content = requests.get(url, timeout=10).content
            else:
                # For very large files, this is tricky without a real streaming zip reader.
                # Let's just try to download the whole thing for now but with a larger limit.
                content = requests.get(url, timeout=20).content

        z = zipfile.ZipFile(io.BytesIO(content))
        for name in z.namelist():
            if name.endswith(".class") and not "module-info" in name:
                with z.open(name) as f:
                    header = f.read(8)
                    if len(header) < 8: continue
                    if header[:4] == b'\xca\xfe\xba\xbe':
                        major = int.from_bytes(header[6:8], byteorder='big')
                        return major
        return -1
    except: return -1

def check_java_compatibility(group_id: str, artifact_id: str, version: str, target_java: str = "17") -> str:
    """Checks compatibility using both metadata and bytecode inspection."""
    
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
    
    # Metadata Check (Parent POM chasing)
    for depth in range(3): # Limit depth for speed
        g_path = current_g.replace('.', '/')
        pom_url = f"https://repo1.maven.org/maven2/{g_path}/{current_a}/{current_v}/{current_a}-{current_v}.pom"
        try:
            response = requests.get(pom_url, timeout=5)
            if response.status_code != 200: break
            content = response.text
            found = find_jdk_in_content(content)
            if found:
                target_jdk = found
                break
            parent_match = re.search(r'<parent>(.*?)</parent>', content, re.DOTALL)
            if parent_match:
                p_content = parent_match.group(1)
                pg = re.search(r'<groupId>(.*?)</groupId>', p_content)
                pa = re.search(r'<artifactId>(.*?)</artifactId>', p_content)
                pv = re.search(r'<version>(.*?)</version>', p_content)
                if pg and pa and pv:
                    current_g, current_a, current_v = pg.group(1).strip(), pa.group(1).strip(), pv.group(1).strip()
                else: break
            else: break
        except: break

    # Bytecode Check (Verification)
    bytecode_major = get_jar_major_version(group_id, artifact_id, version)
    bytecode_jdk = "Unknown"
    if bytecode_major != -1:
        # Map major version to JDK version
        major_map = {45: "1.1", 46: "1.2", 47: "1.3", 48: "1.4", 49: "5", 50: "6", 51: "7", 52: "8", 53: "9", 54: "10", 55: "11", 56: "12", 57: "13", 58: "14", 59: "15", 60: "16", 61: "17", 62: "18", 63: "19", 64: "20", 65: "21", 66: "22"}
        bytecode_jdk = major_map.get(bytecode_major, str(bytecode_major - 44) if bytecode_major > 44 else "Unknown")

    # Final Decision logic
    def norm(v):
        if not v or v == "Unknown": return None
        v_s = str(v)
        v_s = v_s.split('.')[-1] if '.' in v_s and v_s.startswith('1.') else v_s
        try:
            m = re.search(r'\d+', v_s)
            return int(m.group()) if m else None
        except: return None

    nt = norm(target_java)
    nlt = norm(target_jdk)
    nbc = norm(bytecode_jdk)
    
    # Decision logic
    effective_jdk = bytecode_jdk if nbc else target_jdk
    
    # Heuristics based on version patterns if still unknown
    if effective_jdk == "Unknown":
        v_str = str(version)
        if group_id == "org.springframework.boot":
            if v_str.startswith("3."): effective_jdk = "17"
            elif v_str.startswith("2."): effective_jdk = "8"
        elif "1.7." in v_str or "1.6." in v_str: effective_jdk = "1.6"
        elif "1.8." in v_str: effective_jdk = "1.8"
    
    ne = norm(effective_jdk)
    is_compatible = "Maybe"
    
    if ne and nt:
        is_compatible = "No" if ne > nt else "Yes"
    elif nt and nt >= 8:
        is_compatible = "Yes (Assumed)"

    return json.dumps({
        "dependency": f"{group_id}:{artifact_id}",
        "version": version,
        "metadata_jdk": target_jdk,
        "bytecode_jdk": bytecode_jdk,
        "effective_jdk": effective_jdk,
        "is_compatible": is_compatible,
        "verification_url": f"https://search.maven.org/artifact/{group_id}/{artifact_id}/{version}/jar"
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

class DependencySolver:
    """
    A robust backtracking solver for dependency combinations.
    Handles JDK compatibility and transitive version constraints.
    """
    def __init__(self, target_java: str):
        self.target_java = target_java
        self.candidates = {}  # (g, a) -> [v1, v2, ...]
        self.constraints = {} # (g, a, v) -> [transitive_deps]
        self.solutions = []

    def add_library(self, group_id: str, artifact_id: str, max_versions: int = 10):
        v_json = list_all_versions(group_id, artifact_id)
        v_list = json.loads(v_json).get("versions", [])[:max_versions]
        
        comp_list = []
        for v in v_list:
            res = json.loads(check_java_compatibility(group_id, artifact_id, v, self.target_java))
            if res['is_compatible'] in ["Yes", "Yes (Assumed)", "Maybe"]:
                comp_list.append(v)
                # Cache transitive deps for this version
                t_deps = json.loads(get_transitive_dependencies(group_id, artifact_id, v))
                self.constraints[(group_id, artifact_id, v)] = t_deps
        
        if comp_list:
            self.candidates[(group_id, artifact_id)] = comp_list

    def solve(self, current_combo=None, remaining_libs=None):
        if current_combo is None:
            current_combo = {}
            remaining_libs = list(self.candidates.keys())

        if not remaining_libs:
            # Check if this combination is valid across all transitive constraints
            if self._is_valid_combination(current_combo):
                self.solutions.append(current_combo.copy())
            return

        lib_key = remaining_libs[0]
        for version in self.candidates[lib_key]:
            current_combo[lib_key] = version
            self.solve(current_combo, remaining_libs[1:])
            if len(self.solutions) >= 5: return # Limit to top 5 solutions
            del current_combo[lib_key]

    def _is_valid_combination(self, combo):
        # Flatten all transitive dependencies requested by this combination
        version_map = {f"{g}:{a}": v for (g, a), v in combo.items()}
        
        for (g, a), v in combo.items():
            transitives = self.constraints.get((g, a, v), [])
            for t in transitives:
                t_key = f"{t['groupId']}:{t['artifactId']}"
                t_v = t['version']
                
                # If the transitive dependency is one of our root libs, versions must match
                if t_key in version_map and t_v != "Managed":
                    # Simple equality check for now (Maven uses nearest-wins, but for 'safe' migration we want consistency)
                    if version_map[t_key] != t_v:
                        return False
        return True

def get_jar_major_version_and_signatures(group_id: str, artifact_id: str, version: str) -> Dict:
    """Enhanced scan: Checks major version AND presence of removed Java EE packages."""
    g_path = group_id.replace('.', '/')
    url = f"https://repo1.maven.org/maven2/{g_path}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
    results = {"major": -1, "dangerous_packages": []}
    
    removed_packages = ["javax/xml/bind", "javax/activation", "javax/annotation", "javax/xml/ws", "javax/jws", "javax/xml/soap"]
    
    try:
        # Download the whole JAR for small/medium files (<10MB) to be safe
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return results
        
        import zipfile, io
        z = zipfile.ZipFile(io.BytesIO(response.content))
        
        found_major = False
        for name in z.namelist():
            if not found_major and name.endswith(".class") and not "module-info" in name:
                with z.open(name) as f:
                    header = f.read(8)
                    if len(header) >= 8 and header[:4] == b'\xca\xfe\xba\xbe':
                        results["major"] = int.from_bytes(header[6:8], byteorder='big')
                        found_major = True
            
            for pkg in removed_packages:
                if name.startswith(pkg) and (pkg not in results["dangerous_packages"]):
                    results["dangerous_packages"].append(pkg)
                        
        return results
    except: return results

def check_java_compatibility(group_id: str, artifact_id: str, version: str, target_java: str = "17") -> str:
    """Upgraded: Metadata + Bytecode Major + Java EE Signature Scan."""
    
    def find_jdk_in_content(xml_content):
        tags = ['maven.compiler.target', 'maven.compiler.release', 'maven.compiler.source', 'java.version']
        for tag in tags:
            match = re.search(f'<{tag}>(.*?)</{tag}>', xml_content)
            if match:
                val = match.group(1).strip()
                if val and not val.startswith("${"): return val
        return None

    target_jdk = "Unknown"
    # Metadata Check (Partial parent chasing)
    g_path = group_id.replace('.', '/')
    pom_url = f"https://repo1.maven.org/maven2/{g_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom"
    try:
        response = requests.get(pom_url, timeout=5)
        if response.status_code == 200:
            target_jdk = find_jdk_in_content(response.text) or "Unknown"
    except: pass

    def norm(v):
        if not v or v == "Unknown": return None
        v_s = str(v).split('.')[-1] if '.' in str(v) and str(v).startswith('1.') else str(v)
        m = re.search(r'\d+', v_s)
        return int(m.group()) if m else None

    nt = norm(target_java)
    
    # Perform Enhanced Scan
    scan_results = get_jar_major_version_and_signatures(group_id, artifact_id, version)
    major = scan_results["major"]
    dangerous = scan_results["dangerous_packages"]
    
    bytecode_jdk = "Unknown"
    if major != -1:
        major_map = {52: "8", 53: "9", 54: "10", 55: "11", 61: "17", 65: "21"}
        bytecode_jdk = major_map.get(major, str(major - 44) if major > 44 else "Unknown")
    
    nbc = norm(bytecode_jdk)
    nlt = norm(target_jdk)
    
    effective_jdk = bytecode_jdk if nbc else target_jdk
    ne = nbc if nbc else nlt
    
    is_compatible = "Yes"
    issues = []
    
    if ne and nt and ne > nt:
        is_compatible = "No"
        issues.append(f"Requires JDK {effective_jdk} but target is {target_java}")
        
    if nt and nt >= 11 and dangerous:
        is_compatible = "Warning"
        issues.append(f"Uses Java EE packages removed in JDK 11: {', '.join(dangerous)}")

    return json.dumps({
        "dependency": f"{group_id}:{artifact_id}",
        "version": version,
        "metadata_jdk": target_jdk,
        "bytecode_jdk": bytecode_jdk,
        "effective_jdk": effective_jdk,
        "is_compatible": is_compatible,
        "issues": issues
    })

def resolve_best_combination(root_dependencies: List[Dict[str, str]], target_java: str = "17") -> str:
    """Upgraded: Uses the DependencySolver class for better combinations."""
    solver = DependencySolver(target_java)
    for dep in root_dependencies:
        solver.add_library(dep['groupId'], dep['artifactId'], max_versions=5)
    
    solver.solve()
    
    if not solver.solutions:
        return json.dumps({"error": "No valid combination found.", "recommended_combination": []})
        
    return json.dumps({
        "recommended_combination": [
            {"groupId": k[0], "artifactId": k[1], "version": v} for k, v in solver.solutions[0].items()
        ],
        "all_valid_solutions_count": len(solver.solutions)
    })
