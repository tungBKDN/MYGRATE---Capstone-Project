"""
Maven upgrade pipeline — full 7-step dependency compatibility analysis.

Step 1: Fetch candidate versions from Maven Central
Step 2: Heuristic filter (remove unstable versions)
Step 3: Static check (bytecode scan + Java EE refs detection)
Step 4: Compile check (javac --release verification)
Step 5: Transitive constraint modeling
Step 6: SAT/SMT solver (Z3, with backtracking fallback)
Step 7: Runtime smoke test (JVM class loading)

Entry points:
    index_java_project()     — lightweight index + POM parse (Reader)
    run_upgrade_pipeline()   — full B1-B7 analysis (Architect)
    build_java_upgrade_report() — backward-compatible wrapper
"""

import io
import json
import os
import platform
import re
import subprocess
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import requests

try:
    from z3 import Bool, If, Sum, Implies, Not, And, Optimize, sat, is_true

    HAS_Z3 = True
except ImportError:
    HAS_Z3 = False

from .codebase_indexer import index_codebase


def _emit(logger, message: str) -> None:
    if logger is None:
        return
    try:
        logger(message)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# POM Parsing
# ---------------------------------------------------------------------------

def _find_root_manifest(project_root: Path) -> Optional[Path]:
    direct_pom = project_root / "pom.xml"
    if direct_pom.exists():
        return direct_pom
    pom_candidates = sorted(project_root.rglob("pom.xml"))
    return pom_candidates[0] if pom_candidates else None


def _parse_pom(pom_path: Path) -> dict:
    with open(pom_path, "r", encoding="utf-8") as handle:
        xml_content = handle.read()

    root = ET.fromstring(xml_content)
    ns_url = ""
    if root.tag.startswith("{"):
        ns_url = root.tag.split("}")[0][1:]
    ns = {"mvn": ns_url} if ns_url else {}

    def find_text(node, path):
        found = node.find(path, ns)
        return found.text.strip() if found is not None and found.text else None

    project_group = find_text(root, "mvn:groupId")
    project_artifact = find_text(root, "mvn:artifactId")
    project_version = find_text(root, "mvn:version")

    parent = root.find("mvn:parent", ns)
    if parent is not None:
        if not project_group:
            project_group = find_text(parent, "mvn:groupId")
        if not project_version:
            project_version = find_text(parent, "mvn:version")

    properties = {
        "project.groupId": project_group or "",
        "project.artifactId": project_artifact or "",
        "project.version": project_version or "",
    }
    props_node = root.find("mvn:properties", ns)
    if props_node is not None:
        for prop in props_node:
            tag = prop.tag.split("}")[-1] if "}" in prop.tag else prop.tag
            if prop.text:
                properties[tag] = prop.text.strip()

    dependencies = []
    deps_node = root.find("mvn:dependencies", ns)
    if deps_node is not None:
        for dep in deps_node.findall("mvn:dependency", ns):
            dependencies.append(_parse_dependency(dep, find_text, properties))

    return {
        "project": {
            "groupId": project_group or "Unknown",
            "artifactId": project_artifact or "Unknown",
            "version": project_version or "Unknown",
        },
        "properties": properties,
        "dependencies": dependencies,
    }


def _parse_dependency(dep_node, find_text, properties: dict) -> dict:
    group_id = find_text(dep_node, "mvn:groupId") or ""
    artifact_id = find_text(dep_node, "mvn:artifactId") or ""
    version = find_text(dep_node, "mvn:version") or "Managed"
    scope = find_text(dep_node, "mvn:scope") or "compile"
    resolved_version = _resolve_properties(version, properties)
    return {
        "groupId": _resolve_properties(group_id, properties),
        "artifactId": _resolve_properties(artifact_id, properties),
        "version": resolved_version,
        "scope": scope,
        "raw_version": version,
    }


def _resolve_properties(value: str, properties: dict) -> str:
    if not value or not isinstance(value, str):
        return value
    resolved = value
    for _ in range(5):
        matches = re.findall(r"\$\{([^}]+)\}", resolved)
        if not matches:
            break
        changed = False
        for prop_name in matches:
            if prop_name in properties:
                resolved = resolved.replace(f"${{{prop_name}}}", properties[prop_name])
                changed = True
        if not changed:
            break
    return resolved


def _has_java_manifest(manifest_files: List[Dict[str, str]]) -> bool:
    return any(
        m.get("type") == "maven" or m.get("path", "").endswith("pom.xml")
        for m in manifest_files
    )


def _summarize_index(index_data: dict) -> dict:
    source_files = index_data.get("source_files", [])
    manifests = index_data.get("manifest_files", [])
    notebooks = index_data.get("notebooks", [])
    return {
        "project_type": index_data.get("project_type", "unknown"),
        "language_counts": index_data.get("language_counts", {}),
        "source_file_count": index_data.get("source_file_count", len(source_files)),
        "manifest_count": index_data.get("manifest_count", len(manifests)),
        "notebook_count": index_data.get("notebook_count", len(notebooks)),
        "manifest_files": manifests,
        "notebooks": notebooks,
        "sample_source_files": source_files[:15],
    }


# ---------------------------------------------------------------------------
# Version Utilities
# ---------------------------------------------------------------------------

def _normalize_java_version(value: str) -> int:
    if not value:
        return 0
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else 0


def _stable_version(version: str) -> bool:
    lowered = version.lower()
    unstable_tokens = ["alpha", "beta", "rc", "m", "preview", "snapshot"]
    return not any(token in lowered for token in unstable_tokens)


def _version_key(version: str) -> Tuple[int, int, int, int, str]:
    numbers = [int(part) for part in re.findall(r"\d+", version)[:4]]
    while len(numbers) < 4:
        numbers.append(0)
    return numbers[0], numbers[1], numbers[2], numbers[3], version.lower()


def _major(version: str) -> int:
    numbers = re.findall(r"\d+", version)
    return int(numbers[0]) if numbers else -1


