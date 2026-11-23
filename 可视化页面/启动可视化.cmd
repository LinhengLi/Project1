@echo off
setlocal
if exist "%~dp0..\.venv-ems\Scripts\python.exe" (
  "%~dp0..\.venv-ems\Scripts\python.exe" "%~dp0start.py" %*
) else (
  python "%~dp0start.py" %*
)
if errorlevel 1 pause
