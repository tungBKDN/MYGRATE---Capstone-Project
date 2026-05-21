import os
import sys
import json
import unittest
from pathlib import Path

# Add src to path
root_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(root_dir / "src"))

# Import from local logic file
from analyzer_logic import (
    parse_maven_dependencies, 
    list_all_versions, 
    check_java_compatibility, 
    detect_transitive_conflicts,
    resolve_best_combination
)

class TestDependencyAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = root_dir / "freshbrew_data"
        if not cls.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found at {cls.data_dir}")

    def test_parse_cantor_pom(self):
        pom_path = self.data_dir / "cantor" / "pom.xml"
        result_json = parse_maven_dependencies(str(pom_path))
        data = json.loads(result_json)
        
        self.assertNotIn("error", data)
        self.assertEqual(data["project"]["artifactId"], "cantor")
        self.assertEqual(data["project"]["groupId"], "com.adroll.cantor")
        
        # Check dependencies
        deps = {d["artifactId"]: d for d in data["dependencies"]}
        self.assertIn("junit", deps)
        self.assertIn("slf4j-api", deps)
        self.assertIn("hadoop-common", deps)
        
        # Check property resolution
        hadoop_dep = deps["hadoop-common"]
        self.assertEqual(hadoop_dep["version"], "2.2.0") # ${hadoop.version} resolved

    def test_parse_sonar_stash_pom(self):
        pom_path = self.data_dir / "sonar-stash" / "pom.xml"
        result_json = parse_maven_dependencies(str(pom_path))
        data = json.loads(result_json)
        
        self.assertNotIn("error", data)
        self.assertEqual(data["project"]["artifactId"], "sonar-stash-plugin")
        
        # Check property resolution in dependencies
        deps = {d["artifactId"]: d for d in data["dependencies"]}
        self.assertEqual(deps["sonar-plugin-api"]["version"], "6.7") # ${sonar.version} resolved

    def test_list_versions(self):
        # Testing with a well-known library
        result_json = list_all_versions("org.slf4j", "slf4j-api")
        data = json.loads(result_json)
        self.assertIn("versions", data)
        self.assertTrue(len(data["versions"]) > 0)
        # Check for a more recent version that is likely in the top 50
        self.assertIn("2.0.16", data["versions"])

    def test_java_compatibility(self):
        # org.springframework.boot:spring-boot-starter:3.0.0 requires Java 17
        result_json = check_java_compatibility("org.springframework.boot", "spring-boot-starter", "3.0.0", "11")
        data = json.loads(result_json)
        self.assertEqual(data["is_compatible"], "No")
        
        result_json = check_java_compatibility("org.springframework.boot", "spring-boot-starter", "3.0.0", "17")
        data = json.loads(result_json)
        self.assertEqual(data["is_compatible"], "Yes")

    def test_conflict_detection(self):
        # Mock dependencies with known conflict
        # In a real scenario, we'd use get_transitive_dependencies but for unit test we can mock the input
        deps = [
            {"groupId": "com.google.guava", "artifactId": "guava", "version": "27.0.1-jre"},
            {"groupId": "org.asynchttpclient", "artifactId": "async-http-client", "version": "2.8.1"}
        ]
        # This might take time as it calls network. Let's just check if it runs without error.
        result_json = detect_transitive_conflicts(deps)
        data = json.loads(result_json)
        self.assertIn("conflicts", data)
        self.assertIn("summary", data)

if __name__ == "__main__":
    unittest.main()
