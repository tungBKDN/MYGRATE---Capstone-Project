import pytest
import os
import json
from src.tools.dependency_analyzer import (
    parse_maven_dependencies,
    list_all_versions,
    get_transitive_dependencies,
    check_java_compatibility,
    get_latest_version
)

def test_parse_maven_dependencies(tmp_path):
    pom_content = """<project xmlns="http://maven.apache.org/POM/4.0.0">
        <dependencies>
            <dependency>
                <groupId>junit</groupId>
                <artifactId>junit</artifactId>
                <version>4.11</version>
            </dependency>
        </dependencies>
    </project>"""
    pom_file = tmp_path / "pom.xml"
    pom_file.write_text(pom_content)
    
    result_json = parse_maven_dependencies(str(pom_file))
    result = json.loads(result_json)
    assert len(result) == 1
    assert result[0]['groupId'] == 'junit'
    assert result[0]['version'] == '4.11'

def test_list_all_versions_real():
    # Test with a known library
    result_json = list_all_versions("junit", "junit")
    result = json.loads(result_json)
    assert isinstance(result, list)
    assert len(result) > 0
    assert "4.12" in result

def test_list_all_versions_empty():
    # Test with non-existent library
    result_json = list_all_versions("non.existent", "artifact-x")
    result = json.loads(result_json)
    assert "error" in result
    assert "No versions found" in result["error"]

def test_get_transitive_dependencies_real():
    result_json = get_transitive_dependencies("org.slf4j", "slf4j-api", "1.7.30")
    result = json.loads(result_json)
    assert isinstance(result, list)
    # slf4j-api 1.7.30 usually has no direct compile dependencies in POM
    # but let's check a library that has them, like hadoop-common
    result_json_hadoop = get_transitive_dependencies("org.apache.hadoop", "hadoop-common", "2.7.0")
    result_hadoop = json.loads(result_json_hadoop)
    assert len(result_hadoop) > 0

def test_check_java_compatibility_real():
    result_json = check_java_compatibility("junit", "junit", "4.12", "17")
    result = json.loads(result_json)
    assert result['is_compatible'] in ["Yes", "No", "Maybe"]
    assert result['dependency'] == "junit:junit"

def test_get_latest_version_real():
    version = get_latest_version("junit", "junit")
    assert version != "Unknown"
    assert "." in version
