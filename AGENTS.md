# Repository Guidelines

## Project Structure & Module Organization
Key directories: `src/core/` (workflow, config, logging), `src/modules/` (LLM, TTS, Whisper, subtitle, FFmpeg editors), `src/utils/` (ffmpeg/file/text helpers), and `src/ui/` (Gradio components). UI assets live in `assets/`, sample footage in `datamaterialsvideos/`, and generated artifacts under `data/` plus diagnostic output in `logs/`. `main.py` boots the app and reads `config.toml`; keep architectural notes in `docs/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` — provision a Python 3.10+ environment.
- `pip install -e .[dev]` — install runtime plus lint/test extras; rerun after dependency updates.
- `python main.py` — bring up the Gradio UI on http://127.0.0.1:7860 for manual runs.
- `pytest tests -v --cov=src` — execute unit/async suites with coverage (HTML in `htmlcov/`).
- `black src tests && isort src tests` — enforce the shared 100-character formatting profile.
- `flake8 src tests && mypy src` — run linting and static typing gates.
- `pre-commit run --all-files` — replicate the CI hook chain before pushing.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation and the 100 character max specified in `pyproject.toml`. Functions and modules use snake_case, classes use CapWords, and constants stay SCREAMING_SNAKE_CASE. Keep modules cohesive; new media processors belong in `src/modules/` with clear docstrings covering dependencies and side effects.

## Testing Guidelines
Create or extend `tests/` with files named `test_*.py` (matching `tool.pytest.ini_options`). Mirror the source tree—e.g., `tests/test_workflow_manager.py` for `src/core/workflow_manager.py`. Mark coroutine tests with `pytest.mark.asyncio`, share fixtures in `tests/conftest.py`, and target ≥80% coverage on touched modules, prioritizing FFmpeg wrappers, timing utilities, and async orchestration.

## Commit & Pull Request Guidelines
Existing instructions (README) adopt Conventional Commits—start with `feat:`, `fix:`, `docs:`, etc., in imperative voice such as `feat: add subtitle kerning controls`. Develop on topic branches (`feature/<summary>`, `bugfix/<ticket>`), keep diffs focused, and include testing proof (`pytest` output or Gradio screenshots), config changes, and media impacts in each PR. Ensure all commands above pass and reference related issues or tasks.

## Configuration & Security Tips
Copy `config.toml.example` to `config.toml`, load secrets via environment variables or `.env` handled by `python-dotenv`, and never commit real keys. FFmpeg must be installed and on PATH; use `check_edge_tts_status.py` and `check_ass_content.py` when diagnosing media pipelines. Clean large intermediate renders from `data/` before committing to keep the repo lean.
