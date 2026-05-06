# Repository Guidelines

## Project Structure & Module Organization
`realesrgan/` contains the Python package: `archs/` for network definitions, `data/` for datasets, `models/` for training logic, and `utils.py` for shared helpers. Top-level inference entry points live in `inference_realesrgan.py`, `inference_realesrgan_video.py`, and `cog_predict.py`. Training configs are in `options/`; utility scripts such as ONNX conversion and dataset preparation are in `scripts/`. Tests and sample fixtures are under `tests/` and `tests/data/`. Treat `weights/`, `results/`, `experiments/`, and local image folders as generated/runtime artifacts.

## Build, Test, and Development Commands
Install dependencies and the package in editable mode:
```bash
pip install basicsr facexlib gfpgan -r requirements.txt
python setup.py develop
```
Run the test suite:
```bash
pytest tests/
```
Run lint/format checks used by CI:
```bash
flake8 .
isort --check-only --diff realesrgan/ scripts/ inference_realesrgan.py setup.py
yapf -r -d realesrgan/ scripts/ inference_realesrgan.py setup.py
codespell
```
Enable local hooks before committing:
```bash
pre-commit install
```
Sync files or directories to the configured remote machine:
```bash
./push.sh AGENTS.md
./push.sh realesrgan/ tests/
```

## Coding Style & Naming Conventions
Follow PEP 8 with repository-specific limits from `setup.cfg`: 4-space indentation and a 120-character line limit. Use `yapf` for formatting, `isort` for imports, and `flake8` for linting. Keep modules and functions in `snake_case`; classes use `PascalCase` such as `RealESRGANModel`. Match existing config naming in `options/`, for example `train_realesrgan_x4plus.yml`.

## Testing Guidelines
Tests use `pytest` and are discovered from `tests/` via `setup.cfg`. Name files `test_*.py` and keep fixtures or YAML options in `tests/data/`. Add or update tests for changes in model behavior, dataset loading, or utility functions. Prefer small deterministic inputs like the existing sample tensors and fixture images.

## Commit & Pull Request Guidelines
Recent history uses short, imperative commit subjects, for example `Delete .github/workflows/no-response.yml`. Keep commits focused and descriptive. For pull requests, work from a feature branch, summarize the change, note any model/config updates, link related issues or discussions, and include example outputs or screenshots when inference results change. Run tests and lint checks before opening the PR.

## Security & Configuration Tips
Do not commit model weights, generated results, or private datasets. Keep large artifacts in local runtime directories such as `weights/` or `results/`, and document any new external dependency or download source in `README.md` or `docs/`.
