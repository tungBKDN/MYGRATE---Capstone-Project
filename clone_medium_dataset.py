import os
import re
import subprocess
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
YAML_PATH = BASE_DIR / "org_medium_dataset.yaml"
DEST_DIR = BASE_DIR / "freshbrew_data"

def parse_yaml_repos(yaml_path: Path):
    if not yaml_path.exists():
        print(f"Error: {yaml_path} not found.")
        sys.exit(1)

    content = yaml_path.read_text(encoding="utf-8")
    repos = []
    
    # We can parse the YAML blocks using regex since the structure is consistent
    blocks = content.split("- commit:")
    for block in blocks:
        if not block.strip():
            continue
        
        # Extract commit
        commit_match = re.search(r"^ \s*([a-f0-9]+)", block)
        # Extract repo_name
        repo_match = re.search(r"repo_name:\s*(\S+)", block)
        
        if commit_match and repo_match:
            commit = commit_match.group(1).strip()
            repo_name = repo_match.group(1).strip()
            repos.append({"name": repo_name, "commit": commit})
            
    return repos

def main():
    repos = parse_yaml_repos(YAML_PATH)
    total = len(repos)
    print(f"Found {total} repositories to clone.")
    
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    
    for i, repo in enumerate(repos, 1):
        name = repo["name"]
        commit = repo["commit"]
        folder_name = name.split("/")[-1]
        target_path = DEST_DIR / folder_name

        # Check if the repo is already fetched
        if (target_path / ".git").exists():
            print(f"[{i}/{total}] {name} -> [SKIP] Already cloned at {target_path}")
            continue

        print(f"\n[{i}/{total}] {name}")
            
        print(f"  Cloning https://github.com/{name}.git ...")
        try:
            # Clone
            clone_res = subprocess.run(
                ["git", "clone", "--quiet", f"https://github.com/{name}.git", str(target_path)],
                capture_output=True,
                text=True
            )
            if clone_res.returncode != 0:
                print(f"  [FAIL] Clone failed: {clone_res.stderr.strip()}")
                continue
                
            # Checkout commit
            checkout_res = subprocess.run(
                ["git", "checkout", "--quiet", commit],
                cwd=str(target_path),
                capture_output=True,
                text=True
            )
            if checkout_res.returncode == 0:
                print(f"  [OK] Checked out commit {commit[:8]}")
            else:
                print(f"  [WARN] Checkout failed: {checkout_res.stderr.strip()}")
        except Exception as e:
            print(f"  [ERROR] Unexpected error: {e}")
            
    print("\n=== Done. ===")

if __name__ == "__main__":
    main()
