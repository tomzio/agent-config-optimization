@echo off
REM OpenCode/OmO 配置切换工具 - Windows 批处理包装器
REM 用法: switch.bat [list|current|check|switch] [scheme_id]

set "SCHEMES_DIR=%~dp0"
set "PYTHON_CMD=python"

REM 尝试多种 Python 命令
where python >nul 2>&1 && set "PYTHON_CMD=python"
where python3 >nul 2>&1 && set "PYTHON_CMD=python3"
where py >nul 2>&1 && set "PYTHON_CMD=py -3"

"%PYTHON_CMD%" "%SCHEMES_DIR%switch.py" %*