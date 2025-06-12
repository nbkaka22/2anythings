# PDF转换工具配置文件

# 应用程序信息
APP_NAME = "PDF格式转换工具"
APP_VERSION = "1.0.0"
APP_AUTHOR = "PDF Converter Team"

# 默认设置
DEFAULT_DPI = 300
MIN_DPI = 72
MAX_DPI = 600

# 支持的文件格式
SUPPORTED_INPUT_FORMATS = ['.pdf']
SUPPORTED_OUTPUT_FORMATS = {
    'document': ['docx', 'txt'],
    'image': ['png', 'jpg']
}

# 文件类型描述
FILE_TYPE_DESCRIPTIONS = {
    'pdf': 'PDF文件',
    'docx': 'Word文档',
    'txt': '文本文件',
    'png': 'PNG图片',
    'jpg': 'JPG图片'
}

# UI设置
WINDOW_SIZE = "800x600"
MIN_WINDOW_SIZE = (600, 400)
LOG_MAX_LINES = 1000

# 转换设置
JPG_QUALITY = 95
MAX_BATCH_SIZE = 100  # 批量处理最大文件数
THREAD_TIMEOUT = 300  # 转换线程超时时间（秒）

# 错误消息
ERROR_MESSAGES = {
    'no_input': '请选择PDF文件或文件夹',
    'no_output': '请选择输出目录',
    'invalid_pdf': 'PDF文件无效或已损坏',
    'permission_denied': '没有权限访问文件或目录',
    'disk_full': '磁盘空间不足',
    'conversion_failed': '转换失败',
    'unknown_error': '发生未知错误'
}

# 成功消息已移除（未使用）