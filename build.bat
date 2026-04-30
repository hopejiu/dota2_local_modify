@echo off
cd /d "%~dp0"

echo === Dota2 本地修改工具 - 打包脚本 ===
echo.

REM 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [1/4] 创建虚拟环境...
    python -m venv .venv
) else (
    echo [1/4] 虚拟环境已存在，跳过
)

echo [2/4] 安装依赖...
.venv\Scripts\pip.exe install -r requirement.txt

REM 检查并下载 UPX
echo [3/4] 检查 UPX...
if not exist "upx\upx.exe" (
    echo 正在下载 UPX...
    if not exist "upx" mkdir upx
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/upx/upx/releases/download/v5.1.1/upx-5.1.1-win64.zip' -OutFile 'upx\upx.zip'"
    powershell -Command "Expand-Archive -Path 'upx\upx.zip' -DestinationPath 'upx' -Force"
    for /d %%d in (upx\upx-*-win64) do move "%%d\upx.exe" "upx\upx.exe" >nul 2>&1
    del "upx\upx.zip" >nul 2>&1
    for /d %%d in (upx\upx-*-win64) do rd /s /q "%%d" >nul 2>&1
    echo UPX 下载完成
) else (
    echo UPX 已存在，跳过下载
)

echo [4/4] 开始打包...
.venv\Scripts\pyinstaller.exe --clean --upx-dir "%~dp0upx" dota2_local_change.spec

echo.
if exist "dist\dota2_local_change.exe" (
    echo === 打包成功 ===
    echo 输出文件: dist\dota2_local_change.exe
    for %%f in ("dist\dota2_local_change.exe") do echo 文件大小: %%~zf 字节
) else (
    echo === 打包失败 ===
)
echo.
pause
