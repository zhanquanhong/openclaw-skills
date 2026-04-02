@echo off
chcp 65001 >nul
echo ==========================================
echo    TeamClaw Code Reviewer - Installer
echo    Version: v1.0.2
echo ==========================================
echo.

:: Check Python
echo [1/6] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python not found
    echo.
    echo Please install Python 3.8 or higher
    echo Download: https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% detected
echo.

:: Check version
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>nul
if errorlevel 1 (
    echo [ERROR] Python version too old, need 3.8+
    echo Current: %PYTHON_VERSION%
    pause
    exit /b 1
)
echo [OK] Python version compatible (3.8+)
echo.

:: Create workspace
echo [2/6] Creating workspace...
set WORKSPACE_DIR=%USERPROFILE%\.openclaw\workspace

if not exist "%WORKSPACE_DIR%" (
    mkdir "%WORKSPACE_DIR%"
    echo [OK] Created: %WORKSPACE_DIR%
) else (
    echo [OK] Directory exists: %WORKSPACE_DIR%
)

if not exist "%WORKSPACE_DIR%\scripts" mkdir "%WORKSPACE_DIR%\scripts"
if not exist "%WORKSPACE_DIR%\code-reports" mkdir "%WORKSPACE_DIR%\code-reports"
if not exist "%WORKSPACE_DIR%\idea-plugin" mkdir "%WORKSPACE_DIR%\idea-plugin"
if not exist "%WORKSPACE_DIR%\cursor-tasks" mkdir "%WORKSPACE_DIR%\cursor-tasks"
if not exist "%WORKSPACE_DIR%\docs" mkdir "%WORKSPACE_DIR%\docs"
echo.

:: Copy script files - Using simple copy command
echo [3/6] Copying script files...
set SCRIPT_DIR=%~dp0

echo   Copying scripts...
copy /Y /B "%SCRIPT_DIR%scripts\*.py" "%WORKSPACE_DIR%\scripts\" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Some script files failed to copy
) else (
    echo   [OK] scripts/
)

if exist "%SCRIPT_DIR%idea-plugin\" (
    echo   Copying idea-plugin...
    copy /Y /B "%SCRIPT_DIR%idea-plugin\*.xml" "%WORKSPACE_DIR%\idea-plugin\" >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] Some idea-plugin files failed to copy
    ) else (
        echo   [OK] idea-plugin/
    )
)

if exist "%SCRIPT_DIR%cursor-tasks\" (
    echo   Copying cursor-tasks...
    copy /Y /B "%SCRIPT_DIR%cursor-tasks\*.json" "%WORKSPACE_DIR%\cursor-tasks\" >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] Some cursor-tasks files failed to copy
    ) else (
        echo   [OK] cursor-tasks/
    )
)

if exist "%SCRIPT_DIR%docs\" (
    echo   Copying docs...
    copy /Y /B "%SCRIPT_DIR%docs\*.md" "%WORKSPACE_DIR%\docs\" >nul 2>&1
    if errorlevel 1 (
        echo   [WARN] Some docs files failed to copy
    ) else (
        echo   [OK] docs/
    )
)
echo [OK] Copy completed
echo.

:: Create launcher script
echo [4/6] Creating launcher script...
(
echo @echo off
echo chcp 65001 ^>nul
echo python "%WORKSPACE_DIR%\scripts\code-review-multi-agent.py" %%*
) > "%WORKSPACE_DIR%\code-review.bat"

echo [OK] Launcher created: %WORKSPACE_DIR%\code-review.bat
echo.

:: Configure IDEA - Auto detect all versions
echo [5/6] Configuring IntelliJ IDEA...
echo.

set IDEA_CONFIGURED=0

