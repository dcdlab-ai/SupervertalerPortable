# Supervertaler Portable

Desktop translation QA tool (PyQt6): XLIFF/DOCX segmentation, comment and tag management,
termbase and TM workflows, LLM-assisted review. Runs from a portable, fully bundled Python
environment — no system-wide installation required.

## Running

The application uses a bundled Python runtime located outside the repository
(default: `E:\Dev\python-embed\python.exe`):

```
E:\Dev\python-embed\python.exe Supervertaler.py
```

Python packages are installed into the same bundled runtime via
`E:\Dev\python-embed\python.exe -m pip` (see `requirements.txt`).

## Layout

- `Supervertaler.py` — the application monolith (main window, orchestration).
- `modules/` — extracted packages: `models.py`, `tag_manager.py`, `event_filters.py`,
  `styled_widgets.py`, `dialogs/` and others.
- `assets/` — icons and UI resources.
- `okapi-sidecar/` — Okapi sidecar used for XLIFF processing (Java).
- `tools/batch_validation/` — reusable validation toolkit for the refactoring batches
  (see its README).
- `docs/refactoring/` — the refactoring campaign archive: per-batch prompts (`prompts/`),
  result reports (`reports/`) and measurement artifacts (`audits/`).

## Refactoring campaign

The codebase is being incrementally extracted from the monolith into `modules/` packages
according to `EXTRACTION_PLAN.md`. Current progress and next step: see **`PROJECT_STATUS.md`**
(the single entry point for project state). Per-batch verification is documented in
`CODE_MAP_REFACTOR.md`, `DEPENDENCY_MAP.md`, `DEAD_CODE_REPORT.md` and `VALIDATION_BACKLOG.md`.
Environment, testing and validation practices for agents working on this repository are
codified in `AGENTS.md`.
