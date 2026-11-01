@echo off
rem ============================================================
rem Supervertaler portable build - PACKAGER (Batch P2.4)
rem Assembles the portable build root and packs it into a REAL
rem ZIP archive (deflate via Python zipfile - not bsdtar: bsdtar -a
rem writes an uncompressed tar under a .zip name, P2.0 Finding 1).
rem The zip can be unpacked anywhere: start.bat is then the only
rem entry point.
rem
rem Runtime (P2.4): the shipped python-embed is BUILT from the
rem official embeddable zip + requirements.lock via a wheelhouse.
rem The dev runtime E:\Dev\python-embed is NEVER copied into the
rem distributive - it only executes this build script (orchestrator)
rem and, when the wheelhouse is incomplete, runs `pip download`
rem (read-only). No network is needed when the wheelhouse is full.
rem
rem Zip layout (= build root):
rem   start.bat                 launcher (docs/templates/start.bat)
rem   python-embed\             embedded runtime, built from
rem                             EMBED_ZIP + requirements.lock,
rem                             python313._pth patched
rem                             (..\\SupervertalerPortable + Lib\\site-packages)
rem   SupervertalerPortable\    application code, clean copy
rem                             (no .git/docs/__pycache__/dev data)
rem The data folder Supervertaler\\, temp\\ and pycache\\ are created
rem on first run by the app / start.bat - not shipped in the zip.
rem
rem Usage:  make_portable_zip.bat [output-dir]
rem         (default output: E:\\Dev\\Work_temp\\SupervertalerPortable\\build)
rem ============================================================
setlocal EnableExtensions

set "REPO=%~dp0..\.."
pushd "%REPO%" 2>nul
set "REPO=%CD%"
popd
set "HELPER=%REPO%\docs\templates\packaging_helper.py"

rem --- config -------------------------------------------------
rem ORCHESTRATOR: the dev runtime only RUNS the build (helper script,
rem pip download into the wheelhouse when needed). Its content is not shipped.
set "RUNTIME=E:\Dev\python-embed"
rem Official embeddable CPython 3.13.15 (same version as the verified P2.1
rem distributive) and the pip bootstrap script - local copies:
set "EMBED_ZIP=E:\Dev\python-3.13.15-embed-amd64.zip"
set "GETPIP=E:\Dev\python-embed\get-pip.py"
rem Wheel cache OUTSIDE the repo; filled once by `pip download`, reused
rem offline by every later build:
set "WHEELHOUSE=E:\Dev\wheelhouse"
set "LOCK=%REPO%\requirements.lock"
set "OUTDIR=%~1"
if "%OUTDIR%"=="" set "OUTDIR=E:\Dev\Work_temp\SupervertalerPortable\build"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmm"') do set "TS=%%i"
set "ZIPFILE=%OUTDIR%\supervertaler-portable_%TS%.zip"
set "STAGE=%OUTDIR%\stage_%TS%"

rem --- preflight ----------------------------------------------
if not exist "%REPO%\Supervertaler.py" (
  echo [FAIL] Supervertaler.py not found in "%REPO%" - wrong repo layout? & goto :fail
)
if not exist "%EMBED_ZIP%" (
  echo [FAIL] Embeddable zip not found: "%EMBED_ZIP%" & goto :fail
)
if not exist "%GETPIP%" (
  echo [FAIL] get-pip.py not found: "%GETPIP%" & goto :fail
)
if not exist "%LOCK%" (
  echo [FAIL] requirements.lock not found: "%LOCK%" & goto :fail
)
if not exist "%REPO%\docs\templates\start.bat" (
  echo [FAIL] docs\templates\start.bat missing in the repo & goto :fail
)
if not exist "%HELPER%" (
  echo [FAIL] packaging helper missing: "%HELPER%" & goto :fail
)
echo [1/6] Preparing stage: %STAGE%
if exist "%STAGE%" rd /s /q "%STAGE%"
mkdir "%STAGE%" 2>nul || (echo [FAIL] cannot create stage dir & goto :fail)

