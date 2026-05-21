import os
import sys
import json
import unittest
from pathlib import Path

# Setup path for local logic
sys.path.append(os.path.dirname(__file__))
from analyzer_logic import (
    parse_maven_dependencies, 
    check_java_compatibility, 
    list_all_versions, 
    detect_transitive_conflicts
)

def run_comprehensive_check():
    report = {
        "summary": {},
        "tests": []
    }
    
    # 1. Test POM Parsing with real data
    data_dir = Path("../../freshbrew_data").resolve()
    projects = ["cantor", "sonar-stash"]
    for p in projects:
        pom = data_dir / p / "pom.xml"
        try:
            res = json.loads(parse_maven_dependencies(str(pom)))
            success = "error" not in res
            report["tests"].append({
                "name": f"Parse POM: {p}",
                "status": "PASS" if success else "FAIL",
                "details": f"Project: {res.get('project', {}).get('artifactId')}" if success else res.get('error')
            })
        except Exception as e:
            report["tests"].append({"name": f"Parse POM: {p}", "status": "FAIL", "details": str(e)})

    # 2. Test Bytecode JDK Detection (The "New" Core Logic)
    # Testing a library that is known to be JDK 17 (Spring Boot 3.0.0)
    # and one that is JDK 8 (Guava 27)
    test_cases = [
        ("org.springframework.boot", "spring-boot", "3.0.0", "17"),
        ("com.google.guava", "guava", "27.0.1-jre", "8")
    ]
    
    for g, a, v, expected_jdk in test_cases:
        try:
            res = json.loads(check_java_compatibility(g, a, v, target_java="21"))
            bytecode_jdk = res.get("bytecode_jdk")
            success = bytecode_jdk == expected_jdk
            report["tests"].append({
                "name": f"Bytecode Check: {g}:{a}",
                "status": "PASS" if success else "FAIL",
                "details": f"Expected JDK {expected_jdk}, detected {bytecode_jdk}"
            })
        except Exception as e:
            report["tests"].append({"name": f"Bytecode Check: {g}:{a}", "status": "FAIL", "details": str(e)})

    # 3. Test Transitive Conflicts
    try:
        deps = [
            {"groupId": "com.google.guava", "artifactId": "guava", "version": "27.0.1-jre"},
            {"groupId": "org.asynchttpclient", "artifactId": "async-http-client", "version": "2.8.1"}
        ]
        res = json.loads(detect_transitive_conflicts(deps))
        success = "conflicts" in res
        report["tests"].append({
            "name": "Transitive Conflict Detection",
            "status": "PASS" if success else "FAIL",
            "details": f"Found {len(res.get('conflicts', []))} conflicts"
        })
    except Exception as e:
        report["tests"].append({"name": "Transitive Conflict Detection", "status": "FAIL", "details": str(e)})

    # Summary
    passed = len([t for t in report["tests"] if t["status"] == "PASS"])
    total = len(report["tests"])
    report["summary"] = {"passed": passed, "total": total, "rate": f"{(passed/total)*100:.1f}%"}
    
    return report

if __name__ == "__main__":
    results = run_comprehensive_check()
    
    with open("final_validation_report.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Validation complete. {results['summary']['passed']}/{results['summary']['total']} tests passed.")
