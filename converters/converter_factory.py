"""转换器工厂类

实现工厂模式管理不同的转换器，提供插件架构支持。
"""

import os
import importlib
import importlib.util
import inspect
from typing import Dict, List, Type, Optional, Any
from .converter_interface import ConverterInterface, ConverterMetadata
import logging

logger = logging.getLogger('pdf_converter')

class ConverterFactory:
    """转换器工厂类
    
    负责管理和创建各种转换器实例，支持插件架构
    """
    
    @classmethod
    def get_instance(cls) -> 'ConverterFactory':
        """获取工厂实例（单例模式）"""
        return get_converter_factory()
    
    def __init__(self):
        self._converters: Dict[str, Type[ConverterInterface]] = {}
        self._metadata: Dict[str, ConverterMetadata] = {}
        self._instances: Dict[str, ConverterInterface] = {}
        self._plugin_directories: List[str] = []
        
        # 注册内置转换器
        self._register_builtin_converters()
        
        # 添加默认插件目录并加载插件
        self._setup_plugin_directories()
        self.load_plugins()
    
    def register_converter(self, 
                          converter_class_or_metadata, 
                          metadata: ConverterMetadata = None) -> bool:
        """注册转换器
        
        Args:
            converter_class_or_metadata: 转换器类或转换器元数据
            metadata: 转换器元数据（当第一个参数是转换器类时使用）
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 检查第一个参数的类型
            if isinstance(converter_class_or_metadata, ConverterMetadata):
                # 第一个参数是元数据
                metadata = converter_class_or_metadata
                converter_name = metadata.name
                
                # 从插件管理器获取转换器类
                from .plugin_manager import get_plugin_manager
                plugin_manager = get_plugin_manager()
                
                if converter_name in plugin_manager.loaded_plugins:
                    converter_class = plugin_manager.loaded_plugins[converter_name]
                else:
                    logger.error(f"未找到转换器类: {converter_name}")
                    return False
            else:
                # 第一个参数是转换器类
                converter_class = converter_class_or_metadata
                
                # 验证转换器类是否实现了接口
                if not issubclass(converter_class, ConverterInterface):
                    logger.error(f"转换器 {converter_class.__name__} 未实现 ConverterInterface 接口")
                    return False
                
                # 创建临时实例以获取基本信息
                temp_instance = converter_class()
                converter_name = temp_instance.name
                
                # 如果没有提供元数据，从实例中获取
                if metadata is None:
                    metadata = ConverterMetadata(
                        name=temp_instance.name,
                        description=temp_instance.description,
                        version=temp_instance.version,
                        supported_input_formats=temp_instance.supported_input_formats,
                        supported_output_formats=temp_instance.supported_output_formats
                    )
            
            # 注册转换器
            self._converters[converter_name] = converter_class
            self._metadata[converter_name] = metadata
            
            logger.info(f"转换器 '{converter_name}' 注册成功")
            return True
            
        except Exception as e:
            logger.error(f"注册转换器失败: {e}")
            return False
    
    def unregister_converter(self, converter_name: str) -> bool:
        """注销转换器
        
        Args:
            converter_name: 转换器名称
            
        Returns:
            bool: 注销是否成功
        """
        try:
            if converter_name in self._converters:
                # 清理实例
                if converter_name in self._instances:
                    self._instances[converter_name].cleanup()
                    del self._instances[converter_name]
                
                # 移除注册信息
                del self._converters[converter_name]
                del self._metadata[converter_name]
                
                logger.info(f"转换器 '{converter_name}' 注销成功")
                return True
            else:
                logger.warning(f"转换器 '{converter_name}' 未找到")
                return False
                
        except Exception as e:
            logger.error(f"注销转换器失败: {e}")
            return False
    
    def get_converter(self, input_format_or_name: str, output_format: str = None) -> Optional[ConverterInterface]:
        """获取转换器实例
        
        Args:
            input_format_or_name: 转换器名称或输入格式
            output_format: 输出格式（当第一个参数是输入格式时使用）
            
        Returns:
            ConverterInterface: 转换器实例，如果不存在返回None
        """
        # 如果只提供一个参数，视为转换器名称
        if output_format is None:
            converter_name = input_format_or_name
            if converter_name not in self._converters:
                logger.error(f"转换器 '{converter_name}' 未注册")
                return None
        else:
            # 如果提供两个参数，视为输入输出格式，查找合适的转换器
            input_format = input_format_or_name
            converters = self.get_converters_for_format(input_format, output_format)
            if not converters:
                logger.error(f"没有找到支持 {input_format} -> {output_format} 转换的转换器")
                return None
            converter_name = converters[0]  # 使用第一个匹配的转换器
        
        # 使用单例模式，避免重复创建实例
        if converter_name not in self._instances:
            try:
                converter_class = self._converters[converter_name]
                self._instances[converter_name] = converter_class()
                logger.debug(f"创建转换器实例: {converter_name}")
            except Exception as e:
                logger.error(f"创建转换器实例失败: {e}")
                return None
        
        return self._instances[converter_name]
    
    def get_converters_for_format(self, input_format: str, output_format: str) -> List[str]:
        """获取支持指定格式转换的转换器列表
        
        Args:
            input_format: 输入格式
            output_format: 输出格式
            
        Returns:
            List[str]: 支持的转换器名称列表，按优先级排序
        """
        suitable_converters = []
        
        for name, metadata in self._metadata.items():
            if (input_format.lower() in [fmt.lower() for fmt in metadata.supported_input_formats] and
                output_format.lower() in [fmt.lower() for fmt in metadata.supported_output_formats]):
                suitable_converters.append((name, metadata.priority))
        
        # 按优先级排序（优先级高的在前）
        suitable_converters.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in suitable_converters]
    
    def get_all_converters(self) -> Dict[str, ConverterMetadata]:
        """获取所有已注册的转换器信息
        
        Returns:
            Dict[str, ConverterMetadata]: 转换器名称到元数据的映射
        """
        return self._metadata.copy()
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取所有支持的格式
        
        Returns:
            Dict[str, List[str]]: 包含 'input' 和 'output' 键的字典
        """
        input_formats = set()
        output_formats = set()
        
        for metadata in self._metadata.values():
            input_formats.update(metadata.supported_input_formats)
            output_formats.update(metadata.supported_output_formats)
        
        return {
            'input': sorted(list(input_formats)),
            'output': sorted(list(output_formats))
        }
    
    def get_supported_input_formats(self) -> List[str]:
        """获取所有支持的输入格式"""
        formats = self.get_supported_formats()
        return formats['input']
    
    def get_supported_output_formats(self) -> List[str]:
        """获取所有支持的输出格式"""
        formats = self.get_supported_formats()
        return formats['output']
    
    def get_supported_output_formats_for_input(self, input_format: str) -> List[str]:
        """获取特定输入格式支持的输出格式"""
        output_formats = set()
        
        for metadata in self._metadata.values():
            if input_format.lower() in [fmt.lower() for fmt in metadata.supported_input_formats]:
                output_formats.update(metadata.supported_output_formats)
        
        return sorted(list(output_formats))
    
    def get_all_converters_info(self) -> List[Dict[str, Any]]:
        """获取所有转换器的详细信息"""
        info_list = []
        
        for metadata in self._metadata.values():
            info = {
                'name': metadata.name,
                'description': metadata.description,
                'version': metadata.version,
                'supported_input_formats': metadata.supported_input_formats,
                'supported_output_formats': metadata.supported_output_formats
            }
            
            if hasattr(metadata, 'author') and metadata.author:
                info['author'] = metadata.author
            
            info_list.append(info)
        
        return info_list
    
    def is_conversion_supported(self, input_format: str, output_format: str) -> bool:
        """检查是否支持特定的转换"""
        converter = self.get_converter(input_format, output_format)
        return converter is not None
    
    def convert_file(self, 
                    input_path: str, 
                    output_path: str, 
                    input_format: str = None, 
                    output_format: str = None,
                    converter_name: str = None,
                    **kwargs) -> bool:
        """执行文件转换
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            input_format: 输入格式（如果为None则从文件扩展名推断）
            output_format: 输出格式（如果为None则从输出路径推断）
            converter_name: 指定使用的转换器名称（如果为None则自动选择）
            **kwargs: 传递给转换器的额外参数
            
        Returns:
            bool: 转换是否成功
        """
        try:
            # 推断格式
            if input_format is None:
                input_format = os.path.splitext(input_path)[1][1:].lower()
            if output_format is None:
                output_format = os.path.splitext(output_path)[1][1:].lower()
            
            # 选择转换器
            if converter_name is None:
                suitable_converters = self.get_converters_for_format(input_format, output_format)
                if not suitable_converters:
                    logger.error(f"没有找到支持 {input_format} -> {output_format} 转换的转换器")
                    return False
                converter_name = suitable_converters[0]  # 使用优先级最高的
            
            # 获取转换器实例
            converter = self.get_converter(converter_name)
            if converter is None:
                return False
            
            # 验证输入文件
            if not converter.validate_input(input_path):
                logger.error(f"输入文件验证失败: {input_path}")
                return False
            
            # 执行转换
            logger.info(f"使用转换器 '{converter_name}' 执行转换: {input_path} -> {output_path}")
            return converter.convert(input_path, output_path, **kwargs)
            
        except Exception as e:
            logger.error(f"文件转换失败: {e}")
            return False
    
    def add_plugin_directory(self, directory: str):
        """添加插件目录
        
        Args:
            directory: 插件目录路径
        """
        if os.path.isdir(directory) and directory not in self._plugin_directories:
            self._plugin_directories.append(directory)
            logger.info(f"添加插件目录: {directory}")
    
    def load_plugins(self):
        """从插件目录加载插件"""
        for plugin_dir in self._plugin_directories:
            self._load_plugins_from_directory(plugin_dir)
    
    def _load_plugins_from_directory(self, directory: str):
        """从指定目录加载插件
        
        Args:
            directory: 插件目录路径
        """
        try:
            for filename in os.listdir(directory):
                if filename.endswith('.py') and not filename.startswith('_'):
                    module_name = filename[:-3]
                    module_path = os.path.join(directory, filename)
                    
                    try:
                        # 动态导入模块
                        spec = importlib.util.spec_from_file_location(module_name, module_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # 查找转换器类
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, ConverterInterface) and 
                                obj != ConverterInterface):
                                self.register_converter(obj)
                                
                    except Exception as e:
                        logger.error(f"加载插件失败 {filename}: {e}")
                        
        except Exception as e:
            logger.error(f"扫描插件目录失败 {directory}: {e}")
    
    def _setup_plugin_directories(self):
        """设置插件目录"""
        # 添加当前converters目录作为插件目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.add_plugin_directory(current_dir)
        
        # 添加其他可能的插件目录
        project_root = os.path.dirname(current_dir)
        plugins_dir = os.path.join(project_root, "plugins")
        if os.path.exists(plugins_dir):
            self.add_plugin_directory(plugins_dir)
    
    def _register_builtin_converters(self):
        """注册内置转换器"""
        try:
            # 注册PDF到DOCX转换器
            from .pdf_to_docx_converter import PDFToDocxConverter
            self.register_converter(PDFToDocxConverter)
            
            # 注册PDF到PPT转换器
            from .pdf_to_ppt_converter import PDFToPPTConverter
            self.register_converter(PDFToPPTConverter)
            
            # 注册Word到PPT转换器
            from .word_to_ppt_converter import WordToPPTConverter
            self.register_converter(WordToPPTConverter)
            
            logger.info("内置转换器注册完成")
            
        except ImportError as e:
            logger.warning(f"部分内置转换器导入失败: {e}")
        except Exception as e:
            logger.error(f"注册内置转换器失败: {e}")
    
    def cleanup_all(self):
        """清理所有转换器实例"""
        for instance in self._instances.values():
            try:
                instance.cleanup()
            except Exception as e:
                logger.error(f"清理转换器实例失败: {e}")
        
        self._instances.clear()
        logger.info("所有转换器实例已清理")

# 全局工厂实例
_converter_factory = None

def get_converter_factory() -> ConverterFactory:
    """获取全局转换器工厂实例"""
    global _converter_factory
    if _converter_factory is None:
        _converter_factory = ConverterFactory()
    return _converter_factory

# 为了向后兼容
converter_factory = get_converter_factory()