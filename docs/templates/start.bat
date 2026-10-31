@echo off
rem ============================================================
rem Supervertaler portable build - launcher template (Batch P1.8)
rem Place this file in the BUILD ROOT, next to:
rem   python-embed\            embedded Python runtime
rem   SupervertalerPortable\   application code (Supervertaler.py)
rem   Supervertaler\           data folder (created by the app on first run)
rem Everything the app writes stays inside this folder:
rem data -> Supervertaler\, %TEMP% transit files -> temp\,
rem Python bytecode cache -> pycache\, QuickTrans popup + last-directory
rem state -> quicktrans.ini / last_directory.json in this folder.
rem No registry keys are written; no USERPROFILE/APPDATA redirect is needed.
rem ============================================================
setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

rem %TEMP% inside the build root (RECON P1.0 section 1.5): AHK/PowerShell
rem send-copy scripts and other tempfile traffic stay portable.
if not exist "%ROOT%\temp" mkdir "%ROOT%\temp"
set "TEMP=%ROOT%\temp"
set "TMP=%ROOT%\temp"

rem Python bytecode cache inside the build root: keeps SupervertalerPortable\
rem byte-identical to the repository (no scattered __pycache__ folders).
if not exist "%ROOT%\pycache" mkdir "%ROOT%\pycache"
set "PYTHONPYCACHEPREFIX=%ROOT%\pycache"

rem No JAVA_HOME/PATH setup: the Windows Okapi sidecar ZIP bundles its own JRE.
rem No profile redirect (QP1.12): since P1.3-P1.6 the code itself writes only
rem inside the build root. If something ever appears outside it, that is a
rem regression - report it, do not mask it with a redirect.
cd /d "%ROOT%"
"%ROOT%\python-embed\python.exe" "%ROOT%\SupervertalerPortable\Supervertaler.py" %*
endlocal
