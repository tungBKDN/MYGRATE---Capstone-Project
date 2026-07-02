#!/usr/bin/env python3
import yaml
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def gaussian_kde(data, num_points=1000):
    data = np.array(data, dtype=float)
    n = len(data)
    std = np.std(data, ddof=1)
    if std == 0:
        std = 1e-5
    # Silverman's rule of thumb
    h = 1.06 * std * (n ** (-0.2))
    
    x_min = data.min() - 3 * h
    x_max = data.max() + 3 * h
    xs = np.linspace(x_min, x_max, num_points)
    
    density = np.zeros_like(xs)
    for val in data:
        u = (xs - val) / h
        density += np.exp(-0.5 * u**2) / np.sqrt(2 * np.pi)
    density /= (n * h)
    
    return xs, density

def main():
    root = Path(__file__).resolve().parent
    yaml_path = root / "org_medium_dataset.yaml"
    
    if not yaml_path.exists():
        print(f"Error: {yaml_path.name} not found.")
        return
        
    with open(yaml_path, "r", encoding="utf-8") as f:
        data_list = yaml.safe_load(f)
        
    # Extract data for all datasets
    all_modules = []
    all_loc = []
    
    # Extract data for 43 datasets (filtered)
    exclude_names = {"UA-Java-Legacy", "DaisyDiff", "jadb", "jersey-jwt", "servicecomb-saga-actuator"}
    filtered_modules = []
    filtered_loc = []
    
    for entry in data_list:
        repo_name = entry.get("repo_name", "")
        repo_basename = repo_name.split("/")[-1]
        
        features = entry.get("repo_features", {})
        modules = features.get("number_of_modules", 0)
        loc = features.get("number_of_lines_of_code", 0)
        
        all_modules.append(modules)
        all_loc.append(loc)
        
        if repo_basename not in exclude_names:
            filtered_modules.append(modules)
            filtered_loc.append(loc)
            
    print(f"Total datasets found: {len(data_list)}")
    print(f"Filtered datasets (should be 43): {len(filtered_modules)}")
    
    # Create 2x2 subplots
    fig, axs = plt.subplots(2, 2, figsize=(14, 9))
    
    # Plot configuration
    color_modules = "#1f77b4" # Blue
    color_loc = "#2ca02c"     # Green
    
    # Row 1: All Datasets
    # 1.1 Modules
    xs, dens = gaussian_kde(all_modules)
    # Clip density at 0
    axs[0, 0].plot(xs, dens, color=color_modules, linewidth=2, label="KDE")
    axs[0, 0].fill_between(xs, dens, color=color_modules, alpha=0.3)
    axs[0, 0].set_title(f"Module Count Distribution - All Datasets (N={len(all_modules)})", fontsize=11, fontweight="bold")
    axs[0, 0].set_xlabel("Number of Modules")
    axs[0, 0].set_ylabel("Density")
    axs[0, 0].grid(True, linestyle="--", alpha=0.5)
    axs[0, 0].set_xlim(left=0)
    
    # 1.2 Lines of Code
    xs, dens = gaussian_kde(all_loc)
    axs[0, 1].plot(xs, dens, color=color_loc, linewidth=2, label="KDE")
    axs[0, 1].fill_between(xs, dens, color=color_loc, alpha=0.3)
    axs[0, 1].set_title(f"Lines of Code Distribution - All Datasets (N={len(all_loc)})", fontsize=11, fontweight="bold")
    axs[0, 1].set_xlabel("Lines of Code (LOC)")
    axs[0, 1].set_ylabel("Density")
    axs[0, 1].grid(True, linestyle="--", alpha=0.5)
    axs[0, 1].set_xlim(left=0)
    
    # Row 2: Filtered Datasets (43)
    # 2.1 Modules
    xs, dens = gaussian_kde(filtered_modules)
    axs[1, 0].plot(xs, dens, color=color_modules, linewidth=2)
    axs[1, 0].fill_between(xs, dens, color=color_modules, alpha=0.3)
    axs[1, 0].set_title(f"Module Count Distribution - Used Datasets (N={len(filtered_modules)})", fontsize=11, fontweight="bold")
    axs[1, 0].set_xlabel("Number of Modules")
    axs[1, 0].set_ylabel("Density")
    axs[1, 0].grid(True, linestyle="--", alpha=0.5)
    axs[1, 0].set_xlim(left=0)
    
    # 2.2 Lines of Code
    xs, dens = gaussian_kde(filtered_loc)
    axs[1, 1].plot(xs, dens, color=color_loc, linewidth=2)
    axs[1, 1].fill_between(xs, dens, color=color_loc, alpha=0.3)
    axs[1, 1].set_title(f"Lines of Code Distribution - Used Datasets (N={len(filtered_loc)})", fontsize=11, fontweight="bold")
    axs[1, 1].set_xlabel("Lines of Code (LOC)")
    axs[1, 1].set_ylabel("Density")
    axs[1, 1].grid(True, linestyle="--", alpha=0.5)
    axs[1, 1].set_xlim(left=0)
    
    plt.suptitle("KDE Distribution of Codebase Size Metrics", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    
    # Save chart
    artifact_dir = Path("C:/Users/tngtr/.gemini/antigravity-ide/brain/5b33ac4b-4634-4d18-b767-92ca82e2ae94")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    save_path = artifact_dir / "kde_distribution.png"
    
    plt.savefig(save_path, dpi=300)
    print(f"KDE Chart saved successfully to {save_path}")

if __name__ == "__main__":
    main()
