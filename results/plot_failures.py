#!/usr/bin/env python3
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Data (5 categories)
categories = [
    "Namespace Migration",
    "Target Settings Not\nUpdated",
    "No Compatible\nDependency\nReplacement\nAvailable",
    "Breaking API Changes\nin Upgraded\nDependencies",
    "Ineffective Agent\nLoop Behavior"
]

# Total failures (including the 4 skipped codebases)
ds_total = 35
qw_total = 32

# Counts (skipped codebases included in Dependency category)
ds_counts = [11, 2, 5, 13, 4]
qw_counts = [10, 0, 4, 15, 3]

# Percentages
ds_pct = [c / ds_total * 100 for c in ds_counts]
qw_pct = [c / qw_total * 100 for c in qw_counts]

# Plot setup
y = np.arange(len(categories))
height = 0.35

fig, ax = plt.subplots(figsize=(10.5, 6.5))

# Grouped horizontal bars
rects_qw = ax.barh(y - height/2, qw_pct, height, label='Qwen3.5', color='#2ca02c')
rects_ds = ax.barh(y + height/2, ds_pct, height, label='DeepSeek-V3', color='#1f77b4')

# Labeling and styling
ax.set_xlabel('Percentage (%)')
ax.set_title('Distribution of Failure Causes by Model (Normalized by Total Failures + Skips)')
ax.set_yticks(y)
ax.set_yticklabels(categories)
ax.set_xlim(0, max(max(ds_pct), max(qw_pct)) + 12)  # Expanded to fit the text labels
ax.grid(axis='x', linestyle='--', alpha=0.5)

# Add values on right of bars (percentage and counts)
def autolabel(rects, counts):
    for i, rect in enumerate(rects):
        width = rect.get_width()
        count = counts[i]
        if width > 0:
            ax.annotate(f'{width:.1f}% ({count})',
                        xy=(width, rect.get_y() + rect.get_height() / 2),
                        xytext=(4, 0),  # 4 points horizontal offset
                        textcoords="offset points",
                        ha='left', va='center', fontsize=9, fontweight='semibold')

autolabel(rects_qw, qw_counts)
autolabel(rects_ds, ds_counts)

ax.legend(loc='lower right')
plt.tight_layout()

# Save path
artifact_dir = Path(__file__).resolve().parent
artifact_dir.mkdir(parents=True, exist_ok=True)
save_path = artifact_dir / "failure_distribution.png"

plt.savefig(save_path, dpi=300)
print(f"Chart saved to {save_path}")
