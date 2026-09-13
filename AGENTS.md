## Environment
### Project
Project working directory:
`E:\Dev\SupervertalerPortable`
All application commands, tests and project scripts should be executed with this directory as the current working directory unless the task explicitly requires another location.
Relative paths used by the application should be resolved from this directory.
### Runtime
The project uses the bundled Python runtime:
`E:\Dev\python-embed\python.exe`
Use this interpreter for all Python commands related to the project.
Do not use:
* system Python;
* another virtual environment;
* a user-installed Python interpreter;
* another Python executable available through `PATH`.
Before running project commands, verify that the current working directory and Python interpreter match the paths specified above.
### Python packages
Project Python packages must be installed into the bundled Python runtime located at:
`E:\Dev\python-embed\`
Always invoke pip through the bundled interpreter:
`E:\Dev\python-embed\python.exe -m pip`
Do not install project dependencies into:
* system Python;
* user site-packages;
* another virtual environment;
* another Python installation.
When installing or upgrading a package, verify that pip is associated with:
`E:\Dev\python-embed\python.exe`
### Refactoring batch documents
Finished per-batch documents are committed to the repository (NOT to `D:\Temp` and NOT to the repo root):
* `docs/refactoring/prompts/` — the per-batch prompt files (`Promt - EXTRACTION BATCH #N.txt`);
* `docs/refactoring/reports/` — the per-batch result reports (`ОТЧЁТ Batch #N.txt`);
* `docs/refactoring/audits/` — the measurement artifacts (`baseline_counts*`, `callsites_*`, `counts_*`, `manifest_*`).
When a new batch is completed, write its prompt, report and audit artifacts directly into these folders
and commit them together with the batch commit. Do not leave such files in the repo root.
`requirements.txt` and `user_data/api_keys.example.txt` are live project files and stay where they are.
At the end of every batch/step also update `PROJECT_STATUS.md` (progress table, monolith
line count, "next step" section with re-derived AST boundaries) and commit it with the
final batch commit.

