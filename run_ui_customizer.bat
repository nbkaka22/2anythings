@echo off
echo 正在启动PDF转换工具UI自定义器...

REM 检查Python是否已安装
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未检测到Python安装，请先安装Python 3.6或更高版本。
    pause
    exit /b 1
)

REM 运行UI自定义器
python ui_customizer.py

if %ERRORLEVEL% NEQ 0 (
    echo 运行UI自定义器时出错，请检查Python环境和依赖项。
    pause
)

exit /b 0