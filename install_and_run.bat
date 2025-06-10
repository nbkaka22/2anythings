@echo off
chcp 65001 >nul
echo ====================================
echo     PDF格式转换工具 安装脚本
echo ====================================
echo.

echo 正在检查Python安装...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python已安装
echo.

echo 正在安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 警告: 依赖安装可能存在问题，但将尝试运行程序
    echo.
)

echo.
echo 依赖安装完成！
echo.
echo 正在启动PDF转换工具...
echo.

python pdf_converter.py

if errorlevel 1 (
    echo.
    echo 程序运行出现错误，请检查错误信息
    pause
)