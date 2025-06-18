#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转换器工具模块

包含项目所需的工具函数、配置信息和日志设置
"""

import os
import sys
import logging

# ==================== 配置信息 ====================

# 错误消息配置
ERROR_MESSAGES = {
    'no_input': '请选择PDF文件或文件夹',
    'no_output': '请选择输出目录',
    'invalid_pdf': 'PDF文件无效或已损坏',
    'permission_denied': '没有权限访问文件或目录',
    'disk_full': '磁盘空间不足',
    'conversion_failed': '转换失败',
    'unknown_error': '发生未知错误'
}

# 应用程序配置
APP_CONFIG = {
    'name': 'PDF转换器',
    'version': '2.0.0',
    'author': 'PDF转换器项目组',
    'log_file': 'pdf_converter.log',
    'encoding': 'utf-8'
}

# ==================== 日志配置 ====================

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(APP_CONFIG['log_file'], encoding=APP_CONFIG['encoding']),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('pdf_converter')

# ==================== 工具函数 ====================

def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径，适用于PyInstaller打包后的情况
    
    Args:
        relative_path (str): 相对路径
        
    Returns:
        str: 绝对路径
    """
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


def get_output_path(input_path, output_dir, output_format, page_num=None):
    """
    根据输入路径和输出格式生成输出文件路径
    
    Args:
        input_path (str): 输入文件路径
        output_dir (str): 输出目录
        output_format (str): 输出格式
        page_num (int, optional): 页码（用于图片格式）
        
    Returns:
        str: 输出文件路径
    """
    # 获取不带扩展名的文件名
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    
    # 如果是图片格式且指定了页码，则添加页码信息
    if page_num is not None and output_format in ['png', 'jpg']:
        file_name = f"{base_name}_page{page_num + 1}.{output_format}"
    else:
        file_name = f"{base_name}.{output_format}"
    
    return os.path.join(output_dir, file_name)


def ensure_dir_exists(directory):
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory (str): 目录路径
        
    Returns:
        bool: 创建成功返回True，失败返回False
    """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            logger.info(f"创建目录: {directory}")
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {directory}, 错误: {str(e)}")
            return False
    return True


def is_valid_pdf(file_path):
    """
    简单检查文件是否为有效的PDF文件
    
    Args:
        file_path (str): PDF文件路径
        
    Returns:
        bool: 有效返回True，无效返回False
    """
    if not os.path.exists(file_path):
        return False
    
    if not file_path.lower().endswith('.pdf'):
        return False
    
    # 检查文件大小是否大于0
    if os.path.getsize(file_path) <= 0:
        return False
    
    # 检查文件头部是否为PDF标识
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF'
    except Exception as e:
        logger.error(f"检查PDF文件有效性失败: {file_path}, 错误: {str(e)}")
        return False


def get_error_message(error_code):
    """
    根据错误代码获取错误消息
    
    Args:
        error_code (str): 错误代码
        
    Returns:
        str: 错误消息
    """
    return ERROR_MESSAGES.get(error_code, ERROR_MESSAGES['unknown_error'])


def get_app_info():
    """
    获取应用程序信息
    
    Returns:
        dict: 应用程序配置信息
    """
    return APP_CONFIG.copy()


def setup_logging(log_level=logging.INFO, log_file=None):
    """
    重新配置日志系统
    
    Args:
        log_level: 日志级别
        log_file (str, optional): 日志文件路径
    """
    if log_file is None:
        log_file = APP_CONFIG['log_file']
    
    # 清除现有的处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # 重新配置
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding=APP_CONFIG['encoding']),
            logging.StreamHandler()
        ],
        force=True
    )


# ==================== 兼容性支持 ====================

# 为了保持向后兼容，导出原config.py中的变量
__all__ = [
    'ERROR_MESSAGES',
    'APP_CONFIG', 
    'logger',
    'get_resource_path',
    'get_output_path',
    'ensure_dir_exists',
    'is_valid_pdf',
    'get_error_message',
    'get_app_info',
    'setup_logging'
]