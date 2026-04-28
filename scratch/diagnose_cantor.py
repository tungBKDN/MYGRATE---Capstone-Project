from src.tools.dependency_analyzer import parse_maven_dependencies, list_all_versions, check_java_compatibility
import json

project_path = "freshbrew_data/cantor/pom.xml"
print(f"--- PARSING POM ---")
deps_json = parse_maven_dependencies(project_path)
deps = json.loads(deps_json)
print(json.dumps(deps, indent=2))

for dep in deps.get('dependencies', []):
    g, a, v = dep['groupId'], dep['artifactId'], dep['version']
    print(f"\n--- ANALYZING {g}:{a} ---")
    
    # List versions
    versions_json = list_all_versions(g, a)
    versions = json.loads(versions_json)
    if "error" in versions:
        print(f"List Versions Error: {versions['error']}")
    else:
        print(f"Versions found (top 5): {versions[:5]}")
        
    # Check compatibility of current version
    comp_json = check_java_compatibility(g, a, v, "17")
    comp = json.loads(comp_json)
    print(f"Current version ({v}) compatibility: {comp['is_compatible']} (Detected JDK: {comp['detected_jdk']})")
    
    # Check compatibility of a newer version (e.g. 1.7.30 for slf4j)
    if a == 'slf4j-api':
        test_v = '1.7.30'
        comp_json = check_java_compatibility(g, a, test_v, "17")
        print(f"Newer version ({test_v}) compatibility: {json.loads(comp_json)['is_compatible']}")
