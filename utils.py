import os
import sys
import logging
from config import ERROR_MESSAGES

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pdf_converter.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('pdf_converter')


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径，适用于PyInstaller打包后的情况
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


# 删除了未使用的函数: get_file_size, get_file_count, format_time, create_timestamp, check_disk_space


def is_valid_pdf(file_path):
    """
    简单检查文件是否为有效的PDF文件
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
    """
    return ERROR_MESSAGES.get(error_code, ERROR_MESSAGES['unknown_error'])


# 删除了未使用的函数: get_success_message, clean_temp_files