from pathlib import Path
import xml.etree.ElementTree as ET

repo_path = Path(r"D:\capstone_project\MYGRATE---Capstone-Project\working\default\log4j2-elasticsearch")
print(f"Searching in: {repo_path}")

total_missed = 0
total_covered = 0
coverage_found = False

for jacoco_xml in repo_path.rglob("jacoco.xml"):
    parts = [p.lower() for p in jacoco_xml.parts]
    print(f"\nFound file: {jacoco_xml}")
    print(f"Parts: {parts}")
    
    if "jacoco-aggregate" in parts:
        print("-> Skipped because 'jacoco-aggregate' in parts")
        continue
    if "target" not in parts or "site" not in parts or "jacoco" not in parts:
        print(f"-> Skipped because target/site/jacoco conditions not met: target={ 'target' in parts }, site={ 'site' in parts }, jacoco={ 'jacoco' in parts }")
        continue
        
    print("-> Matches conditions!")
    try:
        tree = ET.parse(jacoco_xml)
        root = tree.getroot()
        for counter in root.findall("counter"):
            if counter.get("type") == "LINE":
                missed = int(counter.get("missed", 0))
                covered = int(counter.get("covered", 0))
                print(f"   LINE counter: missed={missed}, covered={covered}")
                total_missed += missed
                total_covered += covered
                coverage_found = True
                break
    except Exception as e:
        print(f"   Error parsing: {e}")

print(f"\nFinal: total_missed={total_missed}, total_covered={total_covered}, coverage_found={coverage_found}")
