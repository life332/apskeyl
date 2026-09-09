@echo off
rem apskeyl: open window (server starts itself if not alive). ASCII only in this file.
cd /d "%~dp0.."
start "" "%~dp0..\.venv\Scripts\pythonw.exe" "%~dp0..\app\desktop.py"