def _find_jdeprscan_executable() -> Optional[str]:
    candidates = []

    direct = shutil.which("jdeprscan")
    if direct:
        candidates.append(direct)

    java_executable = shutil.which("java")
    if java_executable:
        java_bin_dir = Path(java_executable).resolve().parent
        for name in ("jdeprscan.exe", "jdeprscan"):
            sibling = java_bin_dir / name
            if sibling.exists():
                candidates.append(str(sibling))

    java_home = os.getenv("JAVA_HOME")
    if java_home:
        java_bin_dir = Path(java_home).expanduser() / "bin"
        for name in ("jdeprscan.exe", "jdeprscan"):
            sibling = java_bin_dir / name
            if sibling.exists():
                candidates.append(str(sibling))

    if os.name == "nt":
        common_roots = [
            os.getenv("ProgramFiles"),
            os.getenv("ProgramFiles(x86)"),
            os.getenv("ProgramW6432"),
        ]
        common_vendor_dirs = ["Java", "Eclipse Adoptium", "Microsoft"]
        for root in common_roots:
            if not root:
                continue
            root_path = Path(root)
            for vendor_dir in common_vendor_dirs:
                vendor_path = root_path / vendor_dir
                if not vendor_path.exists():
                    continue
                for jdk_dir in vendor_path.glob("jdk*"):
                    for name in ("jdeprscan.exe", "jdeprscan"):
                        sibling = jdk_dir / "bin" / name
                        if sibling.exists():
                            candidates.append(str(sibling))

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def _parse_jdeprscan_output(output: str) -> List[dict]:
    findings: List[dict] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Jar file ") or line.startswith("Directory "):
            continue
        if "deprecated" not in line.lower():
            continue

        match = re.search(
            r"^(?P<owner>\S+) uses deprecated (?P<kind>class|method|field|interface) (?P<symbol>.+)$",
            line,
        )
        if match:
            findings.append(
                {
                    "owner": match.group("owner"),
                    "kind": match.group("kind"),
                    "symbol": match.group("symbol"),
                    "line": line,
                }
            )
        else:
            findings.append({"line": line})
    return findings


