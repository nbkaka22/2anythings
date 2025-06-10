import os
import sys
import time
import shutil
import logging
from datetime import datetime
from config import ERROR_MESSAGES, SUCCESS_MESSAGES

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


def get_file_size(file_path):
    """
    获取文件大小，返回格式化的字符串
    """
    try:
        size = os.path.getsize(file_path)
        # 转换为合适的单位
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0 or unit == 'GB':
                break
            size /= 1024.0
        return f"{size:.2f} {unit}"
    except Exception as e:
        logger.error(f"获取文件大小失败: {file_path}, 错误: {str(e)}")
        return "未知"


def get_file_count(directory, extension='.pdf'):
    """
    获取指定目录中特定扩展名的文件数量
    """
    try:
        count = 0
        for file in os.listdir(directory):
            if file.lower().endswith(extension.lower()):
                count += 1
        return count
    except Exception as e:
        logger.error(f"获取文件数量失败: {directory}, 错误: {str(e)}")
        return 0


def format_time(seconds):
    """
    将秒数格式化为时分秒
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        seconds %= 60
        return f"{int(minutes)}分{int(seconds)}秒"
    else:
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return f"{int(hours)}时{int(minutes)}分{int(seconds)}秒"


def create_timestamp():
    """
    创建时间戳字符串，用于文件名等
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def check_disk_space(directory, required_mb=100):
    """
    检查指定目录所在磁盘的可用空间是否足够
    """
    try:
        if sys.platform == 'win32':
            free_bytes = shutil.disk_usage(directory).free
        else:
            stat = os.statvfs(directory)
            free_bytes = stat.f_bavail * stat.f_frsize
        
        free_mb = free_bytes / (1024 * 1024)
        return free_mb >= required_mb
    except Exception as e:
        logger.error(f"检查磁盘空间失败: {directory}, 错误: {str(e)}")
        return True  # 如果检查失败，假设空间足够


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


def get_success_message(success_code):
    """
    根据成功代码获取成功消息
    """
    return SUCCESS_MESSAGES.get(success_code, SUCCESS_MESSAGES['conversion_complete'])


def clean_temp_files(directory, prefix='temp_', max_age_hours=24):
    """
    清理临时文件
    """
    try:
        current_time = time.time()
        count = 0
        
        for filename in os.listdir(directory):
            if filename.startswith(prefix):
                file_path = os.path.join(directory, filename)
                file_age_hours = (current_time - os.path.getctime(file_path)) / 3600
                
                if file_age_hours > max_age_hours:
                    os.remove(file_path)
                    count += 1
        
        if count > 0:
            logger.info(f"已清理{count}个临时文件")
        
        return count
    except Exception as e:
        logger.error(f"清理临时文件失败: {directory}, 错误: {str(e)}")
        return 0