@echo off
chcp 65001 >nul
echo ============================================================================
echo                    PDF转换器依赖自动安装脚本
echo ============================================================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python已安装
python --version
echo.

:: 升级pip
echo 📦 升级pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo ⚠️  pip升级失败，继续安装依赖
)
echo.

:: 安装Python依赖
echo 📦 安装Python依赖包...
if exist requirements.txt (
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ Python依赖安装失败
        pause
        exit /b 1
    )
    echo ✅ Python依赖安装成功
) else (
    echo ❌ 未找到requirements.txt文件
    pause
    exit /b 1
)
echo.

:: 检查系统依赖
echo 🔧 检查系统依赖...
echo.

:: Tesseract检查已移除
echo Tesseract OCR功能已移除

:: 检查Poppler
echo 检查Poppler PDF工具...
pdftoppm -h >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Poppler未安装或未添加到PATH
    echo 📋 安装指南:
    echo    1. 访问: https://github.com/oschwartz10612/poppler-windows/releases/
    echo    2. 下载最新版本 (推荐24.08.0+)
    echo    3. 解压到: C:\poppler
    echo    4. 添加 C:\poppler\Library\bin 到系统PATH
    echo    5. 重启命令行
    echo.
) else (
    echo ✅ Poppler已安装
    echo.
)

:: 运行完整依赖检查
echo 📋 运行完整依赖检查...
python scripts/dependency_checker.py
echo.

:: 询问是否启动应用
echo ============================================================================
set /p choice=是否立即启动PDF转换器? (y/n): 
if /i "%choice%"=="y" (
    echo 🚀 启动PDF转换器...
    python pdf_converter.py
) else (
    echo 💡 稍后可以运行: python pdf_converter.py
)

echo.
echo 安装完成！
pause