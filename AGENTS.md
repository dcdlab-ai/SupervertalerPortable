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
**The agent does not modify the dev runtime on its own initiative** (Dmitry's
decision, BATCH Q-A Q7 verdict 2026-10-23): never run `pip install` / `pip
uninstall` against `E:\Dev\python-embed` unless the batch prompt explicitly
says so. If a validation tool is missing (e.g. pyflakes), install it OUTSIDE
the runtime:
`E:\Dev\python-embed\python.exe -m pip install --target <dir outside the runtime> <tool>`
and wire it via `sys.path.insert` in the audit script (the embedded `._pth`
ignores PYTHONPATH). Environment reference snapshot:
`docs/refactoring/audits/env-baseline_q-a.txt`. History: pyflakes statics
have used an external `--target` library since Batch #8.15; the runtime copy
(4.0.3, 2026-10-23) was an accepted one-time deviation.
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

### Batch workflow: coordinator / executor (role discipline)
The agent is ONLY an executor. The coordinator (Dmitry) reviews reports, issues the
go/no-go verdict, plans the next stages, and writes the per-batch prompts.
* A new batch (including any implementation/removal batch) starts ONLY on Dmitry's
  explicit command AND with Dmitry's prompt file. No prompt — no start. "Proceeding to
  the next step in the agreed order" is NOT a start command.
* After a batch report is delivered, the agent stops and waits for the coordinator's
  verdict; it does not plan, schedule, or begin the next batch on its own.
* `git push` is executed ONLY on Dmitry's explicit command. Commits stay local until
  that command.
