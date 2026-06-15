import json
from pathlib import Path

cells = [
    {
        "cell_type": "markdown",
        "id": "title-cell",
        "metadata": {},
        "source": [
            "# MYGRATE Migration Evaluation & Visualization\n",
            "\n",
            "This notebook loads the evaluation metrics from `eval.json` and generates various analytical plots to summarize the codebase migration success rates, test passes, coverage drops, and agent efficiency."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "setup-cell",
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            "import json\n",
            "import pandas as pd\n",
            "import numpy as np\n",
            "import matplotlib.pyplot as plt\n",
            "import seaborn as sns\n",
            "\n",
            "# Set seaborn style for premium aesthetics\n",
            "sns.set_theme(style=\"whitegrid\")\n",
            "plt.rcParams[\"figure.figsize\"] = (10, 6)\n",
            "plt.rcParams[\"font.family\"] = \"sans-serif\"\n",
            "plt.rcParams[\"font.size\"] = 11\n",
            "\n",
            "# Modern premium color palette\n",
            "COLORS = {\n",
            "    \"primary\": \"#3B82F6\",      # Blue\n",
            "    \"success\": \"#10B981\",      # Green\n",
            "    \"warning\": \"#F59E0B\",      # Yellow/Amber\n",
            "    \"danger\": \"#EF4444\",       # Red\n",
            "    \"purple\": \"#8B5CF6\",       # Purple\n",
            "    \"dark\": \"#1F2937\",         # Dark Gray\n",
            "    \"light\": \"#F3F4F6\"         # Light Gray\n",
            "}\n",
            "\n",
            "print(\"Libraries successfully imported!\")"
        ]
    },
    {
        "cell_type": "markdown",
        "id": "load-data-title",
        "metadata": {},
        "source": [
            "## 1. Load and Clean Evaluation Data"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "load-data-code",
        "metadata": {},
        "outputs": [],
        "source": [
            "# Load eval.json\n",
            "eval_path = Path(\"eval.json\")\n",
            "if not eval_path.exists():\n",
            "    raise FileNotFoundError(\"eval.json not found in the workspace!\")\n",
            "\n",
            "with open(eval_path, \"r\", encoding=\"utf-8\") as f:\n",
            "    raw_data = json.load(f)\n",
            "\n",
            "# Convert to DataFrame\n",
            "records = []\n",
            "for project_name, metrics in raw_data.items():\n",
            "    record = {\"project\": project_name}\n",
            "    record.update(metrics)\n",
            "    records.append(record)\n",
            "\n",
            "df = pd.DataFrame(records)\n",
            "\n",
            "# Format boolean columns\n",
            "df[\"compilation_success\"] = df[\"compilation_success\"].astype(bool)\n",
            "df[\"gate2_tests_pass\"] = df[\"gate2_tests_pass\"].astype(bool)\n",
            "df[\"gate3_coverage_ok\"] = df[\"gate3_coverage_ok\"].astype(bool)\n",
            "df[\"overall_success\"] = df[\"overall_success\"].astype(bool)\n",
            "\n",
            "# Calculate test pass rate for current run\n",
            "df[\"test_pass_rate\"] = np.where(df[\"total_tests\"] > 0, df[\"passed_tests\"] / df[\"total_tests\"], 0.0)\n",
            "df[\"baseline_test_pass_rate\"] = np.where(df[\"baseline_total_tests\"] > 0, df[\"baseline_passed_tests\"] / df[\"baseline_total_tests\"], 0.0)\n",
            "\n",
            "# Display data head and summary info\n",
            "print(f\"Loaded {len(df)} codebase records.\")\n",
            "df.head()"
        ]
    },
    {
        "cell_type": "markdown",
        "id": "rates-title",
        "metadata": {},
        "source": [
            "## 2. Key Metrics Rates (Compilation, Test & Overall Success)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "rates-code",
        "metadata": {},
        "outputs": [],
        "source": [
            "# Calculate aggregate success rates\n",
            "compile_rate = df[\"compilation_success\"].mean() * 100\n",
            "test_rate = df[\"gate2_tests_pass\"].mean() * 100\n",
            "overall_rate = df[\"overall_success\"].mean() * 100\n",
            "\n",
            "rates = {\n",
            "    \"Compilation Success\": compile_rate,\n",
            "    \"Unit Test Pass (Gate 2)\": test_rate,\n",
            "    \"Overall Success (All Gates)\": overall_rate\n",
            "}\n",
            "\n",
            "# Plot rates as a premium horizontal bar chart\n",
            "fig, ax = plt.subplots(figsize=(10, 5))\n",
            "bars = ax.barh(list(rates.keys()), list(rates.values()), color=[COLORS[\"primary\"], COLORS[\"purple\"], COLORS[\"success\"]], height=0.55)\n",
            "\n",
            "# Visual improvements\n",
            "ax.set_xlim(0, 110)\n",
            "ax.set_xlabel(\"Success Rate (%)\", fontweight=\"semibold\", labelpad=12)\n",
            "ax.set_title(\"Aggregate Migration Success Indicators\", fontsize=14, fontweight=\"bold\", pad=15)\n",
            "\n",
            "# Label values on the bars\n",
            "for bar in bars:\n",
            "    width = bar.get_width()\n",
            "    ax.text(width + 2, bar.get_y() + bar.get_height()/2, f\"{width:.1f}%\", \n",
            "            va='center', ha='left', fontsize=11, fontweight='semibold', color=COLORS[\"dark\"])\n",
            "\n",
            "sns.despine(left=True, bottom=True)\n",
            "plt.tight_layout()\n",
            "plt.savefig(\"migration_success_rates.png\", dpi=300)\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "id": "drop-dist-title",
        "metadata": {},
        "source": [
            "## 3. Coverage Drop Distribution (Gate 3)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "drop-dist-code",
        "metadata": {},
        "outputs": [],
        "source": [
            "# Filter projects with active coverage baseline\n",
            "df_cov = df[df[\"baseline_coverage\"] > 0]\n",
            "\n",
            "if len(df_cov) > 0:\n",
            "    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))\n",
            "    \n",
            "    # Plot 1: Histogram & KDE of coverage drops\n",
            "    sns.histplot(data=df_cov, x=\"coverage_drop_pp\", kde=True, ax=ax1, color=COLORS[\"warning\"], bins=10)\n",
            "    ax1.axvline(5.0, color=COLORS[\"danger\"], linestyle=\"--\", linewidth=2, label=\"Gate 3 Threshold (5pp)\")\n",
            "    ax1.set_title(\"Distribution of Coverage Drop (pp)\", fontsize=12, fontweight=\"bold\")\n",
            "    ax1.set_xlabel(\"Coverage Drop (Percentage Points)\")\n",
            "    ax1.set_ylabel(\"Number of Codebases\")\n",
            "    ax1.legend()\n",
            "    \n",
            "    # Plot 2: Boxplot for outlier detection\n",
            "    sns.boxplot(data=df_cov, x=\"coverage_drop_pp\", ax=ax2, color=COLORS[\"purple\"], width=0.4)\n",
            "    ax2.axvline(5.0, color=COLORS[\"danger\"], linestyle=\"--\", linewidth=2, label=\"Gate 3 Threshold (5pp)\")\n",
            "    ax2.set_title(\"Coverage Drop Range & Outliers\", fontsize=12, fontweight=\"bold\")\n",
            "    ax2.set_xlabel(\"Coverage Drop (Percentage Points)\")\n",
            "    ax2.legend()\n",
            "    \n",
            "    plt.suptitle(\"Line Coverage Degradation Analysis (Gate 3)\", fontsize=15, fontweight=\"bold\", y=0.98)\n",
            "    plt.tight_layout()\n",
            "    plt.savefig(\"coverage_drop_distribution.png\", dpi=300)\n",
            "    plt.show()\n",
            "else:\n",
            "    print(\"No codebases found with valid baseline coverage to plot.\")"
        ]
    },
    {
        "cell_type": "markdown",
        "id": "calls-dist-title",
        "metadata": {},
        "source": [
            "## 4. Agent Efficiency & Calls Distribution"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "calls-dist-code",
        "metadata": {},
        "outputs": [],
        "source": [
            "# Bar plot of agent calls per project\n",
            "df_sorted_steps = df.sort_values(by=\"step_count\", ascending=False)\n",
            "\n",
            "fig, ax = plt.subplots(figsize=(12, 6))\n",
            "colors_mapped = np.where(df_sorted_steps[\"overall_success\"], COLORS[\"success\"], COLORS[\"danger\"])\n",
            "bars = ax.bar(df_sorted_steps[\"project\"], df_sorted_steps[\"step_count\"], color=colors_mapped, width=0.6)\n",
            "\n",
            "# Add titles and labels\n",
            "ax.set_title(\"Agent ReAct Step Counts per Codebase\", fontsize=14, fontweight=\"bold\", pad=15)\n",
            "ax.set_ylabel(\"ReAct Steps (LLM calls)\", fontweight=\"semibold\")\n",
            "ax.set_xlabel(\"Codebase Project Name\", fontweight=\"semibold\", labelpad=10)\n",
            "plt.xticks(rotation=45, ha=\"right\")\n",
            "\n",
            "# Legend indicators\n",
            "from matplotlib.patches import Patch\n",
            "legend_elements = [\n",
            "    Patch(facecolor=COLORS[\"success\"], label='Migration Success (Passed all Gates)'),\n",
            "    Patch(facecolor=COLORS[\"danger\"], label='Migration Failed / Blocked')\n",
            "]\n",
            "ax.legend(handles=legend_elements, loc='upper right')\n",
            "\n",
            "# Add value labels on top of bars\n",
            "for bar in bars:\n",
            "    height = bar.get_height()\n",
            "    ax.text(bar.get_x() + bar.get_width()/2., height + 0.5, f\"{int(height)}\",\n",
            "            ha='center', va='bottom', fontsize=10, color=COLORS[\"dark\"])\n",
            "\n",
            "sns.despine()\n",
            "plt.tight_layout()\n",
            "plt.savefig(\"agent_calls_distribution.png\", dpi=300)\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "id": "additional-cov-comparison-title",
        "metadata": {},
        "source": [
            "## 5. Additional Visualizations: Coverage Comparison & Efficiency Correlations"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "additional-cov-comparison-code",
        "metadata": {},
        "outputs": [],
        "source": [
            "if len(df_cov) > 0:\n",
            "    # Plot 5.1: Baseline vs Final Coverage Grouped Bar Chart\n",
            "    x = np.arange(len(df_cov))\n",
            "    width = 0.35\n",
            "\n",
            "    fig, ax = plt.subplots(figsize=(14, 7))\n",
            "    rects1 = ax.bar(x - width/2, df_cov[\"baseline_coverage\"], width, label='Baseline Coverage', color=COLORS[\"primary\"])\n",
            "    rects2 = ax.bar(x + width/2, df_cov[\"line_coverage\"], width, label='Final Coverage', color=COLORS[\"success\"])\n",
            "\n",
            "    ax.set_ylabel('Line Coverage (%)', fontweight=\"semibold\")\n",
            "    ax.set_title('Comparison: Baseline vs Final Line Coverage', fontsize=14, fontweight=\"bold\", pad=15)\n",
            "    ax.set_xticks(x)\n",
            "    ax.set_xticklabels(df_cov[\"project\"], rotation=45, ha=\"right\")\n",
            "    ax.legend()\n",
            "    \n",
            "    sns.despine()\n",
            "    plt.tight_layout()\n",
            "    plt.savefig(\"coverage_comparison.png\", dpi=300)\n",
            "    plt.show()\n",
            "    \n",
            "    # Plot 5.2: Scatter Plot steps vs coverage drop\n",
            "    fig, ax = plt.subplots(figsize=(8, 6))\n",
            "    sns.scatterplot(data=df, x=\"step_count\", y=\"coverage_drop_pp\", hue=\"overall_success\", \n",
            "                    palette={True: COLORS[\"success\"], False: COLORS[\"danger\"]}, s=100, ax=ax)\n",
            "    ax.set_title(\"Agent Steps vs Coverage Degradation\", fontsize=13, fontweight=\"bold\", pad=15)\n",
            "    ax.set_xlabel(\"Agent Step Count (LLM Calls)\")\n",
            "    ax.set_ylabel(\"Coverage Drop (Percentage Points)\")\n",
            "    ax.axhline(5.0, color=\"red\", linestyle=\"--\", alpha=0.6, label=\"Threshold (5pp)\")\n",
            "    ax.legend(title=\"Overall Success\")\n",
            "    \n",
            "    sns.despine()\n",
            "    plt.tight_layout()\n",
            "    plt.savefig(\"steps_vs_coverage_drop.png\", dpi=300)\n",
            "    plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "id": "styled-table-title",
        "metadata": {},
        "source": [
            "## 6. Detailed Evaluation Results Table"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "id": "styled-table-code",
        "metadata": {},
        "outputs": [],
        "source": [
            "# Style and format table for clean visualization\n",
            "styled_df = df[[\n",
            "    \"project\", \"compilation_success\", \"gate2_tests_pass\", \n",
            "    \"gate3_coverage_ok\", \"overall_success\", \"step_count\", \n",
            "    \"passed_tests\", \"total_tests\", \"baseline_coverage\", \n",
            "    \"line_coverage\", \"coverage_drop_pp\"\n",
            "]].copy()\n",
            "\n",
            "# Helper to highlight True/False status\n",
            "def highlight_status(val):\n",
            "    if isinstance(val, bool):\n",
            "        color = '#D1FAE5' if val else '#FEE2E2'\n",
            "        return f'background-color: {color}'\n",
            "    return ''\n",
            "\n",
            "styled_df.style.applymap(highlight_status, subset=[\n",
            "    \"compilation_success\", \"gate2_tests_pass\", \"gate3_coverage_ok\", \"overall_success\"\n",
            "]).format({\n",
            "    \"baseline_coverage\": \"{:.2f}%\",\n",
            "    \"line_coverage\": \"{:.2f}%\",\n",
            "    \"coverage_drop_pp\": \"{:.2f}pp\",\n",
            "    \"test_pass_rate\": \"{:.2%}\"\n",
            "})"
        ]
    }
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3 (.venv)",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.12.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

# Write out the generated notebook
target_path = Path("eval_visualization.ipynb")
with open(target_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"Jupyter Notebook successfully written to: {target_path.absolute()}")
