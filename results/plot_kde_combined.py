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
    root = Path(__file__).resolve().parent.parent
    yaml_path = root / "org_medium_dataset.yaml"
    
    if not yaml_path.exists():
        print(f"Error: {yaml_path.name} not found.")
        return
        
    with open(yaml_path, "r", encoding="utf-8") as f:
        data_list = yaml.safe_load(f)
        
    # Exclude UA-Java-Legacy globally because it was never in the evaluated 47 dataset
    exclude_global = {"UA-Java-Legacy"}
    exclude_used = {"DaisyDiff", "jadb", "jersey-jwt", "servicecomb-saga-actuator"}
    
    # Dataset 1: All 47 evaluated codebases
    modules_47 = []
    loc_47 = []
    
    # Dataset 2: 43 used codebases
    modules_43 = []
    loc_43 = []
    
    for entry in data_list:
        repo_name = entry.get("repo_name", "")
        repo_basename = repo_name.split("/")[-1]
        
        if repo_basename in exclude_global:
            continue
            
        features = entry.get("repo_features", {})
        modules = features.get("number_of_modules", 0)
        loc = features.get("number_of_lines_of_code", 0)
        
        modules_47.append(modules)
        loc_47.append(loc)
        
        if repo_basename not in exclude_used:
            modules_43.append(modules)
            loc_43.append(loc)
            
    print(f"Total datasets in Group 1 (All Evaluated, N={len(modules_47)}): 47")
    print(f"Total datasets in Group 2 (Used, N={len(modules_43)}): 43")
    
    # Create 1 row, 2 subplots layout
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.5))
    
    # Custom color palette
    c_47 = "#1f77b4"     # Blue (Group 47)
    c_43 = "#ff7f0e"     # Orange (Group 43)
    
    # Subplot 1: Modules comparison (Linear scale)
    xs_47_mod, dens_47_mod = gaussian_kde(modules_47)
    xs_43_mod, dens_43_mod = gaussian_kde(modules_43)
    
    dens_47_mod = np.clip(dens_47_mod, 0, None)
    dens_43_mod = np.clip(dens_43_mod, 0, None)
    
    axs[0].plot(xs_47_mod, dens_47_mod, color=c_47, linewidth=2.2, label=f"All Evaluated Datasets (N={len(modules_47)})")
    axs[0].fill_between(xs_47_mod, dens_47_mod, color=c_47, alpha=0.15)
    
    axs[0].plot(xs_43_mod, dens_43_mod, color=c_43, linewidth=2.2, linestyle="--", label=f"Used Datasets (N={len(modules_43)})")
    axs[0].fill_between(xs_43_mod, dens_43_mod, color=c_43, alpha=0.15)
    
    axs[0].set_title("Module Count Distribution Comparison", fontsize=12, fontweight="bold")
    axs[0].set_xlabel("Number of Modules")
    axs[0].set_ylabel("Density")
    axs[0].grid(True, linestyle="--", alpha=0.5)
    axs[0].set_xlim(0, max(max(modules_47), max(modules_43)) + 2)
    axs[0].legend(loc="upper right")
    
    # Subplot 2: LOC comparison (Linear scale)
    xs_47_loc, dens_47_loc = gaussian_kde(loc_47)
    xs_43_loc, dens_43_loc = gaussian_kde(loc_43)
    
    dens_47_loc = np.clip(dens_47_loc, 0, None)
    dens_43_loc = np.clip(dens_43_loc, 0, None)
    
    axs[1].plot(xs_47_loc, dens_47_loc, color=c_47, linewidth=2.2, label=f"All Evaluated Datasets (N={len(loc_47)})")
    axs[1].fill_between(xs_47_loc, dens_47_loc, color=c_47, alpha=0.15)
    
    axs[1].plot(xs_43_loc, dens_43_loc, color=c_43, linewidth=2.2, linestyle="--", label=f"Used Datasets (N={len(loc_43)})")
    axs[1].fill_between(xs_43_loc, dens_43_loc, color=c_43, alpha=0.15)
    
    axs[1].set_title("Lines of Code (LOC) Distribution Comparison", fontsize=12, fontweight="bold")
    axs[1].set_xlabel("Lines of Code (LOC)")
    axs[1].set_ylabel("Density")
    axs[1].grid(True, linestyle="--", alpha=0.5)
    axs[1].set_xlim(0, max(max(loc_47), max(loc_43)) + 5000)
    axs[1].legend(loc="upper right")
    
    plt.suptitle("KDE Size Metrics Comparison (47 Evaluated vs. 43 Used Datasets)", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    
    # Save combined chart
    artifact_dir = Path(__file__).resolve().parent
    artifact_dir.mkdir(parents=True, exist_ok=True)
    save_path = artifact_dir / "kde_distribution_combined.png"
    
    plt.savefig(save_path, dpi=300)
    print(f"Combined KDE Chart saved successfully to {save_path}")

if __name__ == "__main__":
    main()
