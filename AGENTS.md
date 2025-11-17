# Repository Guidelines

These guidelines help keep VID-FINGER V3 consistent and maintainable for all contributors (humans and agents).

## Project Structure & Module Organization

- `src/`: CLI entry point (`cli.py`) and core forensic engine.
- `app/`: FastAPI API (`app.main`), models, tasks, and database layer.
- `tests/`: Pytest suite (API and service tests in `test_*` modules).
- `scripts/`: Utilities to start the server, run end‑to‑end tests, and manage storage/DB.
- `docs/`: Operational and deployment guides; do not duplicate them in code comments.

## Build, Test, and Development Commands

- Create venv and install dev deps: `python -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt`.
- Run CLI locally: `python src/cli.py --input samples/example.mp4 --output-dir ./output`.
- Start API server: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.
- Run tests: `pytest` (or `pytest tests/test_api` for API-only).

## Coding Style & Naming Conventions

- Use 4-space indentation, type hints, and descriptive snake_case for functions/variables; classes in PascalCase.
- Follow Black formatting: `black src app tests`.
- Run Ruff for linting: `ruff check src app tests`.
- Keep functions small and focused on a single responsibility.

## Testing Guidelines

- Add or update tests under `tests/` for every non-trivial change.
- Prefer `test_*.py` files and clear test names describing behavior (e.g., `test_upload_chunk_happy_path`).
- Use pytest idioms (fixtures, parametrization) and avoid real external services where possible.

## Commit & Pull Request Guidelines

- Follow Conventional Commits style: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- Commits should be small, self-contained, and reference relevant modules (e.g., `fix: handle invalid chunk number in upload API`).
- PRs must include: short summary, motivation, implementation notes, and how it was tested (commands and sample inputs).

## Security & Configuration Tips

- Never commit secrets, API keys, or real database URLs; use environment variables as documented in `docs/VARIAVEIS_AMBIENTE*.md`.
- Use local SQLite (`vidfinger.db`) or ephemeral databases for development; keep production configuration in separate, secure environments.

