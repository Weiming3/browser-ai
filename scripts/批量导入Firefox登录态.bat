@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   批量导入Firefox登录态
echo   Batch import Firefox cookies
echo ========================================
echo.
echo [!] 该脚本会读取你的Firefox cookies并写入本地profiles目录。
echo [!] 输出目录已被 .gitignore 排除，不会被提交。
echo [!] This script reads your local Firefox cookies and writes them
echo [!] to the local profiles directory (already gitignored).
echo.
echo 选择模式 / Select mode:
echo   1. 预览模式 / Dry run (--dry-run)
echo   2. 实际导入 / Actually import
echo.
set /p mode=输入 1 或 2 / Enter 1 or 2:
if "%mode%"=="1" (
    python import_firefox_login.py --dry-run
) else if "%mode%"=="2" (
    python import_firefox_login.py
) else (
    echo 无效选择 / Invalid selection
)
pause