:: Detect IDEA directories
for /d %%d in (
    "%APPDATA%\JetBrains\IntelliJIdea*"
    "%APPDATA%\JetBrains\IdeaIC*"
) do (
    if exist "%%d" (
        echo [INFO] Found IDEA: %%~nd
        
        :: Create tools directory
        if not exist "%%d\tools" mkdir "%%d\tools"
        
        :: Copy config file
        if exist "%WORKSPACE_DIR%\idea-plugin\code-reviewer-external-tools.xml" (
            copy /Y "%WORKSPACE_DIR%\idea-plugin\code-reviewer-external-tools.xml" "%%d\tools\" >nul
            if errorlevel 1 (
                echo    [WARN] Failed to copy config
            ) else (
                echo    [OK] Config added to: %%d\tools\
                set IDEA_CONFIGURED=1
            )
        )
        echo.
    )
)

if %IDEA_CONFIGURED%==0 (
    echo [WARN] No IDEA installation detected
    echo.
    echo Manual configuration required:
    echo   1. Open IDEA
    echo   2. File - Settings - Tools - External Tools
    echo   3. Click Import icon
    echo   4. Select: %WORKSPACE_DIR%\idea-plugin\code-reviewer-external-tools.xml
    echo.
) else (
    echo [OK] IDEA configuration complete!
    echo.
    echo Next step:
    echo   Please restart all open IntelliJ IDEA instances
    echo   Right-click code file - External Tools - Code Review (Multi-Agent)
    echo.
)

:: Configure Cursor
echo [6/6] Configuring Cursor...
echo.

set CURSOR_CONFIG="%APPDATA%\Cursor\User"
if exist "%CURSOR_CONFIG%" (
    echo [INFO] Found Cursor config directory
    
    :: Create tasks directory
    if not exist "%CURSOR_CONFIG%\tasks" mkdir "%CURSOR_CONFIG%\tasks"
    
    :: Copy task config
    if exist "%WORKSPACE_DIR%\cursor-tasks\code-review.json" (
        copy /Y "%WORKSPACE_DIR%\cursor-tasks\code-review.json" "%CURSOR_CONFIG%\tasks\" >nul
        if errorlevel 1 (
            echo    [WARN] Failed to copy task config
        ) else (
            echo    [OK] Task config added to: %CURSOR_CONFIG%\tasks\
        )
        echo.
        echo [OK] Cursor configuration complete!
        echo.
        echo Usage:
        echo   1. Open Cursor
        echo   2. Ctrl+Shift+P - Tasks: Run Task - Code Review
        echo   3. Or right-click file - Run Task - Code Review
        echo.
    )
) else (
    echo [WARN] Cursor not detected
    echo.
    echo Cursor config path: %WORKSPACE_DIR%\cursor-tasks\code-review.json
    echo If using Cursor, manually copy to:
    echo   %APPDATA%\Cursor\User\tasks\
    echo.
)

:: Complete
echo ==========================================
echo    [SUCCESS] Installation Complete!
echo ==========================================
echo.
echo Usage:
echo.
echo   [IntelliJ IDEA]
echo     Restart IDEA, right-click code - External Tools - Code Review
echo.
echo   [Cursor]
echo     Ctrl+Shift+P - Tasks: Run Task - Code Review
echo.
echo   [Command Line]
echo     cd %WORKSPACE_DIR%
echo     code-review.bat your-file-path
echo.
echo Reports location:
echo   %WORKSPACE_DIR%\code-reports\
echo.
echo Documentation:
echo   %WORKSPACE_DIR%\docs\code-review-quickstart.md
echo.
echo ==========================================
echo.

:: Ask to open reports directory
set /p OPEN_REPORTS="Open reports directory now? (Y/N): "
if /i "%OPEN_REPORTS%"=="Y" (
    if not exist "%WORKSPACE_DIR%\code-reports" mkdir "%WORKSPACE_DIR%\code-reports"
    explorer "%WORKSPACE_DIR%\code-reports"
)

echo.
echo Thank you for using TeamClaw Code Reviewer!
echo.
pause
