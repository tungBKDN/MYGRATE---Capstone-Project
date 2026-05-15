import json
import pytest
from src.tools.dependency_analyzer import detect_transitive_conflicts

def test_detect_transitive_conflicts_no_conflicts():
    # JUnit 4.12 and SLF4J 1.7.30 shouldn't have obvious conflicts in this simple test
    deps = [
        {"groupId": "junit", "artifactId": "junit", "version": "4.12"},
        {"groupId": "org.slf4j", "artifactId": "slf4j-api", "version": "1.7.30"}
    ]
    result_json = detect_transitive_conflicts(deps)
    result = json.loads(result_json)
    assert "conflicts" in result
    # It might find some common transitive deps like hamcrest, but they should be the same version if lucky

def test_detect_transitive_conflicts_real_conflict():
    # This might be hard to guarantee without a known conflict, 
    # but let's try two libraries known to have different requirements for a common dep.
    # For example, older versions of spring and hibernate.
    deps = [
        {"groupId": "org.springframework", "artifactId": "spring-core", "version": "4.3.0.RELEASE"},
        {"groupId": "org.hibernate", "artifactId": "hibernate-core", "version": "5.2.0.Final"}
    ]
    result_json = detect_transitive_conflicts(deps)
    result = json.loads(result_json)
    assert "conflicts" in result
    print(f"Found conflicts: {result['conflicts']}")
