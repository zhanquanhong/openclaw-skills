@echo off
chcp 65001 >nul 2>&1
setlocal

REM wbs-skill v4.0 — 一键安装脚本
REM Windows
REM
REM 使用方式：
REM   双击 install.bat 或命令行执行
REM
REM 安装内容：
REM   1. 检查 Python 3.8+ 环境
REM   2. 创建虚拟环境 .venv
REM   3. 安装所有依赖
REM   4. 创建 input/ output/ 目录

echo ╔══════════════════════════════════════════╗
echo ║  wbs-skill v4.0 — 安装向导               ║
echo ╚══════════════════════════════════════════╝
echo.

REM ========== 步骤 1：检查 Python ==========
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python
    echo.
    echo 请先安装 Python 3.8+：
    echo   下载：https://www.python.org/downloads/
    echo   安装时勾选 "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo ✅ Python 已安装
echo.

REM ========== 步骤 2：创建虚拟环境 ==========
echo [2/5] 创建虚拟环境...
if exist ".venv" (
    echo ⏭️ 已存在，跳过
) else (
    python -m venv .venv
    echo ✅ 完成
)
echo.

REM ========== 步骤 3：安装依赖 ==========
echo [3/5] 安装依赖（约 30 秒）...
if not exist "requirements.txt" (
    echo ❌ requirements.txt 不存在
    pause
    exit /b 1
)
call .venv\Scripts\python.exe -m pip install --upgrade pip -q >nul 2>&1
call .venv\Scripts\pip.exe install -r requirements.txt -q
if errorlevel 1 (
    echo.
    echo ❌ 依赖安装失败
    echo.
    echo 尝试手动安装：
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo ✅ 完成
echo.

REM ========== 步骤 4：创建目录 ==========
echo [4/5] 创建 input/ output/ 目录...
if not exist "input" mkdir input
if not exist "output" mkdir output
echo ✅ 完成
echo.

REM ========== 步骤 5：完成 ==========
echo [5/5] 安装完成
echo.
echo ╔══════════════════════════════════════════╗
echo ║  ✅ 安装完成！                          ║
echo ╚══════════════════════════════════════════╝
echo.
echo 使用方法：
echo   1. 把技术方案文档放到 input/ 目录
echo   2. 执行：wbs.bat input\技术方案.pdf
echo.
echo 支持自然语言：
echo   wbs.bat 技术方案.pdf "按周分解，重点标出接口任务"
echo.
pause
