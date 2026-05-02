import json
import os
import networkx as nx
import matplotlib.pyplot as plt

HAS_MATPLOTLIB = True

def generate_dashboard(intelligence_json_path: str, output_image_path: str = "dependency_graph.png"):
    if not os.path.exists(intelligence_json_path):
        print(f"[-] Error: Could not find {intelligence_json_path}")
        return

    if not HAS_MATPLOTLIB:
        print("[-] Vui lòng cài đặt matplotlib và networkx (pip install matplotlib networkx) để dùng tính năng này.")
        return

    with open(intelligence_json_path, 'r', encoding='utf-8') as f:
        intelligence = json.load(f)

    # Initialize Directed Graph
    G = nx.DiGraph()
    
    # Add Root Node
    G.add_node("Project Root", color="lightblue", size=3000)

    recommendations = intelligence.get("recommendations", {})
    
    colors = []
    sizes = []
    labels = {}

    # Root properties
    colors.append("lightblue")
    sizes.append(3000)
    labels["Project Root"] = "Mygrate\nProject"

    for lib_id, data in recommendations.items():
        # Defensive check: ensure data is a dict
        if not isinstance(data, dict):
            action = "upgrade"
            version = str(data)
            candidate_count = 0
        else:
            action = data.get("action", "keep")
            version = data.get("target_version", "unknown")
            candidates = data.get("candidates_tested", [])
            candidate_count = len(candidates)
        
        # Determine color based on action
        node_color = "lightgreen" if action == "upgrade" else "gold"
        
        # Add Node
        G.add_node(lib_id, color=node_color, size=2000)
        G.add_edge("Project Root", lib_id)
        
        # Update styling lists
        colors.append(node_color)
        sizes.append(2000)
        
        # Enhanced Label with candidate count
        label_text = f"{lib_id}\n(v{version})"
        if candidate_count > 0:
            label_text += f"\n[{candidate_count} tested]"
        labels[lib_id] = label_text

    # Drawing the graph
    plt.figure(figsize=(10, 8))
    plt.title("Mygrate Dependency Intelligence Graph", fontsize=16, fontweight='bold')
    
    # Use spring layout for good node spacing
    pos = nx.spring_layout(G, seed=42)
    
    nx.draw(G, pos, 
            node_color=colors, 
            node_size=sizes, 
            labels=labels, 
            font_size=10, 
            font_weight='bold',
            edge_color='gray',
            width=2,
            arrowsize=20,
            with_labels=True)
            
    # Add Legend manually
    import matplotlib.patches as mpatches
    root_patch = mpatches.Patch(color='lightblue', label='Project Root')
    upgrade_patch = mpatches.Patch(color='lightgreen', label='Upgrade Recommended')
    keep_patch = mpatches.Patch(color='gold', label='Keep Current (Stable)')
    plt.legend(handles=[root_patch, upgrade_patch, keep_patch], loc='upper right')

    # Save to file
    plt.savefig(output_image_path, format="PNG", bbox_inches='tight')
    plt.close()
    
    print(f"[+] Visualization Image generated successfully at: {os.path.abspath(output_image_path)}")

import numpy as np
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap

def generate_cross_matrix(intelligence_json_path: str, output_image_path: str = "cross_matrix.png"):
    if not os.path.exists(intelligence_json_path):
        return

    with open(intelligence_json_path, 'r', encoding='utf-8') as f:
        intelligence = json.load(f)

    recommendations = intelligence.get("recommendations", {})
    cross_compat = intelligence.get("cross_compatibility", [])

    # Lấy danh sách các thư viện độc nhất từ recommendations
    libs = list(recommendations.keys())
    
    # Lọc và bổ sung các thư viện từ cross_compat một cách an toàn
    valid_cross_items = []
    for item in cross_compat:
        if not isinstance(item, dict): continue
        l1 = item.get('lib1')
        l2 = item.get('lib2')
        if l1 and l2:
            valid_cross_items.append(item)
            if l1 not in libs: libs.append(l1)
            if l2 not in libs: libs.append(l2)
    
    n = len(libs)
    if n == 0: return

    lib_to_idx = {lib: i for i, lib in enumerate(libs)}
    
    # Khởi tạo Ma trận (Mặc định 0: Safe)
    matrix = np.zeros((n, n))

    for item in valid_cross_items:
        idx1 = lib_to_idx.get(item.get('lib1'))
        idx2 = lib_to_idx.get(item.get('lib2'))
        if idx1 is None or idx2 is None: continue
            
        status = item.get('status', 'safe').lower()
        val = 0
        if status == 'warning': val = 1
        elif status == 'conflict': val = 2
        
        matrix[idx1, idx2] = val
        matrix[idx2, idx1] = val # Tính chất đối xứng

    # ----- VẼ HEATMAP BẰNG MATPLOTLIB -----
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Định nghĩa màu: Xanh lá, Vàng, Đỏ
    cmap = ListedColormap(['#2ecc71', '#f1c40f', '#e74c3c'])
    cax = ax.matshow(matrix, cmap=cmap, vmin=0, vmax=2)

    # Gắn nhãn cho trục X và Y (Bao gồm cả phiên bản nếu có)
    def get_lib_label(lib_id):
        data = recommendations.get(lib_id, {})
        if isinstance(data, dict) and "target_version" in data:
            return f"{lib_id.split(':')[-1]}\n({data['target_version']})"
        return lib_id.split(':')[-1]

    display_libs = [get_lib_label(l) for l in libs]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(display_libs, rotation=45, ha='left', fontsize=10)
    ax.set_yticklabels(display_libs, fontsize=10)
    
    # Kẻ khung cho các ô
    ax.set_xticks(np.arange(-.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-.5, n, 1), minor=True)
    ax.grid(which='minor', color='w', linestyle='-', linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False)

    # Thêm Legend (Chú giải)
    safe_patch = mpatches.Patch(color='#2ecc71', label='Tương thích (Safe)')
    warn_patch = mpatches.Patch(color='#f1c40f', label='Cảnh báo (Warning)')
    conflict_patch = mpatches.Patch(color='#e74c3c', label='Xung đột (Conflict)')
    plt.legend(handles=[safe_patch, warn_patch, conflict_patch], loc='upper left', bbox_to_anchor=(1.05, 1))

    plt.title("Cross-Dependency Compatibility Matrix", pad=20, fontsize=14, fontweight='bold', color='#4a90e2')
    plt.savefig(output_image_path, format="PNG", bbox_inches='tight')
    plt.close()
    
    print(f"[+] Cross Matrix generated at: {os.path.abspath(output_image_path)}")

if __name__ == "__main__":
    generate_dashboard("migration_intelligence.json")
    generate_cross_matrix("migration_intelligence.json")

