@echo off
cd /d "%~dp0"

REM 使用相对路径调用虚拟环境中的 Python 解释器
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
