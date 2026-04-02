@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1

if "%~1"=="" (
    python .\play_match.py --mode openrouter --rounds 2
) else (
    python .\play_match.py %*
)
