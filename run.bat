@echo off
setlocal EnableExtensions

pushd "%~dp0" >nul 2>&1
if errorlevel 1 (
    echo Failed to enter script directory: %~dp0 1>&2
    exit /b 1
)
chcp 65001 >nul
set "PYTHONUTF8=1"

set "SCRIPT_DIR=%CD%"
set "VENV_DIR=%SCRIPT_DIR%\.venv-win"
set "PYTHON_BIN=%VENV_DIR%\Scripts\python.exe"

if not exist "%PYTHON_BIN%" (
    call :find_bootstrap_python
    if errorlevel 1 goto :finish
    echo Creating local Windows virtual environment in .venv-win... 1>&2
    call :run_bootstrap -m venv "%VENV_DIR%"
    if errorlevel 1 goto :finish
)

"%PYTHON_BIN%" -c "import dotenv, openai" >nul 2>&1
if errorlevel 1 (
    echo Installing Python dependencies into .venv-win... 1>&2
    "%PYTHON_BIN%" -m ensurepip --upgrade >nul 2>&1
    "%PYTHON_BIN%" -m pip install -r "%SCRIPT_DIR%\requirements.txt"
    if errorlevel 1 goto :finish
)

if "%~1"=="" (
    "%PYTHON_BIN%" .\play_match.py --mode openrouter --rounds 2
) else (
    "%PYTHON_BIN%" .\play_match.py %*
)
goto :finish

:find_bootstrap_python
where py >nul 2>&1
if not errorlevel 1 (
    set "BOOTSTRAP_EXE=py"
    set "BOOTSTRAP_ARG=-3"
    exit /b 0
)

where python >nul 2>&1
if not errorlevel 1 (
    set "BOOTSTRAP_EXE=python"
    set "BOOTSTRAP_ARG="
    exit /b 0
)

echo Python not found on Windows. Install Python 3 or the py launcher. 1>&2
exit /b 127

:run_bootstrap
if defined BOOTSTRAP_ARG (
    "%BOOTSTRAP_EXE%" %BOOTSTRAP_ARG% %*
) else (
    "%BOOTSTRAP_EXE%" %*
)
exit /b %errorlevel%

:finish
set "EXITCODE=%ERRORLEVEL%"
popd >nul 2>&1
exit /b %EXITCODE%
