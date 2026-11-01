@echo off
rem ============================================================
rem Supervertaler portable build - PACKAGER (Batch P2.1)
rem Assembles the portable build root and packs it into a REAL
rem ZIP archive (deflate via Python zipfile - not bsdtar: bsdtar -a
rem writes an uncompressed tar under a .zip name, P2.0 Finding 1).
rem The zip can be unpacked anywhere: start.bat is then the only
rem entry point.
rem
rem Zip layout (= build root):
rem   start.bat                 launcher (docs/templates/start.bat)
rem   python-embed\             embedded runtime, python313._pth patched
rem                             (..\\SupervertalerPortable + Lib\\site-packages),
rem                             dev-junk excluded (packaging_helper.py prune)
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
set "RUNTIME=E:\Dev\python-embed"
set "OUTDIR=%~1"
if "%OUTDIR%"=="" set "OUTDIR=E:\Dev\Work_temp\SupervertalerPortable\build"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmm"') do set "TS=%%i"
set "ZIPFILE=%OUTDIR%\supervertaler-portable_%TS%.zip"
set "STAGE=%OUTDIR%\stage_%TS%"

rem --- preflight ----------------------------------------------
if not exist "%REPO%\Supervertaler.py" (
  echo [FAIL] Supervertaler.py not found in "%REPO%" - wrong repo layout? & goto :fail
)
if not exist "%RUNTIME%\python.exe" (
  echo [FAIL] Runtime not found: "%RUNTIME%\python.exe" & goto :fail
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
rem requirements.txt, assets\, translations\, user_data\.
del /q "%STAGE%\SupervertalerPortable\*.md" 2>nul
del /q "%STAGE%\SupervertalerPortable\.gitattributes" 2>nul
del /q "%STAGE%\SupervertalerPortable\.gitignore" 2>nul
rd /s /q "%STAGE%\SupervertalerPortable\scripts" 2>nul
rd /s /q "%STAGE%\SupervertalerPortable\tools" 2>nul

rem --- runtime copy + _pth patch (P1.8 Finding 1) ---------------
echo [3/6] Copying embedded runtime (this takes a minute)...
robocopy "%RUNTIME%" "%STAGE%\python-embed" /E /XD __pycache__ /NFL /NDL /NJH /NJS
if errorlevel 8 (echo [FAIL] robocopy runtime failed & goto :fail)
> "%STAGE%\python-embed\python313._pth" (
  echo python313.zip
  echo .
  echo ..\SupervertalerPortable
  echo Lib\site-packages
  echo import site
)
rem Dev junk out of the distributive COPY (P2.0 verdict item 4): pygments,
rem pytest stack, pyflakes, chardet, get-pip.py (+ dist-info). pip KEPT.
rem The exclusion list lives at the top of packaging_helper.py; the dev
rem runtime E:\Dev\python-embed itself is never touched.
"%RUNTIME%\python.exe" "%HELPER%" prune "%STAGE%\python-embed"
if errorlevel 1 (echo [FAIL] runtime prune failed & goto :fail)

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
  echo [FAIL] smoke import failed - see "%STAGE%\smoke_err.txt" / importsmoke_out.txt & goto :fail
)

rem --- pack: REAL zip (deflate) via Python zipfile, then verify ---
echo [6/6] Packing ZIP (deflate, ~40-60 s)...
mkdir "%OUTDIR%" 2>nul
"%RUNTIME%\python.exe" "%HELPER%" zip "%STAGE%" "%ZIPFILE%"
if errorlevel 1 (echo [FAIL] zip packing/verification failed & goto :fail)
rd /s /q "%STAGE%"

echo [DONE] %ZIPFILE%
echo Unpack the zip anywhere and run start.bat inside.
endlocal
exit /b 0

:fail
echo [DONE-WITH-ERRORS] stage kept for inspection: %STAGE%
endlocal
exit /b 1
