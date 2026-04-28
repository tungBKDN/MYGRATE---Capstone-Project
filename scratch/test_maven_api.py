import requests
import json

def test_maven_query(group_id, artifact_id):
    url = f"https://search.maven.org/solrsearch/select?q=g:%22{group_id}%22+AND+a:%22{artifact_id}%22&core=gav&rows=10&wt=json"
    print(f"Testing URL: {url}")
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        docs = response.json().get('response', {}).get('docs', [])
        versions = [doc['v'] for doc in docs]
        print(f"Versions found: {versions}")
    else:
        print(f"Error: {response.text}")

print("--- Testing junit:junit ---")
test_maven_query("junit", "junit")
print("\n--- Testing slf4j-api ---")
test_maven_query("org.slf4j", "slf4j-api")
