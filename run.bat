@echo off
rem PyCode 練習：Windows 啟動腳本（雙擊即可）
rem 用法：run.bat [--port 5000] [--host 127.0.0.1] [--no-browser]
rem 需求：Python 3.10 以上（https://www.python.org/downloads/），不需要 pip install、不需要網路
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1

rem 優先使用 Python 啟動器 py，其次是 python
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo 找不到 Python 3.10 以上的版本。
    echo 請到 https://www.python.org/downloads/ 下載安裝，安裝時勾選 "Add python.exe to PATH"。
    pause
    exit /b 1
)

%PY% launcher.py %*
if errorlevel 1 pause
