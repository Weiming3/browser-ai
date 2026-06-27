@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   登录AI站点 - 持久化保存登录状态
echo   Login to AI sites - persistent session
echo ========================================
echo.
python browser_ai.py login
echo.
pause