def run_jdeprscan_check(jar_path: str, target_release: str = "17", logger=None) -> dict:
    if not jar_path or not os.path.exists(jar_path):
        return {"status": "SKIP", "reason": "JAR not found"}

    jdeprscan_executable = _find_jdeprscan_executable()
    if not jdeprscan_executable:
        return {"status": "SKIP", "reason": "jdeprscan not available"}

    try:
        _emit(logger, f"[Step 3] Running jdeprscan --release {target_release} for {Path(jar_path).name}")
        result = subprocess.run(
            [jdeprscan_executable, "--release", target_release, jar_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined_output = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
        findings = _parse_jdeprscan_output(combined_output)
        return {
            "status": "WARN" if findings else "PASS",
            "executable": jdeprscan_executable,
            "exit_code": result.returncode,
            "finding_count": len(findings),
            "findings": findings,
            "output": combined_output,
        }
    except FileNotFoundError:
        return {"status": "SKIP", "reason": "jdeprscan not available"}
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "reason": "jdeprscan timeout"}


def _inspect_jar_signals(content: bytes) -> dict:
    result = {"max_major": -1, "dangerous_refs": set()}
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        classes = [n for n in z.namelist() if n.endswith(".class")][:30]
        for c_name in classes:
            with z.open(c_name) as f:
                data = f.read()
                if len(data) > 8:
                    result["max_major"] = max(result["max_major"], int.from_bytes(data[6:8], "big"))
                for pkg in [b"javax/xml/bind", b"javax/activation", b"javax/annotation"]:
                    if pkg in data:
                        result["dangerous_refs"].add(pkg.decode())
    return result


# ---------------------------------------------------------------------------
# Step 1: Fetch candidate versions
# ---------------------------------------------------------------------------

def _fetch_maven_versions(group_id: str, artifact_id: str) -> List[str]:
    query = f'g:"{group_id}" AND a:"{artifact_id}"'
    url = (
        "https://search.maven.org/solrsearch/select?"
        f"q={requests.utils.quote(query)}&core=gav&rows=100&wt=json"
    )
    try:
        response = requests.get(url, timeout=20)
        if response.status_code != 200:
            return []
        docs = response.json().get("response", {}).get("docs", [])
        versions = [doc.get("v") for doc in docs if doc.get("v")]
        return sorted(set(versions), key=_version_key, reverse=True)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Step 2: Heuristic filter
# ---------------------------------------------------------------------------

def heuristic_filter(versions: List[str], max_output: int = 5, stable_only: bool = True) -> List[str]:
    unstable = ["alpha", "beta", "rc", "m", "preview", "snapshot"]
    filtered = [v for v in versions if not (stable_only and any(k in v.lower() for k in unstable))]
    return filtered[:max_output]


# ---------------------------------------------------------------------------
# Step 3: Static check — bytecode scan + Java EE refs + jdeprscan
# ---------------------------------------------------------------------------

def check_java_compatibility(group_id: str, artifact_id: str, version: str, target_java: str = "17", logger=None, jar_path: str | None = None) -> dict:
    g_path = group_id.replace(".", "/")
    url = f"https://repo1.maven.org/maven2/{g_path}/{artifact_id}/{version}/{artifact_id}-{version}.jar"

    result = {"max_major": -1, "dangerous_refs": set()}
    try:
        _emit(logger, f"[Step 3] Scanning {group_id}:{artifact_id}:{version} for bytecode and removed Java EE refs")
        if jar_path and os.path.exists(jar_path):
            with open(jar_path, "rb") as handle:
                content = handle.read()
            result = _inspect_jar_signals(content)
        else:
            resp = requests.get(url, stream=True, timeout=15)
            if resp.status_code == 200:
                content = resp.content
                result = _inspect_jar_signals(content)
    except Exception:
        pass

    result["dangerous_refs"] = list(result["dangerous_refs"])
    major_map = {52: "8", 53: "9", 55: "11", 61: "17", 65: "21"}
    bytecode_jdk = major_map.get(result["max_major"], str(result["max_major"] - 44) if result["max_major"] > 44 else "Unknown")

    jdeprscan_report = {"status": "SKIP", "reason": "jar not provided"}
    if jar_path and os.path.exists(jar_path):
        jdeprscan_report = run_jdeprscan_check(jar_path, target_java, logger=logger)

    status = "Yes"
    target_n = int(target_java)
    bytecode_n = int(bytecode_jdk) if bytecode_jdk.isdigit() else 0
    if bytecode_n > target_n:
        status = "No"
    elif target_n >= 11 and result["dangerous_refs"]:
        status = "Warning"
    elif jdeprscan_report.get("status") == "WARN":
        status = "Warning"

    return {
        "dependency": f"{group_id}:{artifact_id}",
        "version": version,
        "signals": {"bytecode_jdk": bytecode_jdk, "refs": result["dangerous_refs"], "jdeprscan": jdeprscan_report},
        "analysis": {"compatibility_status": status},
    }


# ---------------------------------------------------------------------------
# Step 4: Compile check
# ---------------------------------------------------------------------------

def prepare_jar_for_check(group_id: str, artifact_id: str, version: str, cache_dir: str = "./temp_jars", logger=None) -> str:
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    g_path = group_id.replace(".", "/")
    url = f"https://repo1.maven.org/maven2/{g_path}/{artifact_id}/{version}/{artifact_id}-{version}.jar"
    jar_path = os.path.abspath(os.path.join(cache_dir, f"{artifact_id}-{version}.jar"))
    if not os.path.exists(jar_path):
        try:
            _emit(logger, f"[Download] Fetching JAR {artifact_id}-{version}.jar")
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200:
                with open(jar_path, "wb") as f:
                    f.write(resp.content)
                _emit(logger, f"[Download] Saved {jar_path}")
            else:
                _emit(logger, f"[Download] Failed with HTTP {resp.status_code} for {artifact_id}-{version}.jar")
                return ""
        except Exception:
            _emit(logger, f"[Download] Failed to fetch {artifact_id}-{version}.jar")
            return ""
    else:
        _emit(logger, f"[Cache] Reusing {jar_path}")
    return jar_path


def run_compile_check(jar_path: str, target_jdk: str = "17", logger=None) -> dict:
    if not jar_path or not os.path.exists(jar_path):
        return {"status": "FAIL", "reason": "JAR not found"}
    import uuid
    unique_id = uuid.uuid4().hex
    stub_class = f"MigrationStub_{unique_id}"
    stub_file = f"{stub_class}.java"
    with open(stub_file, "w") as f:
        f.write(f"public class {stub_class} {{ public static void main(String[] args) {{}} }}")
    try:
        cmd = ["javac", "-cp", jar_path, "--release", target_jdk, stub_file]
        _emit(logger, f"[Step 4] Running javac --release {target_jdk} for {Path(jar_path).name}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return {"status": "PASS", "details": "Compatible"}
        return {"status": "FAIL", "reason": "Compile error", "error": result.stderr}
    except FileNotFoundError:
        return {"status": "SKIP", "reason": "javac not available"}
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "reason": "Compile timeout"}
    finally:
        for f in [stub_file, stub_file.replace(".java", ".class")]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


def _check_jdk_available() -> bool:
    try:
        result = subprocess.run(["javac", "-version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# DependencySolver — orchestrates Steps 1-4
# ---------------------------------------------------------------------------

import threading

class DependencySolver:
    def __init__(self, target_java: str, logger=None):
        self.target_java = target_java
        self.candidates: Dict[Tuple[str, str], List[str]] = {}
        self.constraints: Dict[Tuple[str, str, str], List[Dict]] = {}
        self.solutions: List[Dict[Tuple[str, str], str]] = []
        self.reports: Dict[Tuple[str, str, str], dict] = {}
        self.logger = logger
        self.lock = threading.Lock()

    def add_library(self, group_id: str, artifact_id: str, max_versions: int = 3) -> None:
        _emit(self.logger, f"[Step 1] Fetching Maven versions for {group_id}:{artifact_id}")
        all_v = _fetch_maven_versions(group_id, artifact_id)
        v_list = heuristic_filter(all_v, max_output=max_versions)
        _emit(self.logger, f"[Step 2] Heuristic filter kept {len(v_list)} stable version(s) for {artifact_id}")

        candidates_v3 = []
        for v in v_list:
            jar_p = prepare_jar_for_check(group_id, artifact_id, v, logger=self.logger)
            res = check_java_compatibility(group_id, artifact_id, v, self.target_java, logger=self.logger, jar_path=jar_p or None)
            
            with self.lock:
                self.reports[(group_id, artifact_id, v)] = {"step3": res}
            
            if res["analysis"]["compatibility_status"] in ("Yes", "Warning"):
                candidates_v3.append(v)
                _emit(self.logger, f"[Step 5] Fetching transitive dependencies for {artifact_id}:{v}")
                t_deps_raw = get_transitive_dependencies(group_id, artifact_id, v, logger=self.logger)
                with self.lock:
                    self.constraints[(group_id, artifact_id, v)] = json.loads(t_deps_raw)
                
                # SHORT-CIRCUIT
                if res["analysis"]["compatibility_status"] == "Yes":
                    _emit(self.logger, f"[Step 2-3] Short-circuiting: {artifact_id}:{v} is perfectly compatible.")
                    break

        with self.lock:
            if candidates_v3:
                self.candidates[(group_id, artifact_id)] = candidates_v3
                _emit(self.logger, f"[Step 3] {artifact_id} kept {len(candidates_v3)} candidate(s)")
            else:
                _emit(self.logger, f"[Step 3] {artifact_id} produced no compatible candidates")

    def run_step4(self) -> None:
        import concurrent.futures
        
        def check_candidate(g, a, v):
            jar_p = prepare_jar_for_check(g, a, v, logger=self.logger)
            res = run_compile_check(jar_p, self.target_java, logger=self.logger)
            return g, a, v, res

        tasks = []
        for (g, a), versions in self.candidates.items():
            for v in versions:
                tasks.append((g, a, v))
                
        results_by_lib = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_candidate, g, a, v) for g, a, v in tasks]
            for future in concurrent.futures.as_completed(futures):
                g, a, v, res = future.result()
                with self.lock:
                    self.reports.setdefault((g, a, v), {})["step4"] = res
                if res["status"] in ("PASS",):
                    results_by_lib.setdefault((g, a), []).append((v, res))

        # Preserve order of versions
        for (g, a), versions in list(self.candidates.items()):
            passed = []
            lib_res = results_by_lib.get((g, a), [])
            v_res_map = {v: r for v, r in lib_res}
            for v in versions:
                if v in v_res_map:
                    passed.append(v)
            with self.lock:
                if passed:
                    self.candidates[(g, a)] = passed
                    _emit(self.logger, f"[Step 4] {a} kept {len(passed)} version(s) after compile check")
                else:
                    self.candidates[(g, a)] = [versions[0]]
                    _emit(self.logger, f"[Step 4] {a} had no versions pass compile check. Keeping {versions[0]} as fallback for Translator to fix.")

    def solve(self) -> None:
        self.solutions = []
        self.backtrack_steps = 0
        self._solve_backtrack({}, list(self.candidates.keys()))

    def _solve_backtrack(self, current: dict, remaining: list) -> None:
        self.backtrack_steps += 1
        if self.backtrack_steps > 50000:
            return
        if not self._is_valid(current):
            return
        if not remaining:
            self.solutions.append(current.copy())
            return
        key = remaining[0]
        for v in self.candidates[key]:
            current[key] = v
            self._solve_backtrack(current, remaining[1:])
            if len(self.solutions) >= 5 or self.backtrack_steps > 50000:
                return
            del current[key]

    def _is_valid(self, combo: dict) -> bool:
        version_map = {f"{g}:{a}": v for (g, a), v in combo.items()}
        for (g, a), v in combo.items():
            for t in self.constraints.get((g, a, v), []):
                t_key_tuple = (t["groupId"], t["artifactId"])
                t_key_str = f"{t['groupId']}:{t['artifactId']}"
                if t.get("version") != "Managed":
                    if t_key_tuple in self.candidates:
                        if t["version"] not in self.candidates[t_key_tuple]:
                            return False
                        if t_key_str in version_map and version_map[t_key_str] != t["version"]:
                            return False
        return True


def inject_constrained_versions(solver: DependencySolver) -> None:
    for (g, a, v), t_deps in list(solver.constraints.items()):
        for t in t_deps:
            target_key = (t["groupId"], t["artifactId"])
            if target_key in solver.candidates:
                req_version = t["version"]
                if req_version not in solver.candidates[target_key]:
                    solver.candidates[target_key].append(req_version)
                    res = check_java_compatibility(t["groupId"], t["artifactId"], req_version, solver.target_java, logger=solver.logger)
                    solver.reports[(t["groupId"], t["artifactId"], req_version)] = {"step3": res}
                    t_deps_raw = get_transitive_dependencies(t["groupId"], t["artifactId"], req_version, logger=solver.logger)
                    solver.constraints[(t["groupId"], t["artifactId"], req_version)] = json.loads(t_deps_raw)


# ---------------------------------------------------------------------------
# Step 5: Transitive constraint modeling
# ---------------------------------------------------------------------------

_TRANSITIVE_CACHE = {}

def get_transitive_dependencies(group_id: str, artifact_id: str, version: str, logger=None) -> str:
    global _TRANSITIVE_CACHE
    cache_key = f"{group_id}:{artifact_id}:{version}"
    if cache_key in _TRANSITIVE_CACHE:
        return _TRANSITIVE_CACHE[cache_key]

    import urllib.parse as _urlparse
    pkg_name = _urlparse.quote(f"{group_id}:{artifact_id}", safe="")
    url = f"https://api.deps.dev/v3/systems/maven/packages/{pkg_name}/versions/{version}:dependencies"
    try:
        _emit(logger, f"[Step 5] Querying deps.dev for {group_id}:{artifact_id}:{version}")
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            resolved = []
            for i, node in enumerate(data.get("nodes", [])):
                if i == 0:
                    continue
                vk = node.get("versionKey", {})
                name_parts = vk.get("name", "").split(":")
                if len(name_parts) == 2:
                    g, a = name_parts
                    v = vk.get("version", "")
                    resolved.append({"groupId": g, "artifactId": a, "version": v, "scope": "compile"})
            _TRANSITIVE_CACHE[cache_key] = json.dumps(resolved)
            return _TRANSITIVE_CACHE[cache_key]
        _emit(logger, f"[Step 5] deps.dev returned HTTP {response.status_code} for {artifact_id}:{version}")
        _TRANSITIVE_CACHE[cache_key] = json.dumps([])
        return _TRANSITIVE_CACHE[cache_key]
    except Exception:
        _emit(logger, f"[Step 5] deps.dev lookup failed for {group_id}:{artifact_id}:{version}")
        _TRANSITIVE_CACHE[cache_key] = json.dumps([])
        return _TRANSITIVE_CACHE[cache_key]


def _fetch_transitive_recursive(group_id, artifact_id, version, solver_constraints, depth=1, max_depth=2, visited=None):
    if visited is None:
        visited = set()
    key = (group_id, artifact_id, version)
    if key in visited or depth > max_depth:
        return []
    visited.add(key)

    t_deps = []
    if key in solver_constraints:
        t_deps = solver_constraints[key]
    else:
        try:
            t_raw = get_transitive_dependencies(group_id, artifact_id, version)
            t_deps = json.loads(t_raw)
        except Exception:
            t_deps = []
        solver_constraints[key] = t_deps

    all_deps = []
    for dep in t_deps:
        tg, ta, tv = dep.get("groupId"), dep.get("artifactId"), dep.get("version")
        scope = dep.get("scope", "compile")
        if scope not in ("compile", "runtime", None) or not tg or not ta or tv == "Managed":
            continue
        all_deps.append({"groupId": tg, "artifactId": ta, "version": tv, "depth": depth})
        all_deps.extend(_fetch_transitive_recursive(tg, ta, tv, solver_constraints, depth + 1, max_depth, visited))
    return all_deps


def build_library_resolutions(candidates: dict, solver_constraints: dict, max_depth: int = 2):
    full_dependency_tree = {}
    library_resolutions = {}

    for (g, a), versions in candidates.items():
        for v in versions:
            visited = set()
            deps = _fetch_transitive_recursive(g, a, v, solver_constraints, depth=1, max_depth=max_depth, visited=visited)
            full_dependency_tree[(g, a, v)] = deps
            root_cand = f"{a}:{v}"
            for dep in deps:
                key_con = (dep["groupId"], dep["artifactId"])
                tv_con = dep["version"]
                if key_con not in library_resolutions:
                    library_resolutions[key_con] = {}
                if tv_con not in library_resolutions[key_con]:
                    library_resolutions[key_con][tv_con] = set()
                library_resolutions[key_con][tv_con].add(root_cand)

    return full_dependency_tree, library_resolutions


def analyze_dependency_conflicts(library_resolutions: dict) -> list:
    conflict_edges = []
    for (g, a), version_map in library_resolutions.items():
        if len(version_map) > 1:
            versions = list(version_map.keys())
            for i in range(len(versions)):
                for j in range(i + 1, len(versions)):
                    v1, v2 = versions[i], versions[j]
                    for c1 in version_map[v1]:
                        for c2 in version_map[v2]:
                            if c1.split(":")[0] != c2.split(":")[0]:
                                conflict_edges.append({
                                    "conflict_on": f"{g}:{a}",
                                    "v1": v1, "v2": v2,
                                    "edge": (c1, c2),
                                })
    return conflict_edges


# ---------------------------------------------------------------------------
# Step 6: Z3 solver (with backtracking fallback)
# ---------------------------------------------------------------------------

def solve_with_z3(candidates: dict, solver_constraints: dict, max_solutions: int = 5):
    if not HAS_Z3:
        return None

    opt = Optimize()
    z3_vars = {}
    root_keys = [f"{g}:{a}" for g, a in candidates.keys()]

    for (g, a), versions in candidates.items():
        lib_key = f"{g}:{a}"
        for v in versions:
            var_name = f"{lib_key}=={v}"
            z3_vars[var_name] = Bool(var_name)

    for (g, a), versions in candidates.items():
        lib_key = f"{g}:{a}"
        var_list = [z3_vars[f"{lib_key}=={v}"] for v in versions]
        opt.add(Sum([If(v, 1, 0) for v in var_list]) == 1)

    for (rg, ra, rv), deps in solver_constraints.items():
        root_var_name = f"{rg}:{ra}=={rv}"
        if root_var_name not in z3_vars:
            continue
        root_var = z3_vars[root_var_name]
        for dep in deps:
            dep_key = f"{dep['groupId']}:{dep['artifactId']}"
            if dep_key in root_keys and dep.get("version") != "Managed":
                dep_var_name = f"{dep_key}=={dep['version']}"
                if dep_var_name in z3_vars:
                    opt.add(Implies(root_var, z3_vars[dep_var_name]))
                else:
                    opt.add(Not(root_var))

    solutions = []
    while len(solutions) < max_solutions:
        if opt.check() == sat:
            model = opt.model()
            current = {}
            true_vars = []
            for var_name, z3_var in z3_vars.items():
                if is_true(model[z3_var]):
                    true_vars.append(z3_var)
                    lib, ver = var_name.split("==")
                    current[lib] = ver
            solutions.append(current)
            opt.add(Not(And(true_vars)))
        else:
            break
    return solutions


# ---------------------------------------------------------------------------
# Step 7: Runtime smoke test
# ---------------------------------------------------------------------------

def run_runtime_smoke_test(combo: dict, solver_constraints: dict, target_jdk: str = "17", logger=None) -> dict:
    if not _check_jdk_available():
        return {"status": "SKIP", "reason": "JDK not available"}

    jar_paths = []
    all_libs = set()
    for lib_key, version in combo.items():
        if isinstance(lib_key, tuple):
            g, a = lib_key
        else:
            g, a = lib_key.split(":")
        all_libs.add((g, a, version))
        t_deps = solver_constraints.get((g, a, version), [])
        for t in t_deps:
            if t.get("version") != "Managed":
                all_libs.add((t["groupId"], t["artifactId"], t["version"]))

    for g, a, v in all_libs:
        p = prepare_jar_for_check(g, a, v, cache_dir="./runtime_test_jars", logger=logger)
        if p:
            jar_paths.append(p)

    cp_sep = ";" if platform.system() == "Windows" else ":"
    classpath = cp_sep.join(jar_paths)

    classes_to_test = []
    for lib_key, version in combo.items():
        if isinstance(lib_key, tuple):
            g, a = lib_key
        else:
            g, a = lib_key.split(":")
        p = os.path.abspath(os.path.join("./runtime_test_jars", f"{a}-{version}.jar"))
        if os.path.exists(p):
            try:
                with zipfile.ZipFile(p) as z:
                    for n in z.namelist():
                        if n.endswith(".class") and "$" not in n and n != "module-info.class":
                            classes_to_test.append(n.replace("/", ".").replace(".class", ""))
                            if len(classes_to_test) >= 5:
                                break
            except Exception:
                continue

    if not classes_to_test:
        return {"status": "SKIP", "reason": "No testable classes found"}

    java_array = ", ".join(f'"{c}"' for c in classes_to_test[:5])
    java_code = f"""
public class RuntimeSmokeTest {{
    public static void main(String[] args) {{
        String[] classes = new String[] {{ {java_array} }};
        int loaded = 0;
        try {{
            for (String c : classes) {{
                try {{
                    Class.forName(c, true, RuntimeSmokeTest.class.getClassLoader());
                    loaded++;
                }} catch (Exception e) {{}}
            }}
            System.out.println("[JVM] Loaded " + loaded + " classes. PASS!");
        }} catch (NoClassDefFoundError | NoSuchMethodError | NoSuchFieldError err) {{
            System.err.println("[JVM ERROR] " + err.toString());
            System.exit(1);
        }}
    }}
}}"""
    stub = "RuntimeSmokeTest.java"
    try:
        _emit(logger, f"[Step 7] Compiling RuntimeSmokeTest.java against {len(jar_paths)} JAR(s)")
        with open(stub, "w", encoding="utf-8") as f:
            f.write(java_code)
        c_res = subprocess.run(["javac", "-cp", classpath, "--release", target_jdk, stub], capture_output=True, text=True, timeout=15)
        if c_res.returncode != 0:
            return {"status": "FAIL", "stage": "Compile", "error": c_res.stderr}
        run_cp = f".{cp_sep}{classpath}"
        _emit(logger, f"[Step 7] Running RuntimeSmokeTest with {len(classes_to_test[:5])} class probes")
        r_res = subprocess.run(["java", "-cp", run_cp, "RuntimeSmokeTest"], capture_output=True, text=True, timeout=15)
        if r_res.returncode == 0:
            return {"status": "PASS", "log": r_res.stdout.strip()}
        return {"status": "FAIL", "stage": "Runtime", "error": r_res.stderr.strip()}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
    finally:
        for f in [stub, stub.replace(".java", ".class")]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Entry point: lightweight index (for Reader)
# ---------------------------------------------------------------------------

def _detect_framework(dependencies: list) -> str:
    has_spring_boot = False
    has_spring = False
    has_sonar = False
    has_jakarta = False
    has_javax = False
    for dep in dependencies:
        g = dep.get("groupId", "").lower() if dep.get("groupId") else ""
        a = dep.get("artifactId", "").lower() if dep.get("artifactId") else ""
        if "spring-boot" in a or "spring-boot" in g:
            has_spring_boot = True
        elif "spring" in g or "spring" in a:
            has_spring = True
        elif "sonar-plugin-api" in a or "sonarqube" in g or "sonar" in g:
            has_sonar = True
        elif g.startswith("jakarta."):
            has_jakarta = True
        elif g.startswith("javax."):
            has_javax = True
    if has_sonar:
        return "SonarQube Plugin"
    if has_spring_boot:
        return "Spring Boot"
    if has_spring:
        return "Spring Framework"
    if has_jakarta:
        return "Jakarta EE"
    if has_javax:
        return "Java EE"
    return "Standard Java"

def _classify_project(pom_data: dict, jdeprscan_report: dict, jdk_target: str) -> str:
    dependencies = pom_data.get("dependencies", [])
    properties = pom_data.get("properties", {})
    
    # Red checks: sonar version
    sonar_version_str = properties.get("sonar.version", "")
    if sonar_version_str:
        try:
            major = int(sonar_version_str.split(".")[0])
            if major < 9:
                return "Red"
        except ValueError:
            pass
            
    for dep in dependencies:
        g = dep.get("groupId", "").lower() if dep.get("groupId") else ""
        a = dep.get("artifactId", "").lower() if dep.get("artifactId") else ""
        v = dep.get("version", "") if dep.get("version") else ""
        if "sonar-plugin-api" in a or "sonar-plugin-api" in g:
            try:
                major = int(v.split(".")[0])
                if major < 9:
                    return "Red"
            except (ValueError, IndexError):
                pass
        if "spring-boot" in a or "spring-boot" in g:
            try:
                parts = [int(p) for p in re.findall(r"\d+", v)[:2]]
                if len(parts) >= 2:
                    major, minor = parts
                    if major < 2 or (major == 2 and minor < 5):
                        return "Red"
            except Exception:
                pass
                
    # Yellow checks: jdeprscan report
    if jdeprscan_report:
        status = jdeprscan_report.get("status")
        b1_compile = jdeprscan_report.get("steps", {}).get("b1_compile", {})
        if status in ("PARTIAL", "FAIL") or b1_compile.get("status") == "FAIL":
            return "Yellow"
        summary = jdeprscan_report.get("summary", {})
        proj_for_removal = summary.get("project_code", {}).get("for_removal_count", 0)
        deps_for_removal = summary.get("dependencies", {}).get("critical_count", 0)
        if proj_for_removal > 0 or deps_for_removal > 0:
            return "Yellow"
        return "Green"
        
    return "Yellow"  # No jdeprscan report yet

def _get_project_properties(project_dir: Path) -> dict:
    pom_path = project_dir / "pom.xml"
    pom_data = {"properties": {}, "dependencies": []}
    jdk_target = "8"
    build_system = "unknown"
    
    if pom_path.exists():
        build_system = "Maven"
        try:
            pom_data = _parse_pom(pom_path)
            properties = pom_data.get("properties", {})
            for key in ["maven.compiler.target", "maven.compiler.source", "java.version", "target.jvm"]:
                if key in properties:
                    jdk_target = properties[key]
                    break
            if jdk_target == "8":
                try:
                    content = pom_path.read_text(encoding="utf-8")
                    match = re.search(r"<target>([^<]+)</target>", content)
                    if match:
                        jdk_target = match.group(1).strip()
                    else:
                        match = re.search(r"<source>([^<]+)</source>", content)
                        if match:
                            jdk_target = match.group(1).strip()
                except Exception:
                    pass
        except Exception as e:
            print(f"Warning: Failed to parse POM {pom_path}: {e}")
    elif (project_dir / "build.gradle").exists() or (project_dir / "build.gradle.kts").exists():
        build_system = "Gradle"
        for name in ("build.gradle", "build.gradle.kts"):
            p = project_dir / name
            if p.exists():
                try:
                    content = p.read_text(encoding="utf-8")
                    match = re.search(r"targetCompatibility\s*=\s*['\"]?(\d+(?:\.\d+)?)['\"]?", content)
                    if match:
                        jdk_target = match.group(1).strip()
                        break
                    match = re.search(r"sourceCompatibility\s*=\s*['\"]?(\d+(?:\.\d+)?)['\"]?", content)
                    if match:
                        jdk_target = match.group(1).strip()
                        break
                except Exception:
                    pass
    elif (project_dir / "build.xml").exists():
        build_system = "Ant"

    java_file_count = len(list(project_dir.rglob("*.java")))
    framework = _detect_framework(pom_data.get("dependencies", []))
    
    # Reports check
    jdeprscan_report = None
    jdeprscan_report_path = None
    for folder in ("test/artifacts", "target"):
        p = project_dir / folder / "jdeprscan_report.json"
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    jdeprscan_report = json.load(f)
                    jdeprscan_report_path = str(p)
                break
            except Exception:
                pass
                
    migration_report_path = None
    for folder in ("test/artifacts", "target"):
        p = project_dir / folder / "migration_report.md"
        if p.exists():
            migration_report_path = str(p)
            break
            
    existing_reports = {}
    if jdeprscan_report_path:
        existing_reports["jdeprscan"] = {
            "path": jdeprscan_report_path,
            "status": jdeprscan_report.get("status") if jdeprscan_report else "unknown",
            "summary": jdeprscan_report.get("summary") if jdeprscan_report else {}
        }
    if migration_report_path:
        existing_reports["migration_report"] = {
            "path": migration_report_path
        }
        
    classification = _classify_project(pom_data, jdeprscan_report, jdk_target)
    
    return {
        "build_system": build_system,
        "jdk_target": jdk_target,
        "java_file_count": java_file_count,
        "framework": framework,
        "existing_reports": existing_reports,
        "classification": classification,
        "pom_data": pom_data,
        "dependencies": pom_data.get("dependencies", [])
    }

def index_java_project(project_path: str) -> dict:
    """Index a codebase and parse POM — lightweight, no network calls."""
    index_raw = index_codebase(project_path)
    index_data = json.loads(index_raw)

    if "error" in index_data:
        return {"status": "error", "project_path": project_path, "message": index_data["error"]}

    project_root = Path(index_data["project_path"])
    project_type = index_data.get("project_type", "unknown")
    manifest_files = index_data.get("manifest_files", [])

    # Check if this is a multi-project directory or a single project
    has_root_manifest = (
        (project_root / "pom.xml").exists()
        or (project_root / "build.gradle").exists()
        or (project_root / "build.gradle.kts").exists()
        or (project_root / "build.xml").exists()
    )

    if not has_root_manifest:
        # Check subdirectories
        sub_projects_info = []
        for sub in sorted(project_root.iterdir()):
            if sub.is_dir() and not sub.name.startswith('.'):
                if (
                    (sub / "pom.xml").exists()
                    or (sub / "build.gradle").exists()
                    or (sub / "build.gradle.kts").exists()
                    or (sub / "build.xml").exists()
                ):
                    props = _get_project_properties(sub)
                    props["name"] = sub.name
                    props["path"] = str(sub.resolve())
                    sub_projects_info.append(props)

        if sub_projects_info:
            # Build Markdown summary table of all projects
            markdown_table = [
                "| Project | Build System | JDK Target | Java Files | Framework | Reports Status | Classification |",
                "| --- | --- | --- | --- | --- | --- | --- |"
            ]
            for p in sub_projects_info:
                rep_status = "None"
                j_rep = p.get("existing_reports", {}).get("jdeprscan")
                if j_rep:
                    rep_status = f"jdeprscan: {j_rep.get('status')}"
                    summary = j_rep.get("summary", {})
                    rem = summary.get("project_code", {}).get("for_removal_count", 0)
                    dep = summary.get("project_code", {}).get("deprecated_count", 0)
                    if rem > 0 or dep > 0:
                        rep_status += f" ({rem} forRemoval, {dep} deprecated)"
                
                markdown_table.append(
                    f"| `{p['name']}` | {p['build_system']} | {p['jdk_target']} | {p['java_file_count']} | {p['framework']} | {rep_status} | **{p['classification']}** |"
                )
            
            overview_md = "\n".join(markdown_table)
            
            # Aggregate dependencies, filtering out internal sub-project cross-dependencies
            all_dependencies = []
            sub_project_coords = {(p.get("project", {}).get("groupId"), p.get("project", {}).get("artifactId")) for p in sub_projects_info if p.get("project")}
            for p in sub_projects_info:
                for dep in p.get("dependencies", []):
                    if (dep.get("groupId"), dep.get("artifactId")) in sub_project_coords:
                        continue
                    if not any(d.get("groupId") == dep.get("groupId") and d.get("artifactId") == dep.get("artifactId") for d in all_dependencies):
                        all_dependencies.append(dep)
            
            scan_report_data = {
                "status": "ok",
                "project_path": str(project_root),
                "project_type": "java",
                "is_multi_project": True,
                "projects": sub_projects_info,
                "dependencies": all_dependencies,
                "markdown_report": overview_md,
                "index_summary": {
                    "project_type": "java",
                    "is_multi_project": True,
                    "project_count": len(sub_projects_info),
                    "projects": [p["name"] for p in sub_projects_info]
                }
            }
            
            # Write scan reports to artifacts folder
            try:
                artifacts_dir = Path(project_path) / "test" / "artifacts"
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                with open(artifacts_dir / "reader_scan_report.json", "w", encoding="utf-8") as f:
                    json.dump(scan_report_data, f, ensure_ascii=False, indent=2, default=str)
                with open(artifacts_dir / "reader_scan_report.md", "w", encoding="utf-8") as f:
                    f.write(scan_report_data.get("markdown_report", ""))
            except Exception as e:
                print(f"Warning: Failed to write reader scan reports: {e}")

            return scan_report_data

    # Fallback/Default: Single project scan
    if not _has_java_manifest(manifest_files):
        return {
            "status": "unsupported",
            "project_path": str(project_root),
            "project_type": project_type,
            "message": "No Java build manifest found.",
            "index_summary": _summarize_index(index_data),
        }

    pom_path = _find_root_manifest(project_root)
    if pom_path is None:
        return {"status": "error", "message": "Java project detected but no pom.xml found."}

    pom_data = _parse_pom(pom_path)

    # Analyze project structure and parse submodules using MavenProject
    from src.tools.maven.maven_project import MavenProject
    project = MavenProject(str(pom_path))
    
    modules_data = {}
    
    # Filter out internal module dependencies (e.g. submodules of the same project)
    internal_group = pom_data.get("project", {}).get("groupId")
    internal_artifacts = {pom_data.get("project", {}).get("artifactId")}
    if project.is_multi_module():
        internal_artifacts.update(project.get_modules())
        for mod in project.get_modules():
            internal_artifacts.add(mod.split('/')[-1])
            
    all_dependencies = [
        d for d in pom_data.get("dependencies", [])
        if not (d.get("groupId") == internal_group and d.get("artifactId") in internal_artifacts)
    ]
    
    if project.is_multi_module():
        modules = project.get_modules()
        for mod in modules:
            mod_pom_path = Path(os.path.dirname(str(pom_path))) / mod / "pom.xml"
            if mod_pom_path.exists():
                try:
                    mod_data = _parse_pom(mod_pom_path)
                    modules_data[mod] = mod_data
                    for dep in mod_data.get("dependencies", []):
                        if dep.get("groupId") == internal_group and dep.get("artifactId") in internal_artifacts:
                            continue
                        if not any(d.get("groupId") == dep.get("groupId") and d.get("artifactId") == dep.get("artifactId") for d in all_dependencies):
                            all_dependencies.append(dep)
                except Exception as e:
                    print(f"Warning: Failed to parse POM for module {mod}: {e}")

    # Analyze Java packages and file distribution
    source_files = index_data.get("source_files", [])
    java_files = [f.get("path") for f in source_files if f.get("language") == "java"]
    
    package_distribution = {}
    for f_path in java_files:
        dir_name = os.path.dirname(f_path).replace("\\", "/")
        package_distribution[dir_name] = package_distribution.get(dir_name, 0) + 1
        
    project_structure = {
        "is_multi_module": project.is_multi_module(),
        "modules": project.get_modules() if project.is_multi_module() else [],
        "java_file_count": len(java_files),
        "package_distribution": package_distribution,
    }

    # Extract single project props
    props = _get_project_properties(project_root)
    props["name"] = project_root.name
    props["path"] = str(project_root.resolve())
    
    # Build single project markdown table/overview
    markdown_table = [
        "| Project | Build System | JDK Target | Java Files | Framework | Reports Status | Classification |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]
    rep_status = "None"
    j_rep = props.get("existing_reports", {}).get("jdeprscan")
    if j_rep:
        rep_status = f"jdeprscan: {j_rep.get('status')}"
        summary = j_rep.get("summary", {})
        rem = summary.get("project_code", {}).get("for_removal_count", 0)
        dep = summary.get("project_code", {}).get("deprecated_count", 0)
        if rem > 0 or dep > 0:
            rep_status += f" ({rem} forRemoval, {dep} deprecated)"
            
    markdown_table.append(
        f"| `{props['name']}` | {props['build_system']} | {props['jdk_target']} | {props['java_file_count']} | {props['framework']} | {rep_status} | **{props['classification']}** |"
    )
    overview_md = "\n".join(markdown_table)

    scan_report_data = {
        "status": "ok",
        "pipeline": "reader-index",
        "project_path": str(project_root),
        "project_type": project_type,
        "pom_data": pom_data,
        "modules_pom_data": modules_data,
        "dependencies": all_dependencies,
        "project_structure": project_structure,
        "index_summary": _summarize_index(index_data),
        "is_multi_project": False,
        "project_info": props,
        "markdown_report": overview_md
    }

    # Write scan reports to artifacts folder
    try:
        artifacts_dir = Path(project_path) / "test" / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        with open(artifacts_dir / "reader_scan_report.json", "w", encoding="utf-8") as f:
            json.dump(scan_report_data, f, ensure_ascii=False, indent=2, default=str)
        with open(artifacts_dir / "reader_scan_report.md", "w", encoding="utf-8") as f:
            f.write(scan_report_data.get("markdown_report", ""))
    except Exception as e:
        print(f"Warning: Failed to write reader scan reports: {e}")

    return scan_report_data


# ---------------------------------------------------------------------------
# Entry point: full B1-B7 pipeline (for Architect)
# ---------------------------------------------------------------------------

def run_upgrade_pipeline(dependencies: list, target_java: str = "17", max_versions: int = 3, max_solutions: int = 3, logger=None) -> dict:
    """Run the full 7-step pipeline to find compatible dependency combinations."""
    root_deps = [d for d in dependencies if d.get("scope") in ("compile", "runtime", None) or d.get("version") != "Managed"]
    if not root_deps:
        return {"status": "error", "message": "No compatible dependencies found."}

    jdk_available = _check_jdk_available()

    # Steps 1-3: fetch, filter, static check
    solver = DependencySolver(target_java, logger=logger)
    
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for dep in root_deps:
            g = dep.get("groupId", "")
            a = dep.get("artifactId", "")
            if g and a:
                futures.append(executor.submit(solver.add_library, g, a, max_versions))
        concurrent.futures.wait(futures)

    inject_constrained_versions(solver)

    # Step 4: compile check (only if JDK available)
    if jdk_available:
        solver.run_step4()

    # Step 5: transitive constraint modeling
    full_tree, lib_resolutions = build_library_resolutions(solver.candidates, solver.constraints)
    conflict_edges = analyze_dependency_conflicts(lib_resolutions)

    # Step 6: Z3 solver (fallback to backtracking if z3 unavailable)
    z3_solutions = None
    if HAS_Z3:
        z3_solutions = solve_with_z3(solver.candidates, solver.constraints, max_solutions)

    # Backtracking solver (always runs as baseline)
    solver.solve()
    backtrack_solutions = solver.solutions

    # Choose best solutions: prefer Z3, fall back to backtracking
    if z3_solutions:
        chosen_solutions = z3_solutions
        solver_method = "z3"
    elif backtrack_solutions:
        chosen_solutions = [
            {f"{g}:{a}": v for (g, a), v in sol.items()}
            for sol in backtrack_solutions
        ]
        solver_method = "backtracking"
    else:
        chosen_solutions = []
        solver_method = "none"

    # Step 7: runtime smoke test for top 3 solutions
    smoke_results = []
    if jdk_available and chosen_solutions:
        for sol in chosen_solutions[:3]:
            # Adapt key format for smoke test
            adapted = {}
            for k, v in sol.items():
                if isinstance(k, tuple):
                    adapted[k] = v
                else:
                    parts = k.split(":")
                    adapted[(parts[0], parts[1]) if len(parts) == 2 else k] = v
            result = run_runtime_smoke_test(adapted, solver.constraints, target_java, logger=logger)
            smoke_results.append({"solution": sol, "result": result})
    elif not jdk_available:
        smoke_results = [{"solution": {}, "result": {"status": "SKIP", "reason": "JDK not available"}}]

    # Format candidates for output
    candidates_out = {}
    for (g, a), versions in solver.candidates.items():
        candidates_out[f"{g}:{a}"] = versions

    return {
        "status": "ok",
        "pipeline": "full-7-step",
        "target_java": target_java,
        "jdk_available": jdk_available,
        "candidates": candidates_out,
        "conflict_edges": conflict_edges,
        "solver_method": solver_method,
        "solutions": chosen_solutions[:max_solutions],
        "smoke_test_results": smoke_results,
        "step3_reports": {
            f"{g}:{a}:{v}": r.get("step3", {})
            for (g, a, v), r in solver.reports.items()
        },
        "step4_available": jdk_available,
    }


# ---------------------------------------------------------------------------
# Backward-compatible wrapper
# ---------------------------------------------------------------------------

def build_java_upgrade_report(project_path: str, target_java: str = "17") -> dict:
    """Full upgrade report — indexes codebase then runs pipeline."""
    index_result = index_java_project(project_path)

    if index_result.get("status") != "ok":
        return index_result

    pipeline_result = run_upgrade_pipeline(
        index_result.get("dependencies", []),
        target_java=target_java,
    )

    pipeline_result["project_path"] = index_result["project_path"]
    pipeline_result["project_type"] = index_result["project_type"]
    pipeline_result["pom_data"] = index_result.get("pom_data", {})
    pipeline_result["index_summary"] = index_result.get("index_summary", {})

    # Visualization
    visualizations: List[str] = []
    candidates = pipeline_result.get("candidates", {})
    if candidates:
        project_name = Path(project_path).name
        for mode in ("conservative", "balanced", "modern"):
            graph_path = _render_dependency_graph(project_path, {
                "name": mode,
                "dependencies": [
                    {"groupId": lib_key.split(":")[0], "artifactId": lib_key.split(":")[1] if ":" in lib_key else lib_key, "version": vs[0], "chosen_version": vs[0], "upgrade_type": "unchanged"}
                    for lib_key, vs in candidates.items() if mode == "balanced" and vs
                ] if mode == "balanced" else [],
                "score": 0,
            })
            if mode == "balanced":
                visualizations.append(str(graph_path))

    # Determine best solution
    best = {}
    solutions = pipeline_result.get("solutions", [])
    smoke_results = pipeline_result.get("smoke_test_results", [])
    if solutions:
        # Prefer solutions that pass smoke test
        passed = [s for s in smoke_results if s.get("result", {}).get("status") == "PASS"]
        if passed:
            best = passed[0].get("solution", {})
        else:
            best = solutions[0] if isinstance(solutions[0], dict) else {}

    pipeline_result["best_solution"] = best
    pipeline_result["visualizations"] = visualizations

    return pipeline_result


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def _render_dependency_graph(project_path: str, plan: dict) -> Path:
    project_name = Path(project_path).name
    report_root = Path(project_path) / "test" / "artifacts"
    graph_dir = report_root / "dependency_graphs"
    graph_dir.mkdir(parents=True, exist_ok=True)

    graph = nx.DiGraph()
    root_id = f"{project_name}:root"
    graph.add_node(root_id, label=f"{project_name}\nroot")

    for dependency in plan.get("dependencies", []):
        node_id = f"{dependency.get('groupId')}:{dependency.get('artifactId')}"
        current_version = dependency.get("version", "Managed")
        chosen_version = dependency.get("chosen_version", current_version)
        upgrade_type = dependency.get("upgrade_type", "unchanged")

        color_map = {"same-major": "#7bd389", "major-upgrade": "#f2c14e", "downgrade": "#e76f51", "managed": "#9aa0a6"}
        color = color_map.get(upgrade_type, "#c4f0c2")
        label = f"{dependency.get('artifactId')}\n{current_version} -> {chosen_version}"
        graph.add_node(node_id, label=label, color=color)
        graph.add_edge(root_id, node_id)

    plt.figure(figsize=(13, 9))
    pos = nx.spring_layout(graph, seed=42, k=0.85)
    node_colors = [graph.nodes[n].get("color", "#c4f0c2") for n in graph.nodes()]
    labels = {n: graph.nodes[n].get("label", n) for n in graph.nodes()}
    nx.draw_networkx_nodes(graph, pos, node_color=node_colors, node_size=2200, edgecolors="#2f3e46")
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=9, font_weight="bold")
    nx.draw_networkx_edges(graph, pos, arrows=True, arrowstyle="->", arrowsize=18, width=1.8)
    plt.title(f"{project_name} - {plan.get('name', 'dependency plan')}", fontsize=14, fontweight="bold")
    plt.axis("off")
    plt.tight_layout()

    output_path = graph_dir / f"{plan.get('name', 'plan')}.png"
    plt.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close()
    return output_path
