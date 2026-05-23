import os
import re
import json
import requests
import zipfile
import io
import urllib.parse
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

from langchain_core.tools import tool

# ==============================================================================
# HÀM LÕI
# ==============================================================================

def list_all_versions(group_id: str, artifact_id: str) -> str:
    """Retrieves the latest 50 versions from Maven Central, numerically sorted."""
    def version_key(v: str):
        parts = re.split(r'[-.]', str(v))
        return [part.zfill(8) if part.isdigit() else part for part in parts]

    url = f"https://search.maven.org/solrsearch/select?q=g:%22{group_id}%22+AND+a:%22{artifact_id}%22&core=gav&rows=50&wt=json"
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            docs = response.json().get('response', {}).get('docs', [])
            if not docs: return json.dumps({"error": f"No versions found for {group_id}:{artifact_id}"})
            versions = [doc['v'] for doc in docs]
            versions.sort(key=version_key, reverse=True)
            return json.dumps({"versions": versions})
    except Exception as e:
        return json.dumps({"error": str(e)})
    return json.dumps({"error": "Lookup failed."})

def heuristic_filter(versions: list, max_output: int = 5, stable_only: bool = True):
    unstable = ['alpha', 'beta', 'rc', 'm', 'preview', 'snapshot']
    filtered = [v for v in versions if not (stable_only and any(k in v.lower() for k in unstable))]
    return filtered[:max_output]

def check_java_compatibility(group_id, artifact_id, version, target_java="17", verbose=False):
    """Quét JAR từ Maven để xác định JDK và các gói Java EE bị xóa."""
    g_path = group_id.replace('.', '/')
    url = f"https://repo1.maven.org/maven2/{g_path}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
    
    res = {"max_major": -1, "dangerous_refs": set()}
    try:
        resp = requests.get(url, stream=True, timeout=15)
        if resp.status_code == 200:
            content = resp.content
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                classes = [n for n in z.namelist() if n.endswith(".class")][:30]
                for c_name in classes:
                    with z.open(c_name) as f:
                        data = f.read()
                        if len(data) > 8:
                            res["max_major"] = max(res["max_major"], int.from_bytes(data[6:8], 'big'))
                        for pkg in [b"javax/xml/bind", b"javax/activation", b"javax/annotation"]:
                            if pkg in data: res["dangerous_refs"].add(pkg.decode())
    except: pass
    
    major_map = {52: "8", 53: "9", 55: "11", 61: "17", 65: "21"}
    bytecode_jdk = major_map.get(res["max_major"], str(res["max_major"] - 44) if res["max_major"] > 44 else "Unknown")
    
    status = "Yes"
    target_n = int(target_java)
    bytecode_n = int(bytecode_jdk) if bytecode_jdk.isdigit() else 0
    if bytecode_n > target_n: status = "No"
    elif target_n >= 11 and res["dangerous_refs"]: status = "Warning"
    
    # Heuristic for Spring Boot 3.x requiring Java 17 (handles POM-only artifacts)
    if (group_id == "org.springframework.boot" or "spring-boot" in artifact_id) and version.startswith("3."):
        if target_n < 17:
            status = "No"
            bytecode_jdk = "17"
    
    return {
        "dependency": f"{group_id}:{artifact_id}",
        "version": version,
        "signals": {"bytecode_jdk": bytecode_jdk, "refs": list(res["dangerous_refs"])},
        "analysis": {"compatibility_status": status}
    }

