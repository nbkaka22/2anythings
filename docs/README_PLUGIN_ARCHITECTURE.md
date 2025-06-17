# 转换器插件架构说明

本项目已实现了基于工厂模式的插件架构，便于添加新的转换格式和管理不同的转换器。

## 架构概述

### 核心组件

1. **ConverterInterface** (`converters/converter_interface.py`)
   - 定义了所有转换器必须实现的接口
   - 提供统一的转换器规范

2. **ConverterFactory** (`converters/converter_factory.py`)
   - 实现工厂模式，管理所有转换器
   - 提供转换器注册、获取、执行转换等功能

3. **PluginManager** (`converters/plugin_manager.py`)
   - 自动发现和加载插件
   - 管理插件生命周期

### 现有转换器

- **PDFToDocxConverter**: PDF转Word文档
- **PDFToPPTConverter**: PDF转PowerPoint演示文稿
- **WordToPPTConverter**: Word文档转PowerPoint演示文稿

## 使用方法

### 基本使用

```python
from converters.converter_factory import ConverterFactory
from converters.plugin_manager import get_plugin_manager, initialize_plugins

# 初始化插件系统
plugin_manager = get_plugin_manager()
initialize_plugins(plugin_manager)

# 获取转换器工厂实例
factory = ConverterFactory.get_instance()

# 注册插件到工厂
for plugin_name, converter_metadata in plugin_manager.get_all_converters().items():
    factory.register_converter(converter_metadata)

# 执行文件转换
success = factory.convert_file(
    input_path="input.pdf",
    output_path="output.docx",
    input_format="pdf",
    output_format="docx"
)

if success:
    print("转换成功！")
else:
    print("转换失败！")
```

### 获取支持的格式

```python
# 获取所有支持的输入格式
input_formats = factory.get_supported_input_formats()
print(f"支持的输入格式: {input_formats}")

# 获取所有支持的输出格式
output_formats = factory.get_supported_output_formats()
print(f"支持的输出格式: {output_formats}")

# 获取特定输入格式支持的输出格式
output_formats_for_pdf = factory.get_supported_output_formats_for_input("pdf")
print(f"PDF支持的输出格式: {output_formats_for_pdf}")
```

## 开发新的转换器插件

### 步骤1: 实现转换器类

创建一个新的转换器类，继承自 `ConverterInterface`：

```python
from converters.converter_interface import ConverterInterface, ConverterMetadata
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MyCustomConverter(ConverterInterface):
    """自定义转换器"""
    
    def __init__(self):
        self._temp_files = []
    
    @property
    def name(self) -> str:
        return "my_custom_converter"
    
    @property
    def description(self) -> str:
        return "我的自定义转换器"
    
    @property
    def supported_input_formats(self) -> List[str]:
        return ["input_format"]
    
    @property
    def supported_output_formats(self) -> List[str]:
        return ["output_format"]
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def validate_input(self, input_path: str) -> bool:
        """验证输入文件"""
        # 实现输入验证逻辑
        return True
    
    def convert(self, input_path: str, output_path: str, **kwargs) -> bool:
        """执行转换"""
        try:
            # 实现转换逻辑
            logger.info(f"开始转换: {input_path} -> {output_path}")
            
            # 你的转换代码在这里
            
            logger.info("转换完成")
            return True
        except Exception as e:
            logger.error(f"转换失败: {e}")
            return False
    
    def get_default_options(self) -> Dict[str, Any]:
        """获取默认选项"""
        return {}
    
    def get_output_extension(self, input_format: str) -> str:
        """获取输出文件扩展名"""
        return "output_format"
    
    def generate_output_path(self, input_path: str, output_dir: str, output_format: str) -> str:
        """生成输出路径"""
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        extension = self.get_output_extension(output_format)
        return os.path.join(output_dir, f"{base_name}.{extension}")
    
    def cleanup(self):
        """清理临时文件"""
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {temp_file}, {e}")
        self._temp_files.clear()
```

### 步骤2: 定义转换器元数据

```python
# 转换器元数据
MY_CONVERTER_METADATA = ConverterMetadata(
    name="my_custom_converter",
    description="我的自定义转换器",
    version="1.0.0",
    author="你的名字",
    supported_input_formats=["input_format"],
    supported_output_formats=["output_format"],
    converter_class=MyCustomConverter
)
```

### 步骤3: 创建插件注册函数

```python
def register_plugin():
    """注册插件到转换器工厂"""
    from converters.converter_factory import ConverterFactory
    
    factory = ConverterFactory.get_instance()
    factory.register_converter(MY_CONVERTER_METADATA)
    
    return MY_CONVERTER_METADATA
```

### 步骤4: 放置插件文件

将你的转换器文件放在以下位置之一：

1. `converters/` 目录（推荐）
2. 任何通过 `plugin_manager.add_plugin_directory()` 添加的目录

### 步骤5: 测试插件

```python
# 测试你的插件
from converters.plugin_manager import get_plugin_manager, initialize_plugins
from converters.converter_factory import ConverterFactory

# 初始化插件系统
plugin_manager = get_plugin_manager()
initialize_plugins(plugin_manager)

# 获取工厂实例
factory = ConverterFactory.get_instance()

# 注册所有插件
for plugin_name, converter_metadata in plugin_manager.get_all_converters().items():
    factory.register_converter(converter_metadata)

# 测试转换
success = factory.convert_file(
    input_path="test_input.input_format",
    output_path="test_output.output_format",
    input_format="input_format",
    output_format="output_format"
)

print(f"转换结果: {'成功' if success else '失败'}")
```

## 插件目录结构

```
project_root/
├── converters/
│   ├── __init__.py
│   ├── converter_interface.py      # 转换器接口定义
│   ├── converter_factory.py        # 工厂模式实现
│   ├── plugin_manager.py           # 插件管理器
│   ├── pdf_to_docx_converter.py    # PDF转Word转换器
│   ├── pdf_to_ppt_converter.py     # PDF转PPT转换器
│   └── word_to_ppt_converter.py    # Word转PPT转换器
├── custom_plugins/                  # 可选的自定义插件目录
│   └── your_custom_converter.py    # 你的自定义插件
└── pdf_converter.py                # 主应用程序
```

## 高级功能

### 动态加载插件

```python
# 添加新的插件目录
plugin_manager.add_plugin_directory("/path/to/custom/plugins")

# 重新加载所有插件
plugin_manager.reload_all_plugins()
```

### 获取转换器信息

```python
# 获取所有转换器信息
converters_info = factory.get_all_converters_info()
for info in converters_info:
    print(f"转换器: {info['name']} v{info['version']}")
    print(f"描述: {info['description']}")
    print(f"输入格式: {info['supported_input_formats']}")
    print(f"输出格式: {info['supported_output_formats']}")
    print("---")
```

### 错误处理

```python
try:
    success = factory.convert_file(input_path, output_path, input_format, output_format)
    if not success:
        print("转换失败，请检查输入文件和格式")
except Exception as e:
    print(f"转换过程中发生错误: {e}")
```

## 注意事项

1. **依赖管理**: 确保你的插件所需的依赖库已安装
2. **错误处理**: 在转换方法中添加适当的错误处理
3. **日志记录**: 使用logging模块记录转换过程和错误信息
4. **临时文件**: 在cleanup方法中清理所有临时文件
5. **性能考虑**: 对于大文件转换，考虑添加进度回调

## 示例插件

参考 `converters/` 目录中的现有转换器实现，了解完整的插件实现示例。

这个架构使得添加新的转换格式变得非常简单，只需要实现转换器接口并放置在转换器目录中即可自动被发现和加载。