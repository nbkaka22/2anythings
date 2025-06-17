#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖检查模块

在应用程序启动时检查所有必需的依赖项，确保系统环境配置正确。

作者: PDF转换器项目组
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class DependencyChecker:
    """依赖检查器类"""
    
    def __init__(self):
        self.python_dependencies = {
            'pdf2docx': 'PDF转DOCX转换',
            'pdfplumber': 'PDF文本提取',
            'reportlab': 'PDF生成处理',
            'pptx': 'PowerPoint操作',
            'PIL': '图像处理',
            # 'pytesseract': 'OCR文字识别', # 已移除
        # 'pdf2image': 'PDF转图像', # 已移除（主要用于OCR功能）
            'docx': 'Word文档处理'
        }
        
        self.system_dependencies = {
            # 'tesseract': {
            #     'command': 'tesseract --version',
            #     'description': 'Tesseract OCR引擎',
            #     'install_guide': self._get_tesseract_guide()
            # }, # 已移除
            # 'poppler': {
            #     'command': 'pdftoppm -h',
            #     'description': 'Poppler PDF工具集',
            #     'install_guide': self._get_poppler_guide()
            # } # 已移除，不再使用pdf2image库
        }
        
        self.check_results = {
            'python_deps': {},
            'system_deps': {},
            'overall_status': True
        }
        
    # def _get_tesseract_guide(self) -> str:
    #     """获取Tesseract安装指南 - 已移除"""
    #     pass
            
    def _get_poppler_guide(self) -> str:
        """获取Poppler安装指南"""
        if os.name == 'nt':  # Windows
            return (
                "Windows安装指南:\n"
                "1. 访问: https://github.com/oschwartz10612/poppler-windows/releases/\n"
                "2. 下载最新版本 (推荐24.08.0+)\n"
                "3. 解压到: C:\\poppler\n"
                "4. 添加 C:\\poppler\\Library\\bin 到系统PATH\n"
                "5. 重启应用程序"
            )
        else:
            return (
                "Linux/Mac安装指南:\n"
                "Ubuntu/Debian: sudo apt-get install poppler-utils\n"
                "CentOS/RHEL: sudo yum install poppler-utils\n"
                "macOS: brew install poppler"
            )
    
    def check_python_dependency(self, package_name: str) -> Tuple[bool, Optional[str]]:
        """检查单个Python依赖"""
        try:
            module = importlib.import_module(package_name)
            version = getattr(module, '__version__', 'Unknown')
            return True, version
        except ImportError as e:
            return False, str(e)
    
    def check_system_dependency(self, command: str) -> Tuple[bool, str]:
        """检查系统依赖"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                # 提取版本信息
                output_lines = result.stdout.strip().split('\n')
                version_info = output_lines[0] if output_lines else 'Installed'
                return True, version_info
            else:
                return False, result.stderr.strip() or 'Command failed'
        except subprocess.TimeoutExpired:
            return False, 'Command timeout'
        except Exception as e:
            return False, str(e)
    
    def check_all_python_dependencies(self) -> Dict[str, Dict]:
        """检查所有Python依赖"""
        results = {}
        
        for package, description in self.python_dependencies.items():
            success, info = self.check_python_dependency(package)
            results[package] = {
                'success': success,
                'description': description,
                'version': info if success else None,
                'error': info if not success else None
            }
            
            if not success:
                self.check_results['overall_status'] = False
                
        self.check_results['python_deps'] = results
        return results
    
    def check_all_system_dependencies(self) -> Dict[str, Dict]:
        """检查所有系统依赖"""
        results = {}
        
        for dep_name, dep_info in self.system_dependencies.items():
            success, info = self.check_system_dependency(dep_info['command'])
            results[dep_name] = {
                'success': success,
                'description': dep_info['description'],
                'version': info if success else None,
                'error': info if not success else None,
                'install_guide': dep_info['install_guide']
            }
            
            if not success:
                self.check_results['overall_status'] = False
                
        self.check_results['system_deps'] = results
        return results
    
    def generate_report(self) -> str:
        """生成依赖检查报告"""
        report = []
        report.append("="*60)
        report.append("📋 依赖检查报告")
        report.append("="*60)
        
        # Python依赖检查结果
        report.append("\n🐍 Python依赖检查:")
        report.append("-"*40)
        
        for package, info in self.check_results['python_deps'].items():
            status = "✅" if info['success'] else "❌"
            version = f" (v{info['version']})" if info['version'] else ""
            report.append(f"{status} {package}{version} - {info['description']}")
            
            if not info['success']:
                report.append(f"   错误: {info['error']}")
        
        # 系统依赖检查结果
        report.append("\n🔧 系统依赖检查:")
        report.append("-"*40)
        
        for dep_name, info in self.check_results['system_deps'].items():
            status = "✅" if info['success'] else "❌"
            version = f" ({info['version']})" if info['version'] and info['success'] else ""
            report.append(f"{status} {dep_name}{version} - {info['description']}")
            
            if not info['success']:
                report.append(f"   错误: {info['error']}")
                report.append(f"   {info['install_guide']}")
        
        # 总体状态
        report.append("\n" + "="*60)
        if self.check_results['overall_status']:
            report.append("🎉 所有依赖检查通过! 应用程序可以正常运行。")
        else:
            report.append("⚠️  发现缺失的依赖项，请按照上述指南安装。")
            report.append("\n💡 提示: 可以运行 'python scripts/setup.py' 进行自动安装。")
        report.append("="*60)
        
        return "\n".join(report)
    
    def check_all(self, verbose: bool = True) -> bool:
        """执行完整的依赖检查"""
        # 检查Python依赖
        self.check_all_python_dependencies()
        
        # 检查系统依赖
        self.check_all_system_dependencies()
        
        # 生成并打印报告
        if verbose:
            print(self.generate_report())
        
        return self.check_results['overall_status']
    
    def get_missing_dependencies(self) -> Dict[str, List[str]]:
        """获取缺失的依赖列表"""
        missing = {
            'python': [],
            'system': []
        }
        
        for package, info in self.check_results['python_deps'].items():
            if not info['success']:
                missing['python'].append(package)
        
        for dep_name, info in self.check_results['system_deps'].items():
            if not info['success']:
                missing['system'].append(dep_name)
        
        return missing
    
    def quick_check(self) -> bool:
        """快速检查（不输出详细信息）"""
        return self.check_all(verbose=False)


def check_dependencies_on_startup() -> bool:
    """应用启动时的依赖检查函数"""
    checker = DependencyChecker()
    return checker.check_all()


def quick_dependency_check() -> bool:
    """快速依赖检查（用于应用内部调用）"""
    checker = DependencyChecker()
    return checker.quick_check()


def get_dependency_status() -> Dict:
    """获取依赖状态信息"""
    checker = DependencyChecker()
    checker.check_all(verbose=False)
    return checker.check_results


if __name__ == "__main__":
    # 直接运行此脚本时执行依赖检查
    check_dependencies_on_startup()