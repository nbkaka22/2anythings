#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换器项目自动安装脚本

此脚本将自动检查和安装项目所需的所有依赖项。

使用方法:
    python setup.py

作者: PDF转换器项目组
"""

import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import shutil
from pathlib import Path


class DependencyInstaller:
    """依赖安装器类"""
    
    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == "Windows"
        self.project_root = Path(__file__).parent
        
    def print_step(self, step_num, description):
        """打印安装步骤"""
        print(f"\n{'='*60}")
        print(f"步骤 {step_num}: {description}")
        print(f"{'='*60}")
        
    def run_command(self, command, check=True):
        """执行命令"""
        try:
            result = subprocess.run(command, shell=True, check=check, 
                                  capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return False, e.stdout, e.stderr
            
    def check_python_version(self):
        """检查Python版本"""
        self.print_step(1, "检查Python版本")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("❌ 错误: 需要Python 3.8或更高版本")
            print(f"当前版本: {version.major}.{version.minor}.{version.micro}")
            return False
            
        print(f"✅ Python版本检查通过: {version.major}.{version.minor}.{version.micro}")
        return True
        
    def install_python_dependencies(self):
        """安装Python依赖"""
        self.print_step(2, "安装Python依赖包")
        
        # 检查是否在虚拟环境中
        in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        
        if not in_venv:
            print("⚠️  建议在虚拟环境中安装依赖")
            response = input("是否创建虚拟环境? (y/n): ")
            if response.lower() == 'y':
                self.create_virtual_environment()
                return True
                
        # 升级pip
        print("📦 升级pip...")
        success, stdout, stderr = self.run_command(f"{sys.executable} -m pip install --upgrade pip")
        if not success:
            print(f"⚠️  pip升级失败: {stderr}")
            
        # 安装依赖
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            print("📦 安装项目依赖...")
            success, stdout, stderr = self.run_command(f"{sys.executable} -m pip install -r {requirements_file}")
            if success:
                print("✅ Python依赖安装成功")
                return True
            else:
                print(f"❌ 依赖安装失败: {stderr}")
                return False
        else:
            print("❌ 未找到requirements.txt文件")
            return False
            
    def create_virtual_environment(self):
        """创建虚拟环境"""
        venv_path = self.project_root / ".venv"
        
        print(f"🔧 创建虚拟环境: {venv_path}")
        success, stdout, stderr = self.run_command(f"{sys.executable} -m venv {venv_path}")
        
        if success:
            print("✅ 虚拟环境创建成功")
            if self.is_windows:
                activate_script = venv_path / "Scripts" / "activate.bat"
                print(f"\n激活虚拟环境: {activate_script}")
                print("然后重新运行: python setup.py")
            else:
                activate_script = venv_path / "bin" / "activate"
                print(f"\n激活虚拟环境: source {activate_script}")
                print("然后重新运行: python setup.py")
        else:
            print(f"❌ 虚拟环境创建失败: {stderr}")
            
    # def check_tesseract(self):
    #     """检查Tesseract安装 - 已移除"""
    #     pass
            
    # def install_tesseract_guide(self):
    #     """显示Tesseract安装指南 - 已移除"""
    #     pass
            
    def check_poppler(self):
        """检查Poppler安装"""
        self.print_step(4, "检查Poppler PDF工具")
        
        success, stdout, stderr = self.run_command("pdftoppm -h", check=False)
        if success:
            print("✅ Poppler已安装")
            return True
        else:
            print("❌ Poppler未安装或未添加到PATH")
            self.install_poppler_guide()
            return False
            
    def install_poppler_guide(self):
        """显示Poppler安装指南"""
        if self.is_windows:
            print("\n📋 Poppler安装指南 (Windows):")
            print("1. 访问: https://github.com/oschwartz10612/poppler-windows/releases/")
            print("2. 下载最新版本 (推荐24.08.0或更高)")
            print("3. 解压到: C:\\poppler")
            print("4. 将 C:\\poppler\\Library\\bin 添加到系统PATH环境变量")
            print("5. 重启命令行或IDE")
        else:
            print("\n📋 Poppler安装指南 (Linux/Mac):")
            print("Ubuntu/Debian: sudo apt-get install poppler-utils")
            print("CentOS/RHEL: sudo yum install poppler-utils")
            print("macOS: brew install poppler")
            
    def verify_installation(self):
        """验证安装"""
        self.print_step(5, "验证安装")
        
        # 测试Python包导入
        test_imports = [
            'pdf2docx',
            'pdfplumber',
        'easyocr', 
            'reportlab',
            'pptx',
            'PIL',
            # 'pytesseract', # 已移除
        # 'pdf2image' # 已移除（主要用于OCR功能）
        ]
        
        failed_imports = []
        for package in test_imports:
            try:
                __import__(package)
                print(f"✅ {package} 导入成功")
            except ImportError:
                print(f"❌ {package} 导入失败")
                failed_imports.append(package)
                
        if failed_imports:
            print(f"\n❌ 以下包导入失败: {', '.join(failed_imports)}")
            return False
        else:
            print("\n🎉 所有Python包验证成功!")
            return True
            
    def run_installation(self):
        """运行完整安装流程"""
        print("🚀 PDF转换器项目自动安装程序")
        print("=" * 60)
        
        # 检查Python版本
        if not self.check_python_version():
            return False
            
        # 安装Python依赖
        if not self.install_python_dependencies():
            return False
            
        # 检查系统依赖
        # tesseract_ok = self.check_tesseract() # 已移除
        poppler_ok = self.check_poppler()
        
        # 验证安装
        python_ok = self.verify_installation()
        
        # 总结
        print("\n" + "="*60)
        print("📋 安装总结")
        print("="*60)
        print(f"Python依赖: {'✅ 成功' if python_ok else '❌ 失败'}")
        # print(f"Tesseract OCR: {'✅ 成功' if tesseract_ok else '❌ 需要手动安装'}") # 已移除
        print(f"Poppler PDF: {'✅ 成功' if poppler_ok else '❌ 需要手动安装'}")
        print("\n" + "="*50)
        
        if python_ok and poppler_ok:  # 移除了tesseract_ok检查
            print("\n🎉 所有依赖安装完成! 可以运行应用程序了:")
            print("   python pdf_converter.py")
            return True
        else:
            print("\n⚠️  部分依赖需要手动安装，请按照上述指南完成安装")
            return False


def main():
    """主函数"""
    installer = DependencyInstaller()
    installer.run_installation()


if __name__ == "__main__":
    main()