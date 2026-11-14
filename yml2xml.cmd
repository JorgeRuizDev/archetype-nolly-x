@echo off
chcp 65001 > nul
setlocal
set "SCRIPT_DIR=%~dp0"

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%preset_editor\yml2xml.py" %*
) else if exist "%SCRIPT_DIR%preset_editor\.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%preset_editor\.venv\Scripts\python.exe" "%SCRIPT_DIR%preset_editor\yml2xml.py" %*
) else (
    where uv >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        uv run python "%SCRIPT_DIR%preset_editor\yml2xml.py" %*
    ) else (
        python "%SCRIPT_DIR%preset_editor\yml2xml.py" %*
    )
)

