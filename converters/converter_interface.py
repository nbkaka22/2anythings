"""转换器接口定义

定义了所有转换器必须实现的基础接口，确保插件架构的一致性。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import os

class ConverterInterface(ABC):
    """转换器基础接口
    
    所有转换器插件都必须继承此接口并实现相应方法
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """转换器名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """转换器描述"""
        pass
    
    @property
    @abstractmethod
    def supported_input_formats(self) -> List[str]:
        """支持的输入格式列表"""
        pass
    
    @property
    @abstractmethod
    def supported_output_formats(self) -> List[str]:
        """支持的输出格式列表"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """转换器版本"""
        pass
    
    @abstractmethod
    def validate_input(self, input_path: str) -> bool:
        """验证输入文件是否有效
        
        Args:
            input_path: 输入文件路径
            
        Returns:
            bool: 文件是否有效
        """
        pass
    
    @abstractmethod
    def convert(self, input_path: str, output_path: str, **kwargs) -> bool:
        """执行转换
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            **kwargs: 转换参数
            
        Returns:
            bool: 转换是否成功
        """
        pass
    
    @abstractmethod
    def get_default_options(self) -> Dict[str, Any]:
        """获取默认转换选项
        
        Returns:
            Dict[str, Any]: 默认选项字典
        """
        pass
    
    def get_output_extension(self, output_format: str) -> str:
        """根据输出格式获取文件扩展名
        
        Args:
            output_format: 输出格式
            
        Returns:
            str: 文件扩展名（包含点号）
        """
        format_extensions = {
            'pdf': '.pdf',
            'docx': '.docx',
            'pptx': '.pptx',
            'txt': '.txt',
            'jpg': '.jpg',
            'png': '.png',
            'jpeg': '.jpeg'
        }
        return format_extensions.get(output_format.lower(), f'.{output_format.lower()}')
    
    def generate_output_path(self, input_path: str, output_format: str, output_dir: str = None) -> str:
        """生成输出文件路径
        
        Args:
            input_path: 输入文件路径
            output_format: 输出格式
            output_dir: 输出目录，如果为None则使用输入文件目录
            
        Returns:
            str: 输出文件路径
        """
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        extension = self.get_output_extension(output_format)
        
        if output_dir is None:
            output_dir = os.path.dirname(input_path)
        
        return os.path.join(output_dir, f"{base_name}{extension}")
    
    def cleanup(self):
        """清理临时文件和资源
        
        子类可以重写此方法来清理特定的资源
        """
        pass

class ConverterMetadata:
    """转换器元数据
    
    用于描述转换器的详细信息
    """
    
    def __init__(self, 
                 name: str,
                 description: str,
                 version: str,
                 author: str = "",
                 supported_input_formats: List[str] = None,
                 supported_output_formats: List[str] = None,
                 dependencies: List[str] = None,
                 priority: int = 0):
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.supported_input_formats = supported_input_formats or []
        self.supported_output_formats = supported_output_formats or []
        self.dependencies = dependencies or []
        self.priority = priority  # 优先级，数字越大优先级越高
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'supported_input_formats': self.supported_input_formats,
            'supported_output_formats': self.supported_output_formats,
            'dependencies': self.dependencies,
            'priority': self.priority
        }