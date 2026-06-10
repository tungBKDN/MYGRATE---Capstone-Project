from __future__ import annotations

import os
from pathlib import Path
from src.tools import MavenPomEditor, MavenProject, MavenRunner


def test_maven_pom_editor(tmp_path: Path):
    # Create a dummy pom.xml
    pom_file = tmp_path / "pom.xml"
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>dummy-project</artifactId>
    <version>1.0.0</version>
    <properties>
        <java.version>1.8</java.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-api</artifactId>
            <version>1.7.30</version>
        </dependency>
    </dependencies>
</project>
"""
    pom_file.write_text(pom_content, encoding="utf-8")

    # Load editor
    editor = MavenPomEditor(str(pom_file))
    
    # Assert elements exist
    assert editor.element_exists("m:properties")
    assert editor.element_exists("m:dependencies/m:dependency")
    
    # Check dependency exists
    assert editor.dependency_exists("org.slf4j", "slf4j-api")
    assert not editor.dependency_exists("org.slf4j", "slf4j-simple")

    # Update dependency
    def update_func(dep_elem):
        version_elem = editor.ensure_element(dep_elem, "m:version")
        version_elem.text = "1.7.36"
    
    success = editor.update_dependency("org.slf4j", "slf4j-api", update_func)
    assert success
    
    # Add new dependency
    editor.add_dependency("com.google.guava", "guava", "30.1-jre", scope="compile")
    assert editor.dependency_exists("com.google.guava", "guava")
    
    # Check Java version property
    editor.ensure_property("java.version", "17")
    
    # Read modified pom content and check modifications
    updated_pom = MavenPomEditor(str(pom_file))
    assert updated_pom.dependency_exists("com.google.guava", "guava")
    
    # Find property value
    props = updated_pom.root.find("m:properties", namespaces=updated_pom.namespaces)
    java_version = props.find("m:java.version", namespaces=updated_pom.namespaces)
    assert java_version is not None
    assert java_version.text == "17"


def test_maven_project(tmp_path: Path):
    # Create single-module project pom.xml
    pom_file = tmp_path / "pom.xml"
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>dummy-project</artifactId>
    <version>1.0.0</version>
</project>
"""
    pom_file.write_text(pom_content, encoding="utf-8")

    project = MavenProject(str(pom_file))
    assert not project.is_multi_module()
    assert len(project.get_modules()) == 0
    
    poms = project.get_all_pom_paths()
    assert "root" in poms
    assert poms["root"] == str(pom_file.resolve())


def test_maven_runner():
    # We can't easily run full compile without maven in pytest environment,
    # but we can verify the runner commands initialization
    runner = MavenRunner(target_java_version="17")
    assert runner.target_java_version == "17"


def test_index_java_project(tmp_path: Path):
    from src.tools.maven_upgrade_tools import index_java_project
    
    # Create a multi-module structure
    root_pom = tmp_path / "pom.xml"
    root_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>root-project</artifactId>
    <version>1.0.0</version>
    <packaging>pom</packaging>
    <modules>
        <module>submodule-a</module>
    </modules>
</project>
"""
    root_pom.write_text(root_content, encoding="utf-8")
    
    submodule_dir = tmp_path / "submodule-a"
    submodule_dir.mkdir()
    
    submodule_pom = submodule_dir / "pom.xml"
    submodule_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.example</groupId>
        <artifactId>root-project</artifactId>
        <version>1.0.0</version>
    </parent>
    <artifactId>submodule-a</artifactId>
    <dependencies>
        <dependency>
            <groupId>org.slf4j</groupId>
            <artifactId>slf4j-api</artifactId>
            <version>1.7.36</version>
        </dependency>
    </dependencies>
</project>
"""
    submodule_pom.write_text(submodule_content, encoding="utf-8")
    
    # Create a dummy Java file inside submodule
    src_dir = submodule_dir / "src" / "main" / "java" / "com" / "example"
    src_dir.mkdir(parents=True)
    java_file = src_dir / "App.java"
    java_file.write_text("package com.example; public class App {}", encoding="utf-8")
    
    # Index the project
    result = index_java_project(str(tmp_path))
    
    assert result["status"] == "ok"
    assert "project_structure" in result
    struct = result["project_structure"]
    assert struct["is_multi_module"] is True
    assert "submodule-a" in struct["modules"]
    assert struct["java_file_count"] == 1
    
    # Verify aggregated dependencies
    deps = result["dependencies"]
    assert len(deps) == 1
    assert deps[0]["groupId"] == "org.slf4j"
    assert deps[0]["artifactId"] == "slf4j-api"
    assert deps[0]["version"] == "1.7.36"

