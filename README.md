# MYGRATE---Capstone-Project

MYGRATE is a Java migration analysis workspace used to inspect, batch-run, summarize, and report migration outcomes across many codebases. The repository contains the migration pipeline, generated datasets, evaluation artifacts, and the reporting tools used for the capstone project.

The final project notes are in [docs/final-state.md](docs/final-state.md), and generated inspection reports are written to [docs/reports/](docs/reports/).

## What This Repo Does

- Runs migration jobs across the sample codebases under `freshbrew_data/`.
- Stores per-model evaluation results in `eval_<model>.json` files at the repository root.
- Generates summary and inspection reports from those evaluation results.
- Preserves working copies and runtime logs under `working/`.

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
- `working/`: per-model working copies and runtime logs created by batch runs.
- `artifacts/`: supporting analysis artifacts and discovery output.
- `docs/reports/`: generated inspection reports.
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

Generate a markdown report for each model:

```powershell
python scripts/reporting/generate_inspection_reports.py
```

Output is written to [docs/reports/](docs/reports/).

### Narrative-Style Report

Generate the more descriptive report variant:

```powershell
python scripts/reporting/generate_llm_like_reports.py
```

Output is written to [docs/reports/](docs/reports/).

### Legacy Cause Classification

Classify the historical failure causes from evaluation logs:

```powershell
python scripts/reporting/classify_by_old_causes.py
```

### CLI Simulation

Replay the CLI output from a saved log file:

```powershell
python simulate_cli.py
```

You can pass a numeric delay as the first argument to slow down the playback.

## Outputs and Artifacts

- `eval_<model>.json`: per-model evaluation data written by batch runs.
- `working/<model>/`: working copies of each codebase for that model.
- `docs/reports/inspect_<model>.md`: generated inspection reports.
- `artifacts/`: discovery and analysis outputs produced by the pipeline.

Generated files can be recreated at any time, so they should stay out of version control unless you explicitly need them for documentation.

## Notes

- The reporting scripts now live in `scripts/reporting/` instead of the repository root.
- Shared ANSI-cleaning logic is centralized in `scripts/reporting/script_utils.py`.
- The repository still contains large input datasets and runtime working trees because they are part of the migration workflow.
- See [docs/final-state.md](docs/final-state.md) for a concise final-state summary.