### Temporary files and test artifacts
Use the dedicated project temporary workspace:
`D:\Temp\SupervertalerPortable\`
Do not use the following locations for project-generated temporary files or test artifacts unless the task explicitly requires it:
* `%TEMP%`;
* `%TMP%`;
* `%LOCALAPPDATA%\Temp`;
* the user's profile directories;
* system-wide temporary directories.
Each independent task, test run, or work stage must have its own subdirectory under:
`D:\Temp\SupervertalerPortable\`
Use descriptive stage-specific directories, for example:
`D:\Temp\SupervertalerPortable\analysis\`
`D:\Temp\SupervertalerPortable\translation\`
`D:\Temp\SupervertalerPortable\refactoring\`
`D:\Temp\SupervertalerPortable\tests\`
For repeated or potentially conflicting runs, create a unique run subdirectory, for example:
`D:\Temp\SupervertalerPortable\tests\run-001\`
Do not reuse the same temporary directory for unrelated stages when doing so could mix artifacts.
Keep temporary artifacts that may be useful for debugging, comparison, or verification until the current task has been successfully completed.
Temporary artifacts may be deleted after successful completion when they are no longer needed and are not required for reproducibility or debugging.
### Environment variables
Do not permanently modify global Windows user or system environment variables merely to perform a project task.
When a project command or test needs explicit temporary directories, set `TEMP` and `TMP` for that process to the appropriate stage-specific directory under:
`D:\Temp\SupervertalerPortable\`
For example:
```bat
set "TEMP=D:\Temp\SupervertalerPortable\tests\run-001"
set "TMP=D:\Temp\SupervertalerPortable\tests\run-001"
E:\Dev\python-embed\python.exe ...
```
Prefer process-local environment variables over permanent changes to the Windows environment.
When a tool provides its own temporary-directory option, prefer that option and point it to the current stage directory.
### Path discipline
Prefer explicit project paths over paths resolved through `PATH`, user profile directories, or system-wide installations.
Do not assume that the first `python`, `pip`, or other executable found through `PATH` belongs to this project.
When invoking Python, use:
`E:\Dev\python-embed\python.exe`
When invoking pip, use:
`E:\Dev\python-embed\python.exe -m pip`
### Environment verification
Before running project commands, verify:
1. The current working directory is:
   `E:\Dev\SupervertalerPortable`
2. The Python executable is:
   `E:\Dev\python-embed\python.exe`
3. Python packages are being resolved from the bundled runtime.
4. Temporary project artifacts are being written to the appropriate directory under:
   `D:\Temp\SupervertalerPortable\`
If a tool reports a different Python interpreter, package location, working directory, or temporary directory than specified here, correct the environment before continuing.
### Bundled runtime quirk: CWD is not on sys.path
The embedded distribution (`E:\Dev\python-embed\`) ignores the current directory
(it ships a `._pth` file that excludes it). Ad-hoc scripts that import project
modules (`Supervertaler`, `modules.*`) must add the project directory explicitly:
```python
import os, sys
sys.path.insert(0, os.getcwd())
```
Symptom if forgotten: `ModuleNotFoundError: No module named 'modules'`.

### Path and tooling quirks (Git Bash on Windows)
* The embedded Python does not understand Git Bash `/tmp` paths (they map to
  `D:\Temp`). Pass explicit `D:\Temp\SupervertalerPortable\...` paths to Python
  scripts, never `/tmp/...`.
* The bundled `grep.exe` prints backslash path separators on Windows
  (`modules\dialogs\file.py`). Forward-slash `grep -v` filters will not match
  them — account for this when post-filtering grep output.
* Prefer the Edit/Write file tools over chained `sed -i` edits for test
  scripts: quoting/backslash mangling in long sed pipelines caused rework
  repeatedly in Batches #3a/#3b.

### GUI (PyQt6) testing
Run GUI checks offscreen and non-interactively:
* Set `QT_QPA_PLATFORM=offscreen` for every GUI test process.
* Modal dialogs never close offscreen and block forever: `QDialog.exec()`,
  `QMessageBox.*`, `QFileDialog.*`, `QColorDialog.getColor`,
  `QInputDialog.getText`. Monkeypatch them in the test harness (e.g. auto-accept
  `QDialog.exec`), or use programmatic alternatives (build a `Project` object
  and assign `current_project` instead of calling `new_project()`, which opens
  a modal wizard).
* Run GUI test scripts unbuffered (`python.exe -u script.py > out.txt 2>&1`)
  with output in the stage directory; run them in the background and poll the
  file. Buffered stdout makes a hung run look like a silent one.
* Instantiating `SupervertalerQt` takes roughly 1–2 minutes (database, prompt
  library, hotkeys, sidecar). Do not kill a run before ~3 minutes have elapsed;
  confirm a real hang with a stack dump (below), not by silence.
* To diagnose a hang, add at the top of the script:
  ```python
  import faulthandler, sys
  faulthandler.dump_traceback_later(60, repeat=True, file=sys.stderr)
  ```
  The repeated thread-stack dump names the exact blocking call.
* After each GUI test process, kill leftover `python.exe`/`java.exe` before the
  next run: the app spawns an Okapi sidecar subprocess, and test scripts that
  exit via `os._exit()` leave it orphaned.

### Git line-ending artifacts
Comparing `git show HEAD:<file>` bytes against the working copy can produce
false differences (LF in the repository vs CRLF in the tree, e.g. observed on
`modules/tag_manager.py`). For "what really changed" checks use `git status` /
`git diff` or file-to-file hash manifests captured from the same source (both
from the filesystem, or both from git), never one from each.

### Refactoring batch validation practices
Validated in Batches #2, #3a, #3b — keep doing this:
* Documented line ranges in `CODE_MAP_REFACTOR.md` / `EXTRACTION_PLAN.md` go
  stale after every batch. Always re-derive class boundaries with AST
  (`ast.parse`, `lineno`/`end_lineno`); never trust documented numbers, but do
  fix the documents when they are proven wrong.
* Before editing, snapshot the to-be-moved blocks from `git HEAD` into the
  stage directory together with their sha256; after creating the new files,
  verify the verbatim transfer by comparing file tails byte-wise against the
  snapshots. Re-verify once more immediately before the commit.
* Count the 8 baseline metrics with the identical command before and after
  (`grep -rE`, parens escaped: `\.connect\(`, `QShortcut\(`, `create_shortcut\(`,
  `QTimer\(`, `timeout\.connect`, `QTimer\.timeout`, `singleShot`,
  `QMetaObject\.invokeMethod`), always excluding `__pycache__`.
* Collect callsites and external-name inventories via AST, not by eyeballing:
  an external-name scan must walk the whole top-level (imports inside
  `try:`/`if:` blocks count) and must report names resolved by monolith imports
  too, not only unresolvable ones — this is how the `CheckmarkCheckBox`,
  `contextmanager`, `time` header dependencies were nearly missed in Batch #3b.

### Behavioral comparison of duplicate/merged implementations (Batch #3c)
When a batch merges classes into an existing module (or the plan claims code is
a "duplicate"), prove the behavioral claim before merging:
* Static: `ast.dump()` both method bodies (docstrings/control-flow shape may
  differ textually while rendering stays identical) and diff the final
  stylesheet strings char-by-char — in #3c the difference was exactly 4 hex
  substitutions.
* Dynamic: offscreen pixel comparison of `widget.grab().toImage()` renders,
  pixel-by-pixel over scenarios (unchecked / checked / checked+resize /
  disabled+checked), saving PNG evidence per scenario per state.
* A pixel-level FAIL may be a test-harness bug, not a code difference — in #3c
  the base widget was compared without applying the counterpart's stylesheet.
  Before diagnosing a regression, verify the harness actually tests what its
  label claims (an "expected equal" check that prints FAIL with equal-length
  strings usually means the wrong objects are compared).
* The reusable scripts live in `tools/batch_validation/` (see its README):
  `render_compare.py` (pixel gate), `probe.py` (full-app snapshot),
  `smoke.py` (2-process save/load), `manifest.py`/`counts.py` (baseline).
* Every numeric claim in the Этап 4 report must be reproduced from a
  measurement command (`wc -l` before/after), not carried from memory —
  in #3c the report initially claimed "−313 lines" while the real net was
  −310 (311-line block deleted, import line grew from 1 to 2 lines).

### Full-app before/after probes and user-data isolation
* To compare live-app behavior DO/POS, `git worktree add <stage>/head-wt HEAD`
  and run the same probe script in both trees; compare JSON snapshots
  (per class: `findChildren`, count, text, checked/enabled, size,
  sha256 of `styleSheet()`). Expect the only diff to be `class_module`.
* User data does NOT follow cwd: `get_user_data_path()` resolves from the
  global `~/.supervertaler_config.json` (in #3c a worktree probe resolved to
  the production `D:\_old\Supervertaler-Portable\Supervertaler`). Read-only
  probes are therefore safe anywhere, but smoke tests WRITE to that shared
  location (project saves, versioned backups) from any tree — keep probes
  read-only, and remember smoke artifacts land in the production user data.
* Widgets created inside modal dialogs never appear at startup. Cover them by
  monkeypatching `QDialog.exec` with a stub that snapshots
  `dialog.findChildren(...)` and returns `QDialog.DialogCode.Rejected`, then
  call the dialog-opening method directly (used in #3c for
  `_show_create_termbase_dialog`).

### Exceptions
The rules in this section may be overridden only when:
* the task explicitly requires another environment;
* a specific external tool cannot operate with the bundled runtime;
* the project itself explicitly requires another location.
When an exception is necessary, keep it limited to the affected command or process and do not permanently modify the project's standard environment.
