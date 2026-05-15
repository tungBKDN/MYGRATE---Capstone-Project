import json
import pytest
from src.tools.dependency_analyzer import resolve_best_combination

def test_resolve_best_combination_basic():
    # Attempt to resolve Spring Boot and JUnit
    deps = [
        {"groupId": "org.springframework.boot", "artifactId": "spring-boot-starter"},
        {"groupId": "junit", "artifactId": "junit"}
    ]
    result_json = resolve_best_combination(deps, target_java="17")
    result = json.loads(result_json)
    
    assert "recommended_combination" in result
    assert len(result["recommended_combination"]) == 2
    for item in result["recommended_combination"]:
        assert "version" in item
        assert item["version"] != "Unknown"

def test_resolve_best_combination_jdk_constraint():
    # Check if it avoids versions that require higher JDK
    # For example, Spring Boot 3.x requires JDK 17.
    # Let's try searching for a version of Spring Boot compatible with JDK 8.
    deps = [
        {"groupId": "org.springframework.boot", "artifactId": "spring-boot-starter"}
    ]
    result_json = resolve_best_combination(deps, target_java="8")
    result = json.loads(result_json)
    
    if "error" in result:
        # If no version found in top 50, that's also a valid outcome for this test
        assert "No compatible versions found" in result["error"]
    else:
        version = result["recommended_combination"][0]["version"]
        assert version.startswith("2.") # Should not pick 3.x for JDK 8
