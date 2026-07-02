# MYGRATE---Capstone-Project

MYGRATE is a Java migration analysis workspace used to inspect, batch-run, summarize, and report migration outcomes across many codebases. The repository contains the migration pipeline, generated datasets, evaluation artifacts, and the reporting tools used for the capstone project.

All final evaluation outputs, result scripts, inspection reports, and plot generators have been consolidated into the centralized `/results/` directory.

## What This Repo Does

- Runs migration jobs across the sample codebases under `freshbrew_data/`.
- Stores model-specific working copies under `working/` (without artifacts).
- Stores all evaluation results, reports, plots, and analysis tools in the `/results/` folder.
- Generates summary and inspection reports from those evaluation results.

## Requirements

- Python 3.10+.
- Java 17.
- Maven available on `PATH` for the migration and verification steps.
- A Python environment with the packages from [requirements.txt](requirements.txt).

If you use the included virtual environment, activate it before running the scripts.

## Project Layout

- `src/`: core application, agents, tools, and workflow code.
- `scripts/reporting/`: reporting and classification entry points.
- `scripts/`: remaining utility entry points and local tooling.
- `freshbrew_data/`: source codebases used as migration inputs.
- `working/`: per-model working copies created by batch runs.
- `artifacts/`: supporting analysis artifacts and discovery output.
- `results/`: consolidated evaluations, reports, plotting scripts, and dataset inspections.
  - `deepseek-v3.2_cloud/` & `qwen3.5_cloud/`: migrated codebase outputs (logs, reports).
  - `eval_*.json`: evaluation result files.
  - `inspect_*.md`: detailed markdown inspection reports.
  - `precalc_baseline.json`: cached baseline metrics.
  - `dataset_inspect.ipynb`: Jupyter notebook for dataset analysis.
  - `calc_jdk8_baseline.py`, `plot_*.py`: baseline and plot generation scripts.
- `docs/`: final documentation and project notes.

## Quick Start

1. Create or activate a Python environment.
2. Install dependencies:

	```powershell
	pip install -r requirements.txt
	```

3. Make sure Java 17 and Maven are available.
4. Run the workflow you need from the sections below.

## Common Workflows

### Batch Migration Run

Run the migration pipeline across all codebases in `freshbrew_data/`:

```powershell
python run_batch.py
```

Useful flags:

- `--only <CODEBASE ...>`: run only the named codebases.
- `--clean`: recopy the input codebase into the working area before each run.
- `--force`: rerun codebases even if results already exist.
- `--target-java 17`: change the target Java version.
- `--pause-every N`: pause after every N completed runs.
- `--reverse`: process codebases in reverse order.

### Summary Report

Print the evaluation summary table for all models:

```powershell
python scripts/reporting/eval_summary.py
```

Include skipped codebases in the statistics:

```powershell
python scripts/reporting/eval_summary.py --contain_skip
```

### Detailed Inspection Report

Generate or update markdown reports for each model:

```powershell
python scripts/reporting/generate_inspection_reports.py
```

Output markdown files are written directly to the `/results/` directory as `results/inspect_<model>.md`.

### Run Plotting and Baseline calculations

All numerical results and plot generator scripts now run from the `/results/` directory and output their `.png` charts there:

```powershell
# Plot failure cause distribution
python results/plot_failures.py

# Plot KDE metric distribution
python results/plot_kde.py

# Plot combined KDE metric distribution comparison
python results/plot_kde_combined.py

# Calculate baseline Java 8 metrics
python results/calc_jdk8_baseline.py
```

### CLI Simulation

Replay the CLI output from a saved log file:

```powershell
python simulate_cli.py
```

You can pass a numeric delay as the first argument to slow down the playback.

## Outputs and Artifacts

- `results/eval_<model>.json`: per-model evaluation data written by batch runs.
- `results/<model>/<codebase>/`: codebase-specific migration artifacts (such as `cli_output.log`, `upgrade_report.json`).
- `results/inspect_<model>.md`: generated inspection reports.
- `results/*.png`: generated chart images (like `kde_distribution.png`).

## Notes

- The reporting scripts now live in `scripts/reporting/` instead of the repository root.
- Shared ANSI-cleaning logic is centralized in `scripts/reporting/script_utils.py`.
- Baseline cache, dataset inspections, failure plots, and model result folders are all organized within the `/results/` directory.
- See [docs/final-state.md](docs/final-state.md) for a concise final-state summary.