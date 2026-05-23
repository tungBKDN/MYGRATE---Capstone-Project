from pathlib import Path
import json
import os
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]

# ensure repo root is in path
sys.path.append(str(REPO_ROOT))

from src.tools.project_indexer import find_main_build_file
from src.tools.dependency_analyzer import parse_maven_dependencies, get_latest_version, resolve_best_combination, detect_transitive_conflicts, get_compatible_versions
from src.tools.visualization_engine import generate_dashboard, generate_cross_matrix


def _resolve_project_root(target_root: str) -> Path:
    candidate = Path(target_root)
    if candidate.exists():
        return candidate.resolve()

    repo_candidate = (REPO_ROOT / target_root)
    if repo_candidate.exists():
        return repo_candidate.resolve()

    return candidate.resolve()


def run(target_root: str = 'freshbrew_data/cantor'):
    root = _resolve_project_root(target_root)
    print(f"Scanning project: {root}")

    main_build = find_main_build_file(str(root))
    if not main_build:
        print("No main build file found. Exiting.")
        return 1

    print(f"Found build file: {main_build}")
    # find_main_build_file returns a path relative to the project root; make absolute
    if not os.path.isabs(main_build):
        main_build_path = str(root.joinpath(main_build))
    else:
        main_build_path = main_build
    parsed = parse_maven_dependencies(main_build_path)
    try:
        parsed_obj = json.loads(parsed)
    except Exception as e:
        print("Failed to parse POM:", e)
        return 1

    deps = parsed_obj.get('dependencies', [])
    recommendations = {}

    for d in deps:
        g = d.get('groupId')
        a = d.get('artifactId')
        cur_v = d.get('version')
        if not g or not a:
            continue
        print(f"Processing {g}:{a} (current: {cur_v})")

        # get candidate compatible versions (fast heuristic)
        compat_json = get_compatible_versions(g, a, target_java="17")
        try:
            compat_obj = json.loads(compat_json)
            candidates = compat_obj.get('compatible_versions', [])
        except Exception:
            candidates = []

        # pick suggested_version as latest compatible or current if none
        suggested = candidates[0] if candidates else (cur_v or "unknown")
        action = "upgrade" if suggested != cur_v and suggested != "unknown" else "keep"

        # quick audit_log: check up to first 3 candidates
        audit_log = []
        for v in candidates[:3]:
            try:
                # call static check
                from src.tools.dependency_analyzer import check_java_compatibility
                res = check_java_compatibility(g, a, v, target_java="17")
                if isinstance(res, str):
                    res_obj = json.loads(res)
                else:
                    res_obj = res
                audit_log.append({"version": v, "status": res_obj.get('analysis', {}).get('compatibility_status'), "jdk": res_obj.get('signals', {}).get('bytecode_jdk'), "reason": res_obj.get('signals', {})})
            except Exception:
                audit_log.append({"version": v, "status": "Unknown"})

        recommendations[f"{g}:{a}"] = {
            "suggested_version": suggested,
            "action": action,
            "audit_log": audit_log,
            "score": 0.9 if action == 'upgrade' else 1.0,
            "reasoning": "Local static checks and heuristics"
        }

    # simple cross compatibility: detect transitive conflicts of the current deps
    cross = []
    conflicts_json = detect_transitive_conflicts(deps)
    try:
        conflicts_obj = json.loads(conflicts_json)
        for c in conflicts_obj.get('conflicts', []):
            cross.append({
                "lib1": f"{c['groupId']}:{c['artifactId']}",
                "lib2": "UNKNOWN",
                "status": "conflict",
                "reason": f"Multiple candidate versions: {c.get('versions')}"
            })
    except Exception:
        pass

    intelligence = {
        "recommendations": recommendations,
        "cross_compatibility": cross,
        "visualization_data": {"nodes": [], "edges": []}
    }

    out_path = REPO_ROOT / 'migration_intelligence.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(intelligence, f, indent=2)

    print(f"Wrote: {out_path}")

    # generate visualizations
    try:
        generate_dashboard(str(out_path), "dependency_graph.png")
        generate_cross_matrix(str(out_path), "cross_matrix.png")
    except Exception as e:
        print("Visualization failed:", e)

    return 0


if __name__ == '__main__':
    import sys
    tgt = sys.argv[1] if len(sys.argv) > 1 else 'freshbrew_data/cantor'
    sys.exit(run(tgt))
