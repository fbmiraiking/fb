@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Standard Lens - Dev Launcher
cd /d "%~dp0"

echo ==========================================
echo   Standard Lens - 本地开发启动器
echo ==========================================
echo.

rem ---------- 1. Python ----------
set "PY_LAUNCHER="
py -3.12 --version >nul 2>&1
if not errorlevel 1 set "PY_LAUNCHER=py -3.12"

if not defined PY_LAUNCHER (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PY_LAUNCHER=py -3"
)

if not defined PY_LAUNCHER (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY_LAUNCHER=python"
)

if not defined PY_LAUNCHER (
    echo [错误] 未找到 Python 3.12 或更高版本。
    echo        请从 https://www.python.org/downloads/ 安装后重试。
    goto :fail
)

set "PYTHONUTF8=1"

rem ---------- 2. Node.js ----------
rem 优先使用 PATH；找不到时尝试注册表安装位置和常见目录，
rem 因为部分机器安装了 Node 却没有把它加入 PATH。
set "NODE_DIR="
where node >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%P in ('where node') do if not defined NODE_DIR set "NODE_DIR=%%~dpP"
)

set "NODE_INSTALL="
if not defined NODE_DIR (
    for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "(Get-ItemProperty 'HKLM:\SOFTWARE\Node.js' -ErrorAction SilentlyContinue).InstallPath"`) do set "NODE_INSTALL=%%P"
)

if defined NODE_INSTALL if "%NODE_INSTALL:~-1%"=="\" set "NODE_INSTALL=%NODE_INSTALL:~0,-1%"

if not defined NODE_DIR if defined NODE_INSTALL if exist "%NODE_INSTALL%\node.exe" set "NODE_DIR=%NODE_INSTALL%"
if not defined NODE_DIR if defined NODE_INSTALL if exist "%NODE_INSTALL%\node\node.exe" set "NODE_DIR=%NODE_INSTALL%\node"
if not defined NODE_DIR if defined NODE_INSTALL if exist "%NODE_INSTALL%\nodejs\node.exe" set "NODE_DIR=%NODE_INSTALL%\nodejs"
if not defined NODE_DIR if exist "%ProgramFiles%\nodejs\node.exe" set "NODE_DIR=%ProgramFiles%\nodejs"
if not defined NODE_DIR if exist "%LOCALAPPDATA%\Programs\nodejs\node.exe" set "NODE_DIR=%LOCALAPPDATA%\Programs\nodejs"

if defined NODE_DIR set "PATH=%NODE_DIR%;%PATH%"

where node >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Node.js。
    echo        请安装 Node.js 20 LTS 或更高版本：https://nodejs.org/
    goto :fail
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 npm，请检查 Node.js 安装是否完整。
    goto :fail
)

call npm --version >nul 2>&1
if errorlevel 1 (
    echo [错误] npm 无法运行，Node.js 安装可能不完整，请重新安装 Node.js LTS。
    goto :fail
)

rem ---------- 3. 虚拟环境 ----------
if exist "backend\.venv\Scripts\python.exe" (
    echo [1/6] 使用已有虚拟环境 backend\.venv
) else (
    echo [1/6] 创建虚拟环境 backend\.venv ...
    %PY_LAUNCHER% -m venv backend\.venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败。
        goto :fail
    )
)

set "PYTHON=%CD%\backend\.venv\Scripts\python.exe"
"%PYTHON%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"
if errorlevel 1 (
    echo [错误] 虚拟环境中的 Python 版本低于 3.12：
    "%PYTHON%" --version
    goto :fail
)

rem ---------- 4. 后端依赖 ----------
if not exist "backend\.venv\.deps-ok" (
    echo [2/6] 安装后端依赖（首次运行需要几分钟）...
    "%PYTHON%" -m pip install --upgrade pip
    "%PYTHON%" -m pip install -r backend\requirements.txt
    if errorlevel 1 (
        echo [错误] 后端依赖安装失败，请检查网络或 requirements.txt。
        goto :fail
    )
    type nul > "backend\.venv\.deps-ok"
) else (
    echo [2/6] 后端依赖已安装（如更新了 requirements.txt，请删除 backend\.venv\.deps-ok 后重试）
)

rem ---------- 5. 配置文件 ----------
if not exist "backend\.env" (
    copy /y "backend\.env.example" "backend\.env" >nul
    echo [3/6] 已生成 backend\.env，请按需修改 MySQL 账号密码。
) else (
    echo [3/6] 已存在 backend\.env
)

if not exist "frontend\.env" (
    copy /y "frontend\.env.example" "frontend\.env" >nul
)

findstr /x /c:"MYSQL_PASSWORD=change_me" "backend\.env" >nul 2>&1
if not errorlevel 1 (
    echo [提示] backend\.env 仍在使用示例密码，请修改 MYSQL_* 配置后再启动。
)

rem ---------- 6. 数据库 ----------
echo [4/6] 检查 MySQL 并执行数据库迁移 ...
pushd backend
"%PYTHON%" -m scripts.init_db
if errorlevel 1 (
    echo [警告] 数据库不可用，服务会以 degraded 状态启动。
    echo        请检查 MySQL 是否运行，以及 backend\.env 中的 MYSQL_* 配置。
) else (
    "%PYTHON%" -m alembic upgrade head
    if errorlevel 1 (
        echo [警告] Alembic 迁移失败，请查看上方错误信息。
    )
)
popd

rem ---------- 7. 启动后端 ----------
echo [5/6] 启动 FastAPI：http://127.0.0.1:8000
start "Standard Lens API" /D "%CD%\backend" cmd /k ""%PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

set "API_READY="
for /l %%I in (1,1,40) do (
    if not defined API_READY (
        curl -s -o NUL --max-time 2 http://127.0.0.1:8000/api/health >nul 2>&1
        if not errorlevel 1 set "API_READY=1"
        if not defined API_READY timeout /t 1 /nobreak >nul
    )
)

if defined API_READY (
    echo       后端已就绪。
) else (
    echo [警告] 后端 40 秒内未响应，请查看 "Standard Lens API" 窗口中的日志。
)

rem ---------- 8. 启动前端 ----------
if not exist "frontend\node_modules" (
    echo [6/6] 安装前端依赖（首次运行需要几分钟）...
    pushd frontend
    call npm install
    if errorlevel 1 (
        popd
        echo [错误] 前端依赖安装失败。
        goto :fail
    )
    popd
) else (
    echo [6/6] 前端依赖已安装。
)

start "Standard Lens Web" /D "%CD%\frontend" cmd /k "call npm run dev"

set "WEB_READY="
for /l %%I in (1,1,30) do (
    if not defined WEB_READY (
        curl -s -o NUL --max-time 2 http://127.0.0.1:5173/ >nul 2>&1
        if not errorlevel 1 set "WEB_READY=1"
        if not defined WEB_READY timeout /t 1 /nobreak >nul
    )
)

if defined WEB_READY (
    start "" http://localhost:5173/
) else (
    echo [警告] Vite 尚未响应，请稍后手动打开 http://localhost:5173/
)

echo.
echo 启动完成。后端和前端分别运行在两个新窗口中，关闭窗口即可停止。
echo 健康检查：http://127.0.0.1:8000/api/health
echo 接口文档：http://127.0.0.1:8000/docs
echo.
pause
exit /b 0

:fail
echo.
pause
exit /b 1
