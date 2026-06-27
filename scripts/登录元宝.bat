@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   登录腾讯元宝 / Login to Yuanbao
echo ========================================
echo.
python browser_ai.py login yuanbao
echo.
pause