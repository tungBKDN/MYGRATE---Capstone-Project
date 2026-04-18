import subprocess
import os

# Danh sách 5 dự án mẫu (Tôi đã điền sẵn 2 cái đầu từ metadata của ông)
repos = [
    {"name": "AdRoll/cantor", "commit": "76b4e1b4fcca28e57e3a23cb6ea61fb428275442"},
    {"name": "AmadeusITGroup/sonar-stash", "commit": "924610151ea5408e077882f3cfc552e4f4a2c678"},
    # Ông copy thêm 3 cái nữa từ file metadata vào đây theo đúng format này nhé
]

base_dir = "freshbrew_data"
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

for repo in repos:
    repo_url = f"https://github.com/{repo['name']}.git"
    folder_name = repo['name'].split('/')[-1]
    target_path = os.path.join(base_dir, folder_name)

    print(f"\n>>> Đang xử lý: {repo['name']}")

    # 1. Clone repo
    subprocess.run(["git", "clone", repo_url, target_path])

    # 2. Checkout đúng commit để đảm bảo dữ liệu khớp metadata
    subprocess.run(["git", "checkout", repo['commit']], cwd=target_path)

print("\nDONE! 5 bộ dữ liệu đã nằm gọn trong thư mục freshbrew_data.")