@echo off
"%~dp0..\.venv-ems\Scripts\python.exe" "%~dp0start.py"
if errorlevel 1 pause
