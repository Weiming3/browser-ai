@echo off
chcp 65001 >nul
cd /d "%~dp0"
python browser_ai.py list
pause