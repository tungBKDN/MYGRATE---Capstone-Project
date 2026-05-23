import sys
sys.path.append('.')
from src.tools.dependency_analyzer import parse_maven_dependencies
print(parse_maven_dependencies('freshbrew_data/cantor/pom.xml'))
