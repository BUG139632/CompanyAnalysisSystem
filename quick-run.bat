@echo off
REM quick-run.bat

REM 固定容器名
set CONTAINER_NAME=investment-analysis-container

echo 🚀 快速启动投资分析系统
echo ========================================

REM 检查是否已构建镜像
docker images investment-analysis >nul 2>&1
if errorlevel 1 (
    echo 🔨 首次运行，正在构建 Docker 镜像...
    docker build -t investment-analysis .
)

REM 删除旧容器（如果存在）
docker ps -aq -f name=^/%CONTAINER_NAME%$ >nul 2>&1
if not errorlevel 1 (
    echo 🗑️  删除旧容器: %CONTAINER_NAME%
    docker rm -f %CONTAINER_NAME%
)

REM 创建目录
if not exist "output" mkdir output
if not exist "data" mkdir data
if not exist "logs" mkdir logs

echo 📁 目录结构:
echo    - 输出目录: %cd%\output
echo    - 数据目录: %cd%\data
echo    - 日志目录: %cd%\logs

echo.
echo 🎯 启动分析系统...
echo 💡 输入公司名称后，结果将自动保存到 output\ 目录
echo 💡 提示：如需使用 Gemini API，请设置环境变量 GEMINI_API_KEY
echo     例如：set GEMINI_API_KEY=your_key_here ^&^& quick-run.bat
echo ========================================

REM 运行容器
docker run -it ^
    --name %CONTAINER_NAME% ^
    -v "%cd%/output:/app/output" ^
    -v "%cd%/data:/app/data" ^
    -v "%cd%/logs:/app/logs" ^
    -v "%cd%/config:/app/config" ^
    -e GEMINI_API_KEY=%GEMINI_API_KEY% ^
    investment-analysis

echo.
echo ✅ 分析完成！
echo 📁 查看结果文件: dir output\
pause 