#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖检查器模块
用于检查项目所需的Python包和系统依赖
"""

import importlib
import subprocess
import sys
from typing import Dict, List, Tuple


class DependencyChecker:
    """依赖检查器类"""
    
    def __init__(self):
        # 必需的Python包
        self.required_packages = {
            'tkinter': 'tkinter',
            'PIL': 'Pillow',
            'fitz': 'PyMuPDF',
            'docx': 'python-docx',
            'pptx': 'python-pptx',
            'cv2': 'opencv-python',
            'numpy': 'numpy',
            'requests': 'requests'
        }
        
        # 可选的Python包
        self.optional_packages = {
            'paddleocr': 'paddleocr',
            'easyocr': 'easyocr',
            'torch': 'torch',
            'torchvision': 'torchvision'
        }
        
        # 系统依赖
        self.system_dependencies = [
            'tesseract'  # OCR引擎
        ]
    
    def check_python_package(self, import_name: str) -> bool:
        """检查Python包是否可用
        
        Args:
            import_name: 导入名称
            
        Returns:
            bool: 包是否可用
        """
        try:
            importlib.import_module(import_name)
            return True
        except ImportError:
            return False
    
    def check_system_dependency(self, command: str) -> bool:
        """检查系统依赖是否可用
        
        Args:
            command: 命令名称
            
        Returns:
            bool: 依赖是否可用
        """
        try:
            subprocess.run([command, '--version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def check_all(self, verbose: bool = False) -> bool:
        """检查所有依赖
        
        Args:
            verbose: 是否显示详细信息
            
        Returns:
            bool: 所有必需依赖是否都可用
        """
        all_ok = True
        
        if verbose:
            print("\n📦 检查Python包...")
        
        # 检查必需的Python包
        for import_name, package_name in self.required_packages.items():
            available = self.check_python_package(import_name)
            if verbose:
                status = "✅" if available else "❌"
                print(f"  {status} {package_name} ({import_name})")
            if not available:
                all_ok = False
        
        if verbose:
            print("\n🔧 检查可选Python包...")
        
        # 检查可选的Python包
        for import_name, package_name in self.optional_packages.items():
            available = self.check_python_package(import_name)
            if verbose:
                status = "✅" if available else "⚠️"
                print(f"  {status} {package_name} ({import_name}) [可选]")
        
        if verbose:
            print("\n🖥️  检查系统依赖...")
        
        # 检查系统依赖
        for dependency in self.system_dependencies:
            available = self.check_system_dependency(dependency)
            if verbose:
                status = "✅" if available else "⚠️"
                print(f"  {status} {dependency} [可选]")
        
        return all_ok
    
    def get_missing_dependencies(self) -> Dict[str, List[str]]:
        """获取缺失的依赖列表
        
        Returns:
            Dict[str, List[str]]: 缺失的依赖，分为python和system两类
        """
        missing = {
            'python': [],
            'system': []
        }
        
        # 检查Python包
        for import_name, package_name in self.required_packages.items():
            if not self.check_python_package(import_name):
                missing['python'].append(package_name)
        
        # 检查系统依赖
        for dependency in self.system_dependencies:
            if not self.check_system_dependency(dependency):
                missing['system'].append(dependency)
        
        return missing
    
    def install_missing_packages(self) -> bool:
        """尝试安装缺失的Python包
        
        Returns:
            bool: 安装是否成功
        """
        missing = self.get_missing_dependencies()
        
        if not missing['python']:
            print("✅ 所有必需的Python包都已安装")
            return True
        
        print(f"📦 正在安装缺失的包: {', '.join(missing['python'])}")
        
        try:
            for package in missing['python']:
                print(f"  安装 {package}...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                             check=True)
            print("✅ 所有包安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 安装失败: {e}")
            return False


def quick_dependency_check() -> bool:
    """快速依赖检查
    
    Returns:
        bool: 基本依赖是否满足
    """
    checker = DependencyChecker()
    
    # 检查最基本的依赖
    basic_deps = ['tkinter', 'PIL', 'fitz']
    
    for dep in basic_deps:
        if not checker.check_python_package(dep):
            return False
    
    return True


if __name__ == "__main__":
    # 命令行使用
    checker = DependencyChecker()
    
    print("🔍 PDF转换器依赖检查")
    print("=" * 50)
    
    all_ok = checker.check_all(verbose=True)
    
    if all_ok:
        print("\n🎉 所有必需依赖都已满足！")
    else:
        print("\n⚠️  发现缺失的依赖项")
        
        # 询问是否自动安装
        try:
            response = input("\n是否尝试自动安装缺失的Python包? (y/n): ")
            if response.lower() == 'y':
                checker.install_missing_packages()
        except KeyboardInterrupt:
            print("\n操作已取消")