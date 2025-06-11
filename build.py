import os
import sys
import subprocess
import shutil
from datetime import datetime

def build_executable():
    """
    使用PyInstaller将应用程序打包为可执行文件
    """
    print("===== PDF格式转换工具打包脚本 =====")
    print("正在准备打包...", end="")
    
    # 确保icon.ico存在
    if not os.path.exists("icon.ico"):
        if os.path.exists("icon.svg"):
            print("\n正在从SVG创建ICO图标...")
            try:
                # 尝试运行create_icon.py脚本
                subprocess.run([sys.executable, "create_icon.py"], check=True)
            except subprocess.CalledProcessError:
                print("警告: 无法创建图标，将使用默认图标")
        else:
            print("\n警告: 未找到图标文件，将使用默认图标")
    
    print("完成")
    
    # 创建输出目录
    dist_dir = "dist"
    if not os.path.exists(dist_dir):
        os.makedirs(dist_dir)
    
    # 创建build目录
    build_dir = "build"
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
    
    # 获取当前日期作为版本号的一部分
    version = datetime.now().strftime("%Y%m%d")
    
    print("\n正在安装PyInstaller...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    except subprocess.CalledProcessError:
        print("错误: 无法安装PyInstaller，请手动安装后重试")
        return False
    
    print("\n正在打包应用程序...")
    try:
        # 构建PyInstaller命令
        cmd = [
            sys.executable, 
            "-m", 
            "PyInstaller",
            "--name=PDF格式转换工具",
            "--windowed",  # 无控制台窗口
            "--onefile",   # 单文件模式
            "--clean",     # 清理临时文件
            "--noconfirm", # 不确认覆盖
            "--hidden-import=numpy._core._exceptions",
            "--hidden-import=numpy._core._dtype_ctypes",
            "--hidden-import=numpy._core._internal",
            "--hidden-import=numpy.core._methods",
            "--hidden-import=numpy.lib.recfunctions",
            "--add-data=icon.ico;.",  # 将图标文件添加到打包中
        ]
        
        # 如果图标存在，添加图标参数
        icon_path = os.path.abspath("icon.ico")
        if os.path.exists(icon_path):
            cmd.append(f"--icon={icon_path}")
            print(f"使用图标文件: {icon_path}")
        else:
            print("警告: 未找到图标文件")
        
        # 添加主程序文件
        cmd.append("pdf_converter.py")
        
        # 执行打包命令
        subprocess.run(cmd, check=True)
        
        # 复制必要的文件到dist目录
        print("\n正在复制附加文件...")
        files_to_copy = [
            "README.md",
            "requirements.txt"
        ]
        
        for file in files_to_copy:
            if os.path.exists(file):
                shutil.copy2(file, os.path.join(dist_dir, file))
        
        # 创建快捷方式批处理文件
        with open(os.path.join(dist_dir, "运行PDF转换工具.bat"), "w", encoding="utf-8") as f:
            f.write('@echo off\n"PDF格式转换工具.exe"')
        
        print("\n打包完成！")
        print(f"可执行文件位于: {os.path.abspath(os.path.join(dist_dir, 'PDF格式转换工具.exe'))}")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"\n错误: 打包过程中出错: {str(e)}")
        return False
    except Exception as e:
        print(f"\n错误: {str(e)}")
        return False

if __name__ == "__main__":
    build_executable()