* Decisions recorded in a report (e.g. answers to the report's questions) authorize the
  content of a future batch, not its start.

### Executor turn discipline (no silent stops) — Dmitry's note 2026-10-20
Observed failure mode: the agent drafted long artifact text in a chat message and ended the
turn without the file-edit call — a text-only message ends the agent turn, which reads as a
silent stop and requires a manual "продолжай" to resume. Rules:
* Long artifact text (report sections, BACKLOG/PROJECT_STATUS blocks, doc paragraphs) is
  applied with file tools (Edit/Write) in the same turn; a "draft in the message" is NOT
  delivery. Plan → apply, never plan → stop.
* A turn that ends with a draft/plan and no tool call is a stall: the agent self-resumes by
  applying the artifact immediately, without waiting for a user prompt.
* Long-running probes (background task, GUI suite, worktree runs) are announced in the
  message before ending the turn: what was started, that the agent awaits its completion
  notification, expected duration — pauses are labeled, never silent.
* Commands expected to exceed 120 s (app instantiation 1–2 min, 16-stage offscreen suites)
  run via `run_in_background` (or with an explicit larger timeout) and are reported as such.
* After tool-call-only chains, end the turn with a visible status line.

### Temporary files and test artifacts
Use the dedicated project temporary workspace:
`E:\Dev\Work_temp\SupervertalerPortable\`
Do not use the following locations for project-generated temporary files or test artifacts unless the task explicitly requires it:
* `%TEMP%`;
* `%TMP%`;
* `%LOCALAPPDATA%\Temp`;
* the user's profile directories;
* system-wide temporary directories.
Each independent task, test run, or work stage must have its own subdirectory under:
`E:\Dev\Work_temp\SupervertalerPortable\`
Use descriptive stage-specific directories, for example:
`E:\Dev\Work_temp\SupervertalerPortable\analysis\`
`E:\Dev\Work_temp\SupervertalerPortable\translation\`
`E:\Dev\Work_temp\SupervertalerPortable\refactoring\`
`E:\Dev\Work_temp\SupervertalerPortable\tests\`
For repeated or potentially conflicting runs, create a unique run subdirectory, for example:
`E:\Dev\Work_temp\SupervertalerPortable\tests\run-001\`
Do not reuse the same temporary directory for unrelated stages when doing so could mix artifacts.
Keep temporary artifacts that may be useful for debugging, comparison, or verification until the current task has been successfully completed.
Temporary artifacts may be deleted after successful completion when they are no longer needed and are not required for reproducibility or debugging.
### Test build for manual-test scenarios
Since 2026-10-31, manual test-build scenarios (`T*.x` from batch reports) run against:
`D:\Supervertaler_clean\` — an UNPACKED DISTRIBUTION from
`docs/templates/make_portable_zip.bat` (zip `supervertaler-portable_20261031_1843.zip`,
product code = HEAD after Batch P1.8; Dmitry's decision, T-P1.8a/T-P1.8b confirmed on it).
Layout: `start.bat` + `python-embed\` (with the `_pth` patch: `..\SupervertalerPortable`,
`Lib\site-packages`) + `SupervertalerPortable\` (code only: Supervertaler.py, assets,
modules, pyproject.toml, requirements.txt, setup.py, translations, user_data; no .git,
no docs, no dev tooling).
Rules:
* The build has NO nested `.git` and NO profile redirect: `start.bat` (QP1.12) sets only
  `TEMP/TMP` and `PYTHONPYCACHEPREFIX` inside the build root — all data lives in
  `<build root>\Supervertaler\` plus the state-root service files (`quicktrans.ini`,
  `last_directory.json`) in the build root. `C:\Users\Dmitry` profile stays untouched
  except what the user saves explicitly (Documents etc.). The product writes no registry
  (verified by the P1.8 battery M1–M4).
* Rebuilding the test build = re-running `make_portable_zip.bat` (self-verifying: `_pth`
  smoke import before packing) and unpacking the fresh zip — a separate decision by
  Dmitry per batch, or on his command.
* Code validation (py_compile, AST, pyflakes, offscreen probes) is still executed in the
  repository `E:\Dev\SupervertalerPortable` with the `E:\Dev\python-embed` runtime; the
  seam `SUPERVERTALER_DATA_ROOT` isolates probe runs (AGENTS «Data paths» section).
* Unlike the OLD test build, this distrib's `python-embed` does NOT contain
  PyQt6-WebEngine (same as `E:\Dev\python-embed`): Web Resources runs in fallback mode.
  Adding WebEngine to the distrib is a separate build decision.
* HISTORICAL (2026-10-03 … 2026-10-31): the former test build
  `D:\SupervertalerPortable_test\` (frozen repo `.git` `960be5d8`, profile-redirecting
  `start.bat`, bundled PyQt6-WebEngine ≈340 MB) is superseded by `D:\Supervertaler_clean\`
  as of the P1.8 portability final; its profile-redirect insurance is retired by QP1.12.
### Environment variables
Do not permanently modify global Windows user or system environment variables merely to perform a project task.
When a project command or test needs explicit temporary directories, set `TEMP` and `TMP` for that process to the appropriate stage-specific directory under:
`E:\Dev\Work_temp\SupervertalerPortable\`
For example:
```bat
set "TEMP=E:\Dev\Work_temp\SupervertalerPortable\tests\run-001"
set "TMP=E:\Dev\Work_temp\SupervertalerPortable\tests\run-001"
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
   `E:\Dev\Work_temp\SupervertalerPortable\`
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

### Data paths and the test seam (Batch P1-B, P1.3)
Since Batch P1-B the single source of data-path resolution is
`modules/portable_paths.py` (the build root). Priority, fixed:
1. env `SUPERVERTALER_DATA_ROOT` (must be ABSOLUTE; relative raises ValueError)
   → data live in `<env>\Supervertaler\`;
2. dev flag `.supervertaler.local` next to the code (repo root)
   → `<repo>\user_data_private\`;
3. otherwise the build root → `<build_root>\Supervertaler\` (build root =
   parents[2] of `modules/portable_paths.py`, i.e. the dir containing the
   code repo folder). `state_root()` = build root (service files, P1-C/P1.6).
The old pointer file (`config.json` with `user_data_path`), the
`~/Supervertaler` default and the Settings group "Data Folder Location" are
removed: the app never reads or writes the real user profile for data paths.
* EVERY new GUI probe / suite run MUST set `SUPERVERTALER_DATA_ROOT` to the
  isolated profile directory (the same dir that is set as USERPROFILE/HOME),
  so the seeded `<iso>\Supervertaler` keeps matching the app's data root.
  USERPROFILE/APPDATA/LOCALAPPDATA/HOME stay pointed at (empty) isolated
  dirs as the negative control: nothing may appear there.
* Pre-P1-B probe copies (batch-p1a_*, b8-15, g32*, ...) seed a config.json
  pointer that the new code ignores — they are HISTORICAL, do not rerun them
  on the new code. Current suite copies: `batch-p1b_*` (generator:
  `batch-p1b_make_probe_copies.py`; runner: `batch-p1b_run_full.sh`, which
  self-seeds stage dirs and regress fixtures from
  `docs/refactoring/audits/fixtures/regress_inputs/`).

### Path and tooling quirks (Git Bash on Windows)
* The embedded Python does not understand Git Bash `/tmp` paths (they map to
  `D:\Temp`). Pass explicit `E:\Dev\Work_temp\SupervertalerPortable\...` paths to Python
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
* After each GUI test process, clean up leftover `python.exe`/`java.exe` from
  that specific run before the next run: the app spawns an Okapi sidecar
  subprocess, and test scripts that exit via `os._exit()` leave it orphaned.
  **Never kill by image name.** `taskkill /F /IM python.exe` (and the `java.exe`
  equivalent) also kills the user's unrelated interpreters, IDE servers and
  language daemons. Enumerate candidates with their full command lines first
  (PowerShell: `Get-CimInstance Win32_Process -Filter "Name='python.exe' or
  Name='java.exe'" | Select-Object ProcessId, CommandLine`), keep only PIDs
  whose command line belongs to this session's run (the probe script path, the
  stage directory under `E:\Dev\Work_temp\SupervertalerPortable\`, the `python-embed`
  interpreter, the sidecar jar), kill exactly those PIDs with
  `taskkill /F /PID <pid>`, and leave every unmatched process running.
  Report the survivor list in the batch log.

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

### Counting and baseline conventions (Batch #8.13, Dmitry's rules)
* py_compile is reported as TWO numbers:
  * canonical baseline: only code outside `docs/` (on `f804d447` it was 115) —
    does not grow from audit scripts that each batch commits to
    `docs/refactoring/audits/`;
  * reference: the total count including scripts (127 after 8.12 audits).
  Before/after comparisons always run on the same file set; the pass criterion
  is one: 0 errors.
* The canonical Tools-smoke baseline table is
  `docs/refactoring/audits/batch8-13_code_tools_smoke.py` (42 items, no
  gettext entries, Dmitry's decision). `batch8-12_code_tools_smoke.py` is a
  historical baseline log — do not modify it. Batches 8.15, 8.18 and later
  take their smoke baseline from the 8.13 table
  (canonical baseline log: `batch8-13_code_smoke_baseline813.log`).

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

## Manual test instructions for the project owner
The owner is not a programmer. Every manual test (T-xxx) in a report must be written so it can be done without reading code:
1. Goal in one sentence.
2. Preconditions: server/model to use (name), profile settings to change, and how to restore them afterwards.
3. Exact steps with menu paths as shown in the UI (not internal names), and a ready test file with its full path if a file is needed.
4. Expected result: where to look (console / panel / file / server log) and the exact text or behaviour to expect.
5. What counts as a failure.
Do not use internal terms (variable names, widget class names, batch codes) without explaining them.
Keep the number of mandatory tests small (aim for 3-5). Anything that needs a special setup or rarely used feature is marked "optional / covered by probe X" with the probe named.
Put the mandatory tests first and the optional ones in a separate list.
