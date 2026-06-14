"""
jdeprscan pipeline — full 4-step JDK upgrade diagnostic.

B0: Maven resolve dependencies (with caching)
B1: Compile project with JDK 8 (conditional tools.jar)
B2: jdeprscan project JAR (JDK 17)
B3: jdeprscan each dependency JAR (multi-threaded)

Returns a structured dict that agents can use for decision-making.
No hardcoded project-specific strings — works with any Maven-based Java project.

Entry points:
    run_jdeprscan_pipeline()  — full B0-B3 analysis (for agents)
    scan_jar()                — scan a single JAR (utility)
    build_classpath()         — build classpath from JAR directory (utility)
"""

import concurrent.futures
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# JDK discovery
# ---------------------------------------------------------------------------

def find_jdk(home_hint: Optional[str] = None, version: Optional[int] = None) -> Optional[Path]:
    """Tìm JDK home directory.

    Args:
        home_hint: Đường dẫn trực tiếp đến JDK home (ưu tiên cao nhất).
        version: Major version cần tìm (8, 11, 17, 21...). Nếu None, tìm bất kỳ.

    Returns:
        Path đến JDK home, hoặc None nếu không tìm thấy.
    """
    # Ưu tiên hint trực tiếp
    if home_hint:
        p = Path(home_hint)
        if (p / "bin" / ("javac.exe" if os.name == "nt" else "javac")).exists():
            return p

    # Tìm qua JAVA_HOME
    java_home = os.getenv("JAVA_HOME")
    if java_home:
        p = Path(java_home)
        javac = p / "bin" / ("javac.exe" if os.name == "nt" else "javac")
        if javac.exists():
            if version is None or _jdk_version(p) == version:
                return p

    # Tìm trong thư mục phổ biến trên Windows
    if os.name == "nt":
        search_roots = [
            Path(os.getenv("ProgramFiles", "C:\\Program Files")) / "Java",
            Path(os.getenv("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Java",
            Path(os.getenv("LOCALAPPDATA", "")) / "Java",
        ]
        for root in search_roots:
            if not root.exists():
                continue
            for jdk_dir in sorted(root.glob("jdk*"), reverse=True):
                javac = jdk_dir / "bin" / "javac.exe"
                if javac.exists():
                    if version is None or _jdk_version(jdk_dir) == version:
                        return jdk_dir

    # Tìm trong PATH
    javac_in_path = shutil.which("javac")
    if javac_in_path:
        p = Path(javac_in_path).resolve().parent.parent
        if version is None or _jdk_version(p) == version:
            return p

    return None


def _jdk_version(jdk_home: Path) -> Optional[int]:
    """Lấy major version từ JDK home (đọc release file hoặc chạy java -version)."""
    release_file = jdk_home / "release"
    if release_file.exists():
        for line in release_file.read_text(errors="ignore").splitlines():
            if line.startswith("JAVA_VERSION="):
                ver_str = line.split("=", 1)[1].strip('"').strip("'")
                m = re.match(r"1\.(\d+)", ver_str)
                if m:
                    return int(m.group(1))
                digit = re.search(r"\d+", ver_str)
                return int(digit.group()) if digit else None

    # Fallback: chạy java -version
    java_bin = jdk_home / "bin" / ("java.exe" if os.name == "nt" else "java")
    if java_bin.exists():
        try:
            r = subprocess.run(
                [str(java_bin), "-version"],
                capture_output=True, text=True, timeout=10,
            )
            output = r.stderr + r.stdout
            m = re.search(r'"(\d+)(?:\.\d+)*"', output)
            if m:
                v = int(m.group(1))
                if v > 1:
                    return v
                m2 = re.search(r'"1\.(\d+)', output)
                return int(m2.group(1)) if m2 else None
        except Exception:
            pass
    return None


def find_jdeprscan(jdk17_home: Optional[Path] = None) -> Optional[str]:
    """Tìm jdeprscan executable."""
    if jdk17_home:
        for name in ("jdeprscan.exe", "jdeprscan"):
            candidate = jdk17_home / "bin" / name
            if candidate.exists():
                return str(candidate)

    direct = shutil.which("jdeprscan")
    if direct:
        return direct

    java_home = os.getenv("JAVA_HOME")
    if java_home:
        for name in ("jdeprscan.exe", "jdeprscan"):
            candidate = Path(java_home) / "bin" / name
            if candidate.exists():
                return str(candidate)

    return None


def find_maven() -> Optional[str]:
    """Tìm Maven executable (mvn hoặc mvn.cmd)."""
    mvn = shutil.which("mvn") or shutil.which("mvn.cmd")
    if mvn:
        return mvn

    local_maven = Path(os.getenv("LOCALAPPDATA", "")) / "Apache"
    if local_maven.exists():
        maven_dirs = sorted(local_maven.glob("apache-maven-*"), reverse=True)
        for maven_dir in maven_dirs:
            for name in ("mvn.cmd", "mvn"):
                candidate = maven_dir / "bin" / name
                if candidate.exists():
                    return str(candidate)
    return None


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def build_classpath(jar_dir: Path) -> tuple[list[str], str]:
    """Nối classpath từ thư mục JAR.

    Returns:
        (danh sách đường dẫn JAR, chuỗi classpath phân cách bằng ; hoặc :)
    """
    jars = sorted(str(p) for p in jar_dir.glob("*.jar"))
    sep = ";" if os.name == "nt" else ":"
    return jars, sep.join(jars)


def scan_jar(jdeprscan: str, jar_path: str, release: str = "17", timeout: int = 180) -> dict:
    """Chạy jdeprscan trên 1 JAR, trả dict kết quả.

    Args:
        jdeprscan: Đường dẫn đến jdeprscan executable.
        jar_path: Đường dẫn đến file JAR cần quét.
        release: JDK release target (mặc định "17").
        timeout: Thời gian tối đa (giây), mặc định 180.

    Returns:
        dict với keys: jar, total, for_removal, lines.
        total=-1 nghĩa là timeout.
    """
    try:
        r = subprocess.run(
            [jdeprscan, "--release", release, jar_path],
            capture_output=True, text=True, timeout=timeout,
        )
        raw = (r.stdout + r.stderr).strip()
        lines = raw.splitlines() if raw else []
        total = sum(1 for l in lines if "deprecated" in l.lower() or "forRemoval" in l.lower())
        for_removal = sum(1 for l in lines if "forRemoval=true" in l)
        return {"jar": Path(jar_path).name, "total": total, "for_removal": for_removal, "lines": lines}
    except subprocess.TimeoutExpired:
        return {"jar": Path(jar_path).name, "total": -1, "for_removal": -1, "lines": [f"TIMEOUT: jdeprscan quá {timeout}s"]}


def jar_prefix(name: str) -> str:
    """Tách prefix JAR name để gom nhóm ecosystem.

    "commons-lang3-3.2.1.jar" -> "commons-lang3"
    "hadoop-common-2.2.0.jar" -> "hadoop-common"
    "spring-core-5.0.jar" -> "spring-core"
    """
    base = name.rsplit(".jar", 1)[0]
    m = re.match(r"^(.+?)-(\d.*)", base)
    if m:
        return m.group(1).lower()
    return base.lower()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_jdeprscan_pipeline(
    project_path: str,
    target_release: str = "17",
    jdk8_home: Optional[str] = None,
    jdk17_home: Optional[str] = None,
    n_workers: Optional[int] = None,
    logger: Optional[Callable] = None,
) -> dict:
    """Chạy full jdeprscan pipeline B0-B3 cho một dự án Maven-based.

    Args:
        project_path: Đường dẫn đến thư mục gốc dự án (chứa pom.xml).
        target_release: JDK release target cho jdeprscan (mặc định "17").
        jdk8_home: Đường dẫn JDK 8 (tự detect nếu None).
        jdk17_home: Đường dẫn JDK 17 (tự detect nếu None).
        n_workers: Số luồng cho B3 multi-threaded scan (mặc định auto).
        logger: Callback function để log progress.

    Returns:
        dict có cấu trúc:
        {
            "status": "OK" | "PARTIAL" | "FAIL",
            "project_path": str,
            "target_release": str,
            "jdk8_home": str | None,
            "jdk17_home": str | None,
            "jdeprscan_path": str | None,
            "steps": {
                "b0_maven": {"status": ..., "jar_count": ..., "needs_tools_jar": ...},
                "b1_compile": {"status": ..., "class_count": ..., "jar_path": ...},
                "b2_project_scan": {"status": ..., "for_removal": [...], "deprecated": [...], ...},
                "b3_dep_scan": {"status": ..., "total_jars": ..., "problem_jars": [...], ...},
            },
            "summary": {
                "project_code": {"for_removal_count": int, "deprecated_count": int, "clean": bool},
                "dependencies": {"problem_count": int, "critical_count": int, "top_issues": [...]},
                "pom_xml": {"critical_deps": [...], "critical_count": int},
            },
            "errors": [str, ...],
        }
    """
    def log(msg: str):
        if logger:
            logger(msg)

    project = Path(project_path)
    errors = []
    steps = {}
    summary = {}

    # ── Khám phá JDK ──
    log("[jdeprscan] Khám phá JDK...")
    jdk8 = find_jdk(home_hint=jdk8_home, version=8)
    jdk17 = find_jdk(home_hint=jdk17_home, version=17)

    # Fallback nếu không tìm đúng version
    if jdk8 is None and jdk8_home:
        jdk8 = find_jdk(home_hint=jdk8_home)
    if jdk17 is None:
        jdk17 = find_jdk(version=17)
    if jdk17 is None and jdk17_home:
        jdk17 = find_jdk(home_hint=jdk17_home)

    jdeprscan_path = find_jdeprscan(jdk17)
    mvn = find_maven()

    log(f"[jdeprscan] JDK 8:  {jdk8}")
    log(f"[jdeprscan] JDK 17: {jdk17}")
    log(f"[jdeprscan] jdeprscan: {jdeprscan_path}")
    log(f"[jdeprscan] Maven: {mvn}")

    if not jdeprscan_path:
        errors.append("jdeprscan không tìm thấy — cần JDK 9+")
    if not jdk8:
        errors.append("JDK 8 không tìm thấy — cần để compile dự án cũ có jdk.tools")

    # ── B0: Maven resolve dependencies ──
    log("[jdeprscan] B0: Maven resolve dependencies...")
    b0 = _step_b0_maven(project, jdk8, mvn, logger=log)
    steps["b0_maven"] = b0

    # ── B1: Compile project ──
    log("[jdeprscan] B1: Compile project...")
    b1 = _step_b1_compile(project, jdk8, b0, logger=log)
    steps["b1_compile"] = b1

    # ── B2: jdeprscan project JAR ──
    log("[jdeprscan] B2: jdeprscan project JAR...")
    b2 = _step_b2_project_scan(jdeprscan_path, b1, target_release, logger=log)
    steps["b2_project_scan"] = b2

    # ── B3: jdeprscan dependencies ──
    log("[jdeprscan] B3: jdeprscan dependencies...")
    b3 = _step_b3_dep_scan(jdeprscan_path, b0, target_release, n_workers, logger=log)
    steps["b3_dep_scan"] = b3

    # ── Tổng hợp ──
    # Lớp 1: project code
    project_clean = b2.get("for_removal_count", 0) == 0 and b2.get("deprecated_count", 0) == 0
    summary["project_code"] = {
        "for_removal_count": b2.get("for_removal_count", 0),
        "deprecated_count": b2.get("deprecated_count", 0),
        "clean": project_clean,
    }

    # Lớp 2: dependencies
    problem_jars = b3.get("problem_jars", [])
    ranked = sorted(problem_jars, key=lambda s: (s["for_removal"], s["total"]), reverse=True)
    critical_deps = [s for s in ranked if s.get("for_removal", 0) > 0]
    summary["dependencies"] = {
        "problem_count": len(problem_jars),
        "critical_count": len(critical_deps),
        "top_issues": [
            {"jar": s["jar"], "for_removal": s["for_removal"], "total": s["total"]}
            for s in ranked[:5]
        ],
    }

    # Lớp 3: pom.xml — phân tích từ dữ liệu, không hardcode
    summary["pom_xml"] = {
        "critical_deps": [
            {"jar": s["jar"], "for_removal": s["for_removal"], "total": s["total"]}
            for s in critical_deps[:5]
        ],
        "critical_count": len(critical_deps),
    }

    # Overall status
    has_errors = bool(errors)
    partial = any(s.get("status") == "FAIL" for s in steps.values())
    overall = "FAIL" if has_errors else "PARTIAL" if partial else "OK"

    return {
        "status": overall,
        "project_path": str(project),
        "target_release": target_release,
        "jdk8_home": str(jdk8) if jdk8 else None,
        "jdk17_home": str(jdk17) if jdk17 else None,
        "jdeprscan_path": jdeprscan_path,
        "steps": steps,
        "summary": summary,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------

def _step_b0_maven(project: Path, jdk8: Optional[Path], mvn: Optional[str], logger=None) -> dict:
    """B0: Maven resolve dependencies với caching."""
    def log(msg):
        if logger:
            logger(msg)

    result = {"status": "SKIP", "jar_count": 0, "classpath_jars": [], "classpath": "", "needs_tools_jar": False, "dep_dir": None}

    if not mvn:
        log("[jdeprscan] B0: Maven không tìm thấy")
        # Thử fallback directory
        fallback = project / "target" / "dependency"
        if fallback.exists() and any(fallback.glob("*.jar")):
            jars, cp = build_classpath(fallback)
            result.update({"status": "OK", "jar_count": len(jars), "classpath_jars": jars, "classpath": cp, "dep_dir": str(fallback)})
        return result

    dep_dir = project / "target" / "dependency"
    pom_file = project / "pom.xml"
    env = os.environ.copy()
    if jdk8:
        env["JAVA_HOME"] = str(jdk8)

    # Cache check
    pom_mtime = pom_file.stat().st_mtime if pom_file.exists() else 0
    cache_marker = dep_dir / ".cache_pom_mtime"
    need_maven = True

    if dep_dir.exists() and any(dep_dir.glob("*.jar")):
        if cache_marker.exists():
            try:
                cached_mtime = float(cache_marker.read_text().strip())
                if cached_mtime >= pom_mtime:
                    n = len(list(dep_dir.glob("*.jar")))
                    log(f"[jdeprscan] B0: cache hit — {n} JARs, pom.xml không đổi")
                    need_maven = False
            except (ValueError, OSError):
                pass

    if need_maven:
        log("[jdeprscan] B0: đang resolve dependencies...")
        dep_result = subprocess.run(
            [mvn, "dependency:copy-dependencies",
             "-U",
             "-DincludeScope=test",
             f"-DoutputDirectory={dep_dir}",
             "-f", str(pom_file)],
            timeout=300, env=env, shell=(os.name == "nt"),
        )
        if dep_result.returncode == 0:
            dep_dir.mkdir(parents=True, exist_ok=True)
            cache_marker.write_text(str(pom_mtime))
            n = len(list(dep_dir.glob("*.jar")))
            log(f"[jdeprscan] B0: OK — {n} JARs")
        else:
            log(f"[jdeprscan] B0: Maven FAIL (exit code {dep_result.returncode})")
            result["status"] = "FAIL"
            return result

    # Build classpath
    if dep_dir.exists() and any(dep_dir.glob("*.jar")):
        jars, cp = build_classpath(dep_dir)
        result.update({"status": "OK", "jar_count": len(jars), "classpath_jars": jars, "classpath": cp, "dep_dir": str(dep_dir)})

    # Kiểm tra jdk.tools dependency — chỉ chèn tools.jar khi thực sự cần
    needs_tools_jar = False
    if mvn and pom_file.exists():
        list_result = subprocess.run(
            [mvn, "dependency:list", "-f", str(pom_file)],
            capture_output=True, text=True, timeout=120, env=env, shell=(os.name == "nt"),
        )
        if "jdk.tools" in list_result.stdout or "jdk.tools" in list_result.stderr:
            needs_tools_jar = True
            log("[jdeprscan] B0: jdk.tools dependency CÓ -> sẽ chèn tools.jar")
        else:
            log("[jdeprscan] B0: jdk.tools dependency KHÔNG -> bỏ qua tools.jar")
    elif result["classpath_jars"]:
        needs_tools_jar = any("jdk.tools" in j for j in result["classpath_jars"])

    result["needs_tools_jar"] = needs_tools_jar
    return result


def _step_b1_compile(project: Path, jdk8: Optional[Path], b0: dict, logger=None) -> dict:
    """B1: Compile project bằng JDK 8, đóng gói JAR."""
    def log(msg):
        if logger:
            logger(msg)

    result = {"status": "SKIP", "class_count": 0, "jar_path": None, "compile_cp": ""}

    if not jdk8:
        log("[jdeprscan] B1: JDK 8 không tìm thấy — skip compile")
        return result

    javac = jdk8 / "bin" / ("javac.exe" if os.name == "nt" else "javac")
    jar_tool = jdk8 / "bin" / ("jar.exe" if os.name == "nt" else "jar")
    tools_jar = jdk8 / "lib" / "tools.jar"

    if not javac.exists():
        log("[jdeprscan] B1: javac không tồn tại")
        result["status"] = "FAIL"
        return result

    src_dir = project / "src" / "main" / "java"
    out_dir = project / "target" / "classes"
    out_dir.mkdir(parents=True, exist_ok=True)
    java_files = list(src_dir.rglob("*.java"))

    if not java_files:
        log("[jdeprscan] B1: Không tìm thấy .java files")
        result["status"] = "FAIL"
        return result

    # Build compile classpath
    compile_cp = b0.get("classpath", "")
    if b0.get("needs_tools_jar") and tools_jar.exists() and str(tools_jar) not in compile_cp:
        sep = ";" if os.name == "nt" else ":"
        compile_cp = compile_cp + sep + str(tools_jar) if compile_cp else str(tools_jar)
        log("[jdeprscan] B1: tools.jar added to classpath")

    result["compile_cp"] = compile_cp

    # Compile
    log(f"[jdeprscan] B1: compiling {len(java_files)} source files...")
    comp = subprocess.run(
        [str(javac), "-cp", compile_cp, "-d", str(out_dir)] + [str(f) for f in java_files],
        capture_output=True, text=True, timeout=120,
    )
    if comp.returncode == 0:
        n_class = len(list(out_dir.rglob("*.class")))
        log(f"[jdeprscan] B1: OK — {n_class} class files")
        result["status"] = "OK"
        result["class_count"] = n_class
    else:
        log(f"[jdeprscan] B1: Compile FAIL — {comp.stderr[:200]}")
        result["status"] = "FAIL"
        result["error"] = comp.stderr[:500]
        return result

    # Đóng gói JAR
    project_jar = project / "target" / f"{project.name}.jar"
    if out_dir.exists() and any(out_dir.rglob("*.class")):
        subprocess.run(
            [str(jar_tool), "cf", str(project_jar), "-C", str(out_dir), "."],
            capture_output=True, text=True,
        )
    result["jar_path"] = str(project_jar) if project_jar.exists() else None
    return result


def _step_b2_project_scan(jdeprscan_path: Optional[str], b1: dict, target_release: str, logger=None) -> dict:
    """B2: jdeprscan project JAR."""
    def log(msg):
        if logger:
            logger(msg)

    result = {"status": "SKIP", "for_removal": [], "deprecated": [], "for_removal_count": 0, "deprecated_count": 0}

    if not jdeprscan_path:
        log("[jdeprscan] B2: jdeprscan không tìm thấy — skip")
        return result

    project_jar = b1.get("jar_path")
    if not project_jar or not Path(project_jar).exists():
        log("[jdeprscan] B2: project JAR không có — skip")
        return result

    compile_cp = b1.get("compile_cp", "")
    cmd = [jdeprscan_path, "--release", target_release]
    if compile_cp:
        cmd.extend(["--class-path", compile_cp])
    cmd.append(str(project_jar))

    log(f"[jdeprscan] B2: scanning {Path(project_jar).name}...")
    try:
        scan_result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output = (scan_result.stdout + scan_result.stderr).strip()

        for_removal = []
        deprecated_only = []
        if output:
            for line in output.splitlines():
                if "forRemoval=true" in line:
                    for_removal.append(line.strip())
                elif "deprecated" in line.lower() or "uses deprecated" in line.lower():
                    deprecated_only.append(line.strip())

        result.update({
            "status": "OK",
            "for_removal": for_removal,
            "deprecated": deprecated_only,
            "for_removal_count": len(for_removal),
            "deprecated_count": len(deprecated_only),
        })
        log(f"[jdeprscan] B2: {len(for_removal)} forRemoval, {len(deprecated_only)} deprecated")
    except subprocess.TimeoutExpired:
        result["status"] = "FAIL"
        result["error"] = "jdeprscan timeout 120s"

    return result


def _step_b3_dep_scan(jdeprscan_path: Optional[str], b0: dict, target_release: str, n_workers: Optional[int], logger=None) -> dict:
    """B3: jdeprscan từng dependency JAR (multi-threaded)."""
    def log(msg):
        if logger:
            logger(msg)

    result = {"status": "SKIP", "total_jars": 0, "problem_jars": [], "clean_jars": 0, "timeout_jars": [], "ecosystems": {}}

    if not jdeprscan_path:
        log("[jdeprscan] B3: jdeprscan không tìm thấy — skip")
        return result

    dep_dir = b0.get("dep_dir")
    if not dep_dir or not Path(dep_dir).exists():
        log("[jdeprscan] B3: dependency directory không có — skip")
        return result

    scan_dir = Path(dep_dir)
    all_dep_jars = sorted(scan_dir.glob("*.jar"))
    total_jars = len(all_dep_jars)
    result["total_jars"] = total_jars

    if total_jars == 0:
        result["status"] = "OK"
        return result

    # Multi-threaded scan
    workers = n_workers or min(4, max(2, (os.cpu_count() or 4) // 2))
    log(f"[jdeprscan] B3: scanning {total_jars} JARs với {workers} luồng...")

    summary = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(scan_jar, jdeprscan_path, str(hj), target_release): hj.name
            for hj in all_dep_jars
        }
        for future in concurrent.futures.as_completed(future_map):
            info = future.result()
            summary.append(info)

    # Phân loại
    problem_jars = [s for s in summary if s["total"] > 0]
    timeout_jars = [s for s in summary if s["total"] == -1]
    clean_jars = [s for s in summary if s["total"] == 0]

    # Gom nhóm ecosystem tự động theo prefix JAR
    ecosystems = {}
    for s in problem_jars:
        prefix = jar_prefix(s["jar"])
        ecosystems.setdefault(prefix, []).append(s)

    # Sắp xếp ecosystem theo forRemoval giảm dần
    eco_sorted = sorted(
        ecosystems.items(),
        key=lambda kv: sum(s["for_removal"] for s in kv[1]),
        reverse=True,
    )
    ecosystems_ordered = {
        name: {
            "jars": [{"jar": s["jar"], "for_removal": s["for_removal"], "total": s["total"]} for s in members],
            "for_removal_total": sum(s["for_removal"] for s in members),
            "deprecated_total": sum(s["total"] for s in members),
        }
        for name, members in eco_sorted
    }

    result.update({
        "status": "OK",
        "problem_jars": problem_jars,
        "clean_jars": len(clean_jars),
        "timeout_jars": timeout_jars,
        "ecosystems": ecosystems_ordered,
    })

    log(f"[jdeprscan] B3: {len(problem_jars)} problem, {len(clean_jars)} clean, {len(timeout_jars)} timeout")
    return result