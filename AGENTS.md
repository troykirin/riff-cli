# Repository Guidelines

## Project Structure & Module Organization
The `src/` directory holds the Nushell entry points (`riff.nu`, `riff-enhanced.nu`, `riff-simple.nu`) with reusable extraction logic in `src/lib/riff-core.nu` and schema helpers under `src/types/`. Python tooling and its `jsonl_tool.py` live in `python/`, alongside the `pyproject.toml` that defines dependencies and scripts. Installation helpers sit in `install/` (notably `install.sh` and shell alias scripts). Reference docs are under `docs/`, while example inputs for ad-hoc testing live in `tests/sample-data/`. Keep new assets and fixtures in these established locations so contributors can discover them quickly.

## Build, Test, and Development Commands
Make Nushell scripts executable when building locally: `chmod +x src/*.nu`. Install shell aliases with `./install/install.sh`, and remove them via `./install/uninstall.sh`. Exercise the Nushell workflows directly without installing by running `./src/riff.nu tests/sample-data/basic.jsonl --uuid-only` or toggling flags such as `--json` and `--search`. For the Python interface, work inside `python/`: bootstrap dependencies with `uv sync`, launch the interactive browser with `uv run python jsonl_tool.py tests/sample-data/basic.jsonl --query "error"`, and use `uv run pytest` once automated tests are introduced.

## Coding Style & Naming Conventions
Match the existing four-space indentation in Nushell files and keep pipelines declarative with descriptive command names (e.g., `extract_uuids`, `filter_content`). Document complex regex or stream transformations inline. Python modules follow standard PEP 8 conventions; format with `uv run black .` and lint with `uv run ruff check .` from the `python/` directory. Prefer lowercase, hyphen-separated script names (`riff-enhanced.nu`) and snake_case for function names across languages.

## Testing Guidelines
Manual smoke checks rely on JSONL fixtures in `tests/sample-data/`; add minimal, focused files when covering new behaviours. Use representative invocations such as `./src/riff.nu tests/sample-data/basic.jsonl --search "summary"` and verify `riff-enhanced.nu` handles large datasets (`--limit 10`). Python components should gain `pytest` coverage under `python/tests/` with test modules named `test_*.py` and fixtures colocated in a `fixtures/` subdirectory. Strive for high-signal tests that confirm UUID detection, fuzzy filtering, and rendering paths.

## Commit & Pull Request Guidelines
Follow Conventional Commits with optional scopes, mirroring history such as `feat(search): implement recursive intent-driven search system`. Reference issues using "fixes" when applicable. For pull requests, provide a crisp summary of behavioural changes, enumerate manual or automated test runs, and include terminal output or screenshots if UI behaviour changed. Link related documentation updates and flag any follow-up tasks to help reviewers plan incremental improvements.
