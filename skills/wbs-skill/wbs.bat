@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM wbs-skill v4.0 — 自然语言 WBS 生成器
REM Windows 入口脚本
REM
REM 使用方式：
REM   wbs.bat <文件路径>                    REM 默认模式
REM   wbs.bat <文件路径> "需求描述"         REM 自然语言模式
REM
REM 示例：
REM   wbs.bat input\技术方案.pdf
REM   wbs.bat "C:\Users\xxx\Desktop\方案.pdf" "按周分解"
REM
REM 支持格式：PDF、DOCX、Markdown (.md)

set SCRIPT_DIR=%~dp0
set VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe

REM ========== 环境检查 ==========
if not exist "%VENV_PYTHON%" (
    echo ❌ 虚拟环境不存在，请先运行安装脚本：
    echo    install.bat
    echo.
    echo 双击 install.bat 即可完成安装
    exit /b 1
)

REM ========== 参数检查 ==========
if "%~1"=="" (
    echo ╔══════════════════════════════════════╗
    echo ║  wbs-skill v4.0 — WBS 任务分解器     ║
    echo ╚══════════════════════════════════════╝
    echo.
    echo 用法：
    echo   wbs.bat ^<文件路径^>                    # 默认模式
    echo   wbs.bat ^<文件路径^> "需求描述"         # 自然语言模式
    echo.
    echo 示例：
    echo   wbs.bat input\技术方案.pdf
    echo   wbs.bat "C:\Users\xxx\Desktop\方案.pdf" "按周分解"
    echo.
    echo 支持的格式：PDF、DOCX、Markdown (.md)
    exit /b 0
)

set FILE_PATH=%~1
set INTENT=%~2
set EXTRA_ARGS=%~3

REM ========== 文件路径处理 ==========
if not exist "%FILE_PATH%" (
    set INPUT_PATH=%SCRIPT_DIR%input\%FILE_PATH%
    if exist "!INPUT_PATH!" (
        set FILE_PATH=!INPUT_PATH!
        echo 📂 从 input/ 目录找到文件
    ) else (
        echo ❌ 文件不存在：%FILE_PATH%
        echo.
        echo 提示：
        echo   1. 检查文件路径是否正确
        echo   2. 将文件放到 input/ 目录下，然后执行：wbs.bat %FILE_PATH%
        echo   3. 使用绝对路径：wbs.bat "C:\完整\路径\%FILE_PATH%"
        exit /b 2
    )
)

REM ========== 执行 ==========
echo 🚀 开始生成 WBS...

if defined INTENT (
    if defined EXTRA_ARGS (
        "%VENV_PYTHON%" "%SCRIPT_DIR%src\wbs_cli.py" --file "%FILE_PATH%" --intent "%INTENT%" %EXTRA_ARGS%
    ) else (
        "%VENV_PYTHON%" "%SCRIPT_DIR%src\wbs_cli.py" --file "%FILE_PATH%" --intent "%INTENT%"
    )
) else (
    if defined EXTRA_ARGS (
        "%VENV_PYTHON%" "%SCRIPT_DIR%src\wbs_cli.py" --file "%FILE_PATH%" %EXTRA_ARGS%
    ) else (
        "%VENV_PYTHON%" "%SCRIPT_DIR%src\wbs_cli.py" --file "%FILE_PATH%"
    )
)

set EXIT_CODE=%errorlevel%

if %EXIT_CODE% equ 0 (
    echo.
    echo ✅ WBS 生成完成！
    echo 📁 结果文件在：%SCRIPT_DIR%output\
) else (
    echo.
    echo ❌ WBS 生成失败（错误码：%EXIT_CODE%）
    if %EXIT_CODE% equ 1 (
        echo 可能原因：环境配置问题，请运行 install.bat 检查
    ) else if %EXIT_CODE% equ 2 (
        echo 可能原因：文件不存在或格式不支持
    ) else if %EXIT_CODE% equ 3 (
        echo 可能原因：文档解析失败，检查文档是否为扫描件
    ) else if %EXIT_CODE% equ 4 (
        echo 可能原因：Excel 输出失败，检查 output/ 目录权限
    ) else (
        echo 请查看上方错误信息
    )
)

exit /b %EXIT_CODE%
