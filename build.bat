@echo off
cd /d "%~dp0"

echo === Dota2 本地修改工具 - 打包脚本 ===
echo.

REM 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 创建虚拟环境...
    python -m venv .venv
) else (
    echo [1/3] 虚拟环境已存在，跳过
)

echo [2/3] 安装依赖...
.venv\Scripts\pip.exe install -r requirement.txt

echo [3/3] 开始打包...
.venv\Scripts\pyinstaller.exe -F -i "icon.ico" -w --name "dota2_local_change" main.py

echo.
if exist "dist\dota2_local_change.exe" (
    echo === 打包成功 ===
    echo 输出文件: dist\dota2_local_change.exe
) else (
    echo === 打包失败 ===
)
echo.
pause
