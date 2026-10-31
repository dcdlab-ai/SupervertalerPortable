@echo off
rem ============================================================
rem Supervertaler portable build - PACKAGER (Batch P1.8 follow-up)
rem Assembles the portable build root and packs it into a ZIP that
rem can be unpacked anywhere: start.bat is then the only entry point.
rem
rem Zip layout (= build root):
rem   start.bat                 launcher (docs/templates/start.bat)
rem   python-embed\             embedded runtime, python313._pth patched
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
echo [1/6] Preparing stage: %STAGE%
if exist "%STAGE%" rd /s /q "%STAGE%"
mkdir "%STAGE%" 2>nul || (echo [FAIL] cannot create stage dir & goto :fail)

rem --- code copy (clean, no VCS/docs/dev data/bytecode) --------
echo [2/6] Copying application code...
robocopy "%REPO%" "%STAGE%\SupervertalerPortable" /E ^
  /XD .git .zcode docs __pycache__ user_data_private .pytest_cache ^
  /XF .zcodeignore .supervertaler.local *.pyc *.log /NFL /NDL /NJH /NJS
if errorlevel 8 (echo [FAIL] robocopy code failed & goto :fail)
if not exist "%STAGE%\SupervertalerPortable\Supervertaler.py" (
  echo [FAIL] code copy incomplete & goto :fail
)

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

rem --- launcher -------------------------------------------------
echo [4/6] Adding start.bat...
copy /y "%REPO%\docs\templates\start.bat" "%STAGE%\start.bat" >nul || (echo [FAIL] start.bat copy failed & goto :fail)

rem --- smoke: the _pth patch must let python find the code ------
echo [5/6] Smoke test (import of the monolith through the patched _pth)...
pushd "%STAGE%"
"python-embed\python.exe" -c "import Supervertaler; print('IMPORT OK')" >nul 2>"%STAGE%\smoke_err.txt"
set "SMOKE_RC=%ERRORLEVEL%"
popd
if not "%SMOKE_RC%"=="0" (
  echo [FAIL] smoke import failed - see "%STAGE%\smoke_err.txt" & goto :fail
)

rem --- pack ------------------------------------------------------
echo [6/6] Packing ZIP...
mkdir "%OUTDIR%" 2>nul
rem bsdtar treats "E:\file.zip" as host:file - pass the archive name
rem RELATIVE via pushd to avoid the colon.
pushd "%OUTDIR%"
tar -a -cf "supervertaler-portable_%TS%.zip" -C "%STAGE%" start.bat python-embed SupervertalerPortable
set "TAR_RC=%ERRORLEVEL%"
popd
if not "%TAR_RC%"=="0" (echo [FAIL] tar packing failed & goto :fail)
rd /s /q "%STAGE%"

for %%Z in ("%ZIPFILE%") do echo [DONE] %%~zZ bytes: %ZIPFILE%
echo Unpack the zip anywhere and run start.bat inside.
endlocal
exit /b 0

:fail
echo [DONE-WITH-ERRORS] stage kept for inspection: %STAGE%
endlocal
exit /b 1
