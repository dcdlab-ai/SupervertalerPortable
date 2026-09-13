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
### Exceptions
The rules in this section may be overridden only when:
* the task explicitly requires another environment;
* a specific external tool cannot operate with the bundled runtime;
* the project itself explicitly requires another location.
When an exception is necessary, keep it limited to the affected command or process and do not permanently modify the project's standard environment.
