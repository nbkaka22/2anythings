"""插件管理器

自动发现、加载和管理转换器插件
"""

import os
import sys
import importlib
import importlib.util
import inspect
from typing import Dict, List, Type, Optional
import logging
from pathlib import Path

from converters.converter_interface import ConverterInterface, ConverterMetadata

logger = logging.getLogger('pdf_converter')

class PluginManager:
    """插件管理器
    
    负责插件的发现、加载、注册和管理
    """
    
    def __init__(self, plugin_directories: List[str] = None):
        """初始化插件管理器
        
        Args:
            plugin_directories: 插件目录列表
        """
        self.plugin_directories = plugin_directories or []
        self.loaded_plugins: Dict[str, Type[ConverterInterface]] = {}
        self.plugin_metadata: Dict[str, ConverterMetadata] = {}
        self.plugin_instances: Dict[str, ConverterInterface] = {}
        
        # 添加默认插件目录
        default_plugin_dir = os.path.dirname(__file__)
        if default_plugin_dir not in self.plugin_directories:
            self.plugin_directories.append(default_plugin_dir)
    
    def discover_plugins(self) -> List[str]:
        """发现所有可用的插件
        
        Returns:
            List[str]: 发现的插件文件路径列表
        """
        plugin_files = []
        
        for plugin_dir in self.plugin_directories:
            if not os.path.exists(plugin_dir):
                logger.warning(f"插件目录不存在: {plugin_dir}")
                continue
            
            logger.info(f"扫描插件目录: {plugin_dir}")
            
            # 扫描Python文件
            for file_path in Path(plugin_dir).glob('*.py'):
                if file_path.name.startswith('__'):
                    continue  # 跳过__init__.py等文件
                
                if file_path.name.endswith('_converter.py'):
                    plugin_files.append(str(file_path))
                    logger.debug(f"发现插件文件: {file_path}")
        
        logger.info(f"共发现 {len(plugin_files)} 个插件文件")
        return plugin_files
    
    def load_plugin(self, plugin_path: str) -> bool:
        """加载单个插件
        
        Args:
            plugin_path: 插件文件路径
        
        Returns:
            bool: 加载是否成功
        """
        try:
            # 获取模块名
            module_name = Path(plugin_path).stem
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec is None or spec.loader is None:
                logger.error(f"无法创建模块规范: {plugin_path}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找转换器类
            converter_classes = self._find_converter_classes(module)
            
            if not converter_classes:
                logger.warning(f"插件文件中未找到转换器类: {plugin_path}")
                return False
            
            # 注册找到的转换器类
            for converter_class in converter_classes:
                self._register_converter_class(converter_class, module)
            
            logger.info(f"成功加载插件: {plugin_path}")
            return True
            
        except Exception as e:
            logger.error(f"加载插件失败 {plugin_path}: {e}")
            return False
    
    def _find_converter_classes(self, module) -> List[Type[ConverterInterface]]:
        """在模块中查找转换器类"""
        converter_classes = []
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # 检查是否是ConverterInterface的子类
            if (issubclass(obj, ConverterInterface) and 
                obj != ConverterInterface and 
                obj.__module__ == module.__name__):
                converter_classes.append(obj)
        
        return converter_classes
    
    def _register_converter_class(self, converter_class: Type[ConverterInterface], module):
        """注册转换器类"""
        try:
            # 创建实例以获取基本信息
            instance = converter_class()
            converter_name = instance.name
            
            # 注册类
            self.loaded_plugins[converter_name] = converter_class
            
            # 查找并注册元数据
            metadata = self._find_metadata(module, converter_name)
            if metadata:
                self.plugin_metadata[converter_name] = metadata
            else:
                # 创建默认元数据
                self.plugin_metadata[converter_name] = ConverterMetadata(
                    name=converter_name,
                    description=instance.description,
                    version=instance.version,
                    author="Unknown",
                    supported_input_formats=instance.supported_input_formats,
                    supported_output_formats=instance.supported_output_formats,
                    dependencies=[],
                    priority=5
                )
            
            # 清理临时实例
            instance.cleanup()
            
            # 注册到转换器工厂
            from converters.converter_factory import get_converter_factory
            factory = get_converter_factory()
            factory.register_converter(self.plugin_metadata[converter_name])
            
            logger.info(f"注册转换器: {converter_name}")
            
        except Exception as e:
            logger.error(f"注册转换器类失败: {e}")
    
    def _find_metadata(self, module, converter_name: str) -> Optional[ConverterMetadata]:
        """在模块中查找元数据"""
        # 查找以_METADATA结尾的变量
        metadata_var_name = f"{converter_name.upper()}_METADATA"
        
        if hasattr(module, metadata_var_name):
            metadata = getattr(module, metadata_var_name)
            if isinstance(metadata, ConverterMetadata):
                return metadata
        
        # 查找其他可能的元数据变量名
        for attr_name in dir(module):
            if attr_name.endswith('_METADATA'):
                attr_value = getattr(module, attr_name)
                if isinstance(attr_value, ConverterMetadata):
                    return attr_value
        
        return None
    
    def load_all_plugins(self) -> int:
        """加载所有发现的插件
        
        Returns:
            int: 成功加载的插件数量
        """
        plugin_files = self.discover_plugins()
        loaded_count = 0
        
        for plugin_file in plugin_files:
            if self.load_plugin(plugin_file):
                loaded_count += 1
        
        logger.info(f"插件加载完成: {loaded_count}/{len(plugin_files)} 个插件加载成功")
        return loaded_count
    
    def get_converter(self, converter_name: str) -> Optional[ConverterInterface]:
        """获取转换器实例
        
        Args:
            converter_name: 转换器名称
        
        Returns:
            ConverterInterface: 转换器实例，如果不存在则返回None
        """
        if converter_name not in self.loaded_plugins:
            logger.error(f"转换器未找到: {converter_name}")
            return None
        
        # 如果实例已存在，直接返回
        if converter_name in self.plugin_instances:
            return self.plugin_instances[converter_name]
        
        # 创建新实例
        try:
            converter_class = self.loaded_plugins[converter_name]
            instance = converter_class()
            self.plugin_instances[converter_name] = instance
            return instance
        except Exception as e:
            logger.error(f"创建转换器实例失败 {converter_name}: {e}")
            return None
    
    def get_converters_for_format(self, input_format: str, output_format: str) -> List[str]:
        """获取支持指定格式转换的转换器列表
        
        Args:
            input_format: 输入格式
            output_format: 输出格式
        
        Returns:
            List[str]: 支持该转换的转换器名称列表
        """
        matching_converters = []
        
        for converter_name, converter_class in self.loaded_plugins.items():
            try:
                instance = converter_class()
                if (input_format.lower() in [fmt.lower() for fmt in instance.supported_input_formats] and
                    output_format.lower() in [fmt.lower() for fmt in instance.supported_output_formats]):
                    matching_converters.append(converter_name)
                instance.cleanup()
            except Exception as e:
                logger.warning(f"检查转换器格式支持失败 {converter_name}: {e}")
        
        # 按优先级排序
        matching_converters.sort(key=lambda name: self.plugin_metadata.get(name, ConverterMetadata(
            name=name, description="", version="1.0.0", author="", 
            supported_input_formats=[], supported_output_formats=[], 
            dependencies=[], priority=5
        )).priority, reverse=True)
        
        return matching_converters
    
    def get_all_converters(self) -> Dict[str, ConverterMetadata]:
        """获取所有已加载的转换器信息
        
        Returns:
            Dict[str, ConverterMetadata]: 转换器名称到元数据的映射
        """
        return self.plugin_metadata.copy()
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """获取所有支持的格式
        
        Returns:
            Dict[str, List[str]]: 包含'input'和'output'键的字典
        """
        input_formats = set()
        output_formats = set()
        
        for metadata in self.plugin_metadata.values():
            input_formats.update(fmt.lower() for fmt in metadata.supported_input_formats)
            output_formats.update(fmt.lower() for fmt in metadata.supported_output_formats)
        
        return {
            'input': sorted(list(input_formats)),
            'output': sorted(list(output_formats))
        }
    
    def unload_plugin(self, converter_name: str) -> bool:
        """卸载插件
        
        Args:
            converter_name: 转换器名称
        
        Returns:
            bool: 卸载是否成功
        """
        try:
            # 清理实例
            if converter_name in self.plugin_instances:
                instance = self.plugin_instances[converter_name]
                instance.cleanup()
                del self.plugin_instances[converter_name]
            
            # 移除注册信息
            if converter_name in self.loaded_plugins:
                del self.loaded_plugins[converter_name]
            
            if converter_name in self.plugin_metadata:
                del self.plugin_metadata[converter_name]
            
            logger.info(f"成功卸载插件: {converter_name}")
            return True
            
        except Exception as e:
            logger.error(f"卸载插件失败 {converter_name}: {e}")
            return False
    
    def reload_plugin(self, converter_name: str, plugin_path: str) -> bool:
        """重新加载插件
        
        Args:
            converter_name: 转换器名称
            plugin_path: 插件文件路径
        
        Returns:
            bool: 重新加载是否成功
        """
        # 先卸载
        self.unload_plugin(converter_name)
        
        # 重新加载
        return self.load_plugin(plugin_path)
    
    def cleanup_all(self):
        """清理所有插件实例"""
        for instance in self.plugin_instances.values():
            try:
                instance.cleanup()
            except Exception as e:
                logger.warning(f"清理插件实例失败: {e}")
        
        self.plugin_instances.clear()
        logger.info("所有插件实例已清理")
    
    def add_plugin_directory(self, directory: str):
        """添加插件目录
        
        Args:
            directory: 插件目录路径
        """
        if directory not in self.plugin_directories:
            self.plugin_directories.append(directory)
            logger.info(f"添加插件目录: {directory}")
    
    def validate_plugin(self, plugin_path: str) -> bool:
        """验证插件文件是否有效
        
        Args:
            plugin_path: 插件文件路径
        
        Returns:
            bool: 插件是否有效
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(plugin_path):
                return False
            
            # 尝试导入模块
            module_name = Path(plugin_path).stem
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec is None or spec.loader is None:
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找转换器类
            converter_classes = self._find_converter_classes(module)
            
            return len(converter_classes) > 0
            
        except Exception as e:
            logger.debug(f"插件验证失败 {plugin_path}: {e}")
            return False

# 全局插件管理器实例
_plugin_manager = None

def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager

def initialize_plugins() -> int:
    """初始化并加载所有插件
    
    Returns:
        int: 成功加载的插件数量
    """
    plugin_manager = get_plugin_manager()
    return plugin_manager.load_all_plugins()