rem --- code copy (clean, no VCS/docs/dev data/bytecode) --------
echo [2/6] Copying application code...
robocopy "%REPO%" "%STAGE%\SupervertalerPortable" /E ^
  /XD .git .zcode docs __pycache__ user_data_private .pytest_cache okapi-sidecar ^
  /XF .zcodeignore .supervertaler.local *.pyc *.log /NFL /NDL /NJH /NJS
if errorlevel 8 (echo [FAIL] robocopy code failed & goto :fail)
if not exist "%STAGE%\SupervertalerPortable\Supervertaler.py" (
  echo [FAIL] code copy incomplete & goto :fail
)
rem Dev docs and dev tooling out of the distrib (T-P1.8a dry run 2026-10-31):
rem top-level *.md, git housekeeping, scripts\, tools\. Kept: pyproject.toml
rem (read by Supervertaler.py:57 for the version fallback), setup.py,
rem requirements.txt, requirements.lock, requirements-optional.txt,
rem assets\, translations\, user_data\.
del /q "%STAGE%\SupervertalerPortable\*.md" 2>nul
del /q "%STAGE%\SupervertalerPortable\.gitattributes" 2>nul
del /q "%STAGE%\SupervertalerPortable\.gitignore" 2>nul
rd /s /q "%STAGE%\SupervertalerPortable\scripts" 2>nul
rd /s /q "%STAGE%\SupervertalerPortable\tools" 2>nul

rem --- runtime BUILT from lock (P2.4): embed zip unpack + _pth +
rem bootstrap pip offline from the wheelhouse + install requirements.lock
rem + dist-info == lock+pip gate + forbidden gate. On failure the stage is
rem KEPT. The dev runtime is only the orchestrator of this step.
echo [3/6] Building runtime from %EMBED_ZIP% + requirements.lock (first run fills the wheelhouse)...
"%RUNTIME%\python.exe" "%HELPER%" runtime "%STAGE%" "%EMBED_ZIP%" "%GETPIP%" "%WHEELHOUSE%" "%LOCK%"
if errorlevel 1 (echo [FAIL] runtime build failed & goto :fail)

rem --- launcher -------------------------------------------------
echo [4/6] Adding start.bat...
copy /y "%REPO%\docs\templates\start.bat" "%STAGE%\start.bat" >nul || (echo [FAIL] start.bat copy failed & goto :fail)

rem --- smoke: _pth patch must let python find code + packages ----
echo [5/6] Smoke test (monolith + key modules through the patched _pth)...
rem PYTHONDONTWRITEBYTECODE: the smoke import must not leave __pycache__
rem in the staged code folder (bug found by T-P1.8a dry run 2026-10-31).
pushd "%STAGE%"
set "PYTHONDONTWRITEBYTECODE=1"
rem Smoke logs go to OUTDIR (build evidence, never into the zip).
"python-embed\python.exe" -c "import Supervertaler; print('IMPORT OK')" >nul 2>"%OUTDIR%\smoke_%TS%.err"
set "SMOKE_RC=%ERRORLEVEL%"
if "%SMOKE_RC%"=="0" (
  "python-embed\python.exe" "%HELPER%" importsmoke >"%OUTDIR%\importsmoke_%TS%.txt" 2>&1
  if errorlevel 1 set "SMOKE_RC=1"
)
popd
if not "%SMOKE_RC%"=="0" (
  echo [FAIL] smoke import failed - see "%OUTDIR%\smoke_%TS%.err" / importsmoke_%TS%.txt & goto :fail
)

rem --- pack: REAL zip (deflate) via Python zipfile, then verify ---
echo [6/6] Packing ZIP (deflate, ~40-60 s)...
mkdir "%OUTDIR%" 2>nul
"%RUNTIME%\python.exe" "%HELPER%" zip "%STAGE%" "%ZIPFILE%"
if errorlevel 1 (echo [FAIL] zip packing/verification failed & goto :fail)
rd /s /q "%STAGE%"

for %%Z in ("%ZIPFILE%") do echo [DONE] %%~zZ bytes: %ZIPFILE%
echo Unpack the zip anywhere and run start.bat inside.
rem Keep the console open when launched by double-click (T-P2.1a note):
rem without it the window closes before the DONE lines can be read.
pause
endlocal
exit /b 0

:fail
echo [DONE-WITH-ERRORS] stage kept for inspection: %STAGE%
pause
endlocal
exit /b 1
