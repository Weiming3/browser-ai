@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   登录豆包 / Login to Doubao
echo ========================================
echo.
python browser_ai.py login doubao
echo.
pause