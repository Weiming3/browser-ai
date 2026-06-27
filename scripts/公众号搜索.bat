@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   公众号文章搜索 / WeChat Article Search
echo ========================================
set /p kw=请输入关键词 / Enter keyword:
if "%kw%"=="" (
    echo 关键词不能为空 / Keyword required
    pause
    exit /b
)
python browser_ai.py weixin "%kw%"
pause