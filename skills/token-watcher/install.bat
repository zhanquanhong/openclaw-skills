@echo off
chcp 65001 >nul
REM ================================================
REM  Token Watcher 一键安装脚本 (Windows)
REM
REM  用法:
REM     cd skills\token-watcher
REM     install.bat
REM
REM  安装完成后:
REM     token-watcher dashboard           启动 Web Dashboard (默认端口 8100)
REM     token-watcher dashboard --port 8101   指定端口
REM     token-watcher stats               查看统计摘要
REM     token-watcher report              生成 HTML 报告
REM ================================================

setlocal enabledelayedexpansion
set "SKILL_DIR=%~dp0"
set "SKILL_DIR=%SKILL_DIR:~0,-1%"

echo ============================================
echo   📦 Token Watcher 一键安装
echo ============================================
echo.

REM ── 1. 检测 Python ──────────────────────────────────

set "PYTHON="
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON=python3"
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=1-3 delims=. " %%a in ('python --version 2^>^&1') do (
            if %%b geq 8 set "PYTHON=python"
            if %%b geq 10 set "PYTHON=python"
        )
    )
)

if "%PYTHON%"=="" (
    echo ❌ 未找到 Python，请先安装 Python 3.8+
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python: 
%PYTHON% --version

REM ── 2. 安装依赖 ─────────────────────────────────────

echo.
echo 📥 安装 Python 依赖...
%PYTHON% -m pip install -q --upgrade pip 2>nul
%PYTHON% -m pip install -q -r "%SKILL_DIR%\requirements.txt"
echo ✅ 依赖安装完成

REM ── 3. 创建启动脚本 ─────────────────────────────────

set "BAT_PATH=%SKILL_DIR%\token-watcher.bat"
(
echo @echo off
echo chcp 65001 ^>nul
echo cd /d "%SKILL_DIR%"
echo %PYTHON% -m src.main %%*
) > "%BAT_PATH%"

echo.
echo ✅ 启动脚本已创建: %BAT_PATH%

REM 询问是否加入 PATH
set "ADD_PATH="
set /p ADD_PATH="🔗 是否将技能目录加入 PATH？(Y/n): "
if /i "%ADD_PATH%"=="Y" (
    setx PATH "%PATH%;%SKILL_DIR%" >nul
    echo ✅ 已加入 PATH，重启终端后可直接使用 token-watcher
) else (
    echo.
    echo ℹ️  使用方式：
    echo    方法1：将 %SKILL_DIR% 加入系统 PATH
    echo    方法2：直接使用完整路径 "%SKILL_DIR%\token-watcher.bat"
    echo    方法3：cd 到技能目录后运行 token-watcher.bat
)

REM ── 4. 完成 ─────────────────────────────────────────

echo.
echo ============================================
echo   ✅ Token Watcher 安装完成！
echo ============================================
echo.
echo 快速启动:
echo   token-watcher dashboard
echo.
echo 指定端口:
echo   token-watcher dashboard --port 8101
echo.
echo 查看统计:
echo   token-watcher stats
echo.
echo 生成报告:
echo   token-watcher report
echo.
echo 打开浏览器访问 http://localhost:8100 即可查看
echo.

pause