def get_transitive_dependencies(group_id: str, artifact_id: str, version: str) -> str:
    """Sử dụng deps.dev API để lấy danh sách dependencies đã được phân giải."""
    pkg_name = urllib.parse.quote(f"{group_id}:{artifact_id}", safe='')
    url = f"https://api.deps.dev/v3/systems/maven/packages/{pkg_name}/versions/{version}:dependencies"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            resolved_deps = []
            nodes = data.get("nodes", [])
            for i, node in enumerate(nodes):
                if i == 0: continue 
                vk = node.get("versionKey", {})
                name_parts = vk.get("name", "").split(":")
                if len(name_parts) == 2:
                    g, a = name_parts
                    v = vk.get("version", "")
                    resolved_deps.append({
                        "groupId": g,
                        "artifactId": a,
                        "version": v,
                        "scope": "compile" 
                    })
            return json.dumps(resolved_deps)
        return json.dumps([])
    except Exception as e:
        return json.dumps([])

def prepare_jar_for_check(group_id: str, artifact_id: str, version: str, cache_dir: str = "./temp_jars") -> str:
    """Tải file JAR từ Maven Central về máy để phục vụ biên dịch thử."""
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    g_path = group_id.replace('.', '/')
    url = f"https://repo1.maven.org/maven2/{g_path}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
    jar_path = os.path.abspath(os.path.join(cache_dir, f"{artifact_id}-{version}.jar"))
    
    if not os.path.exists(jar_path):
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200:
            with open(jar_path, "wb") as f:
                f.write(resp.content)
        else:
            return ""
    return jar_path

def run_compile_check(jar_path: str, target_jdk: str = "17", verbose: bool = False) -> dict:
    """Thực hiện Bước 4: Kiểm tra tính tương thích bằng cách biên dịch mã nguồn 'mồi'."""
    if not jar_path or not os.path.exists(jar_path):
        return {"status": "FAIL", "reason": "Không tìm thấy file JAR"}

    stub_file = "MigrationStub.java"
    with open(stub_file, "w") as f:
        f.write("public class MigrationStub { public static void main(String[] args) {} }")
    
    try:
        cmd = ["javac", "-cp", jar_path, "--release", target_jdk, stub_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return {"status": "PASS", "details": "Nguồn tương thích hoàn toàn"}
        else:
            return {"status": "FAIL", "reason": "Lỗi biên dịch", "error": result.stderr}
    except FileNotFoundError:
        return {"status": "ERROR", "reason": "Lệnh javac không có trong PATH"}
    finally:
        if os.path.exists(stub_file): os.remove(stub_file)
        class_file = stub_file.replace(".java", ".class")
        if os.path.exists(class_file): os.remove(class_file)

class DependencySolver:
    """Bộ giải thuật quay lui tích hợp Pipeline 7 bước."""
    def __init__(self, target_java: str):
        self.target_java: str = target_java
        self.candidates: Dict[Tuple[str, str], List[str]] = {}  
        self.constraints: Dict[Tuple[str, str, str], List[Dict]] = {} 
        self.solutions: List[Dict[Tuple[str, str], str]] = []
        self.reports: Dict[Tuple[str, str, str], dict] = {}
        self.requested_libs: Set[Tuple[str, str]] = set()

    def add_library(self, group_id: str, artifact_id: str, max_versions: int = 5) -> None:
        self.requested_libs.add((group_id, artifact_id))
        v_json = list_all_versions(group_id, artifact_id)
        all_v = json.loads(v_json).get("versions", [])
        v_list = heuristic_filter(all_v, max_output=max_versions)
        
        candidates_v3 = []
        for v in v_list:
            res_3 = check_java_compatibility(group_id, artifact_id, v, self.target_java)
            self.reports[(group_id, artifact_id, v)] = {"step3": res_3}
            
            if res_3['analysis']['compatibility_status'] in ["Yes", "Warning"]:
                candidates_v3.append(v)
                t_deps_raw = get_transitive_dependencies(group_id, artifact_id, v)
                self.constraints[(group_id, artifact_id, v)] = json.loads(t_deps_raw)
        
        if candidates_v3:
            self.candidates[(group_id, artifact_id)] = candidates_v3

    def solve(self, current_combo=None, remaining_libs=None):
        if len(self.candidates) < len(self.requested_libs):
            return
        if current_combo is None:
            current_combo = {}; remaining_libs = list(self.candidates.keys())
        if not remaining_libs:
            if self._is_valid_combination(current_combo): self.solutions.append(current_combo.copy())
            return
        lib_key = remaining_libs[0]
        for v in self.candidates[lib_key]:
            current_combo[lib_key] = v
            self.solve(current_combo, remaining_libs[1:])
            if len(self.solutions) >= 5: return 
            del current_combo[lib_key]

    def _is_valid_combination(self, combo):
        version_map = {f"{g}:{a}": v for (g, a), v in combo.items()}
        for (g, a), v in combo.items():
            for t in self.constraints.get((g, a, v), []):
                t_key = f"{t['groupId']}:{t['artifactId']}"
                if t_key in version_map and t['version'] != "Managed":
                    if version_map[t_key] != t['version']: return False
        return True

def inject_constrained_versions(solver: DependencySolver):
    for (g, a, v), t_deps in list(solver.constraints.items()):
        for t in t_deps:
            target_key = (t["groupId"], t["artifactId"])
            if target_key in solver.candidates:
                req_version = t["version"]
                if req_version not in solver.candidates[target_key]:
                    solver.candidates[target_key].append(req_version)
                    res_3 = check_java_compatibility(t["groupId"], t["artifactId"], req_version, solver.target_java)
                    solver.reports[(t["groupId"], t["artifactId"], req_version)] = {"step3": res_3}
                    t_deps_raw = get_transitive_dependencies(t["groupId"], t["artifactId"], req_version)
                    solver.constraints[(t["groupId"], t["artifactId"], req_version)] = json.loads(t_deps_raw)

# ==============================================================================
# LANGCHAIN TOOLS
# ==============================================================================

@tool
def fetch_candidate_versions(group_id: str, artifact_id: str) -> List[str]:
    """Bước 1: Lấy tập candidate versions từ Maven Central."""
    res = json.loads(list_all_versions(group_id, artifact_id))
    return res.get("versions", [])

@tool
def heuristic_version_filter(versions: List[str], target_jdk: str) -> List[str]:
    """Bước 2: Tiền lọc heuristic để loại bỏ các version quá cũ hoặc không ổn định."""
    return heuristic_filter(versions)

@tool
def static_compatibility_check(group_id: str, artifact_id: str, version: str, target_jdk: str) -> Dict[str, Any]:
    """Bước 3: Kiểm tra tương thích tĩnh (API/Bytecode) thông qua phân tích JAR thực tế."""
    return check_java_compatibility(group_id, artifact_id, version, target_java=target_jdk)

@tool
def solve_transitive_constraints(dependencies: List[Dict[str, Any]], target_jdk: str) -> List[Dict[str, str]]:
    """
    Bước 5 & 6: Giải quyết xung đột transitive dependency thực tế bằng Backtracking Solver.
    Input format: dependencies = [{"group_id": "...", "artifact_id": "..."}]
    """
    solver = DependencySolver(target_java=target_jdk)
    for dep in dependencies:
        g = dep.get("group_id")
        a = dep.get("artifact_id")
        if g and a:
            solver.add_library(group_id=g, artifact_id=a, max_versions=5)
            
    inject_constrained_versions(solver)
    solver.solve()
    
    formatted_solutions = []
    for sol in solver.solutions:
        formatted_solutions.append({f"{k[0]}:{k[1]}": v for k, v in sol.items()})
    
    return formatted_solutions

@tool
def runtime_smoke_test(group_id: str, artifact_id: str, version: str, target_jdk: str) -> Dict[str, Any]:
    """Bước 4 & 7: Biên dịch thử nghiệm (Compile-check) để xác thực vật lý khả năng tương thích của 1 JAR."""
    jar_path = prepare_jar_for_check(group_id, artifact_id, version)
    res = run_compile_check(jar_path, target_jdk=target_jdk)
    return res
