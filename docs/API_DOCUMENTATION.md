# API 文档

## 概述

本文档描述了 PDF 转换器项目的主要 API 接口和使用方法。

## 核心类

### PDFConverter

主要的 PDF 转换器类，提供图形用户界面。

#### 主要方法

- `__init__()`: 初始化转换器
- `run()`: 启动应用程序
- `convert_file()`: 执行文件转换

### ConverterInterface

转换器接口基类，所有转换器插件都必须实现此接口。

#### 必须实现的属性

- `name`: 转换器名称
- `description`: 转换器描述
- `supported_input_formats`: 支持的输入格式列表
- `supported_output_formats`: 支持的输出格式列表
- `version`: 转换器版本

#### 必须实现的方法

- `validate_input(input_path: str) -> bool`: 验证输入文件
- `convert(input_path: str, output_path: str, **kwargs) -> bool`: 执行转换
- `cleanup()`: 清理资源

### ConverterFactory

转换器工厂类，管理所有转换器的注册和获取。

#### 主要方法

- `register_converter(converter_class)`: 注册转换器
- `get_converter(input_format, output_format)`: 获取转换器实例
- `get_supported_formats()`: 获取支持的格式

### PluginManager

插件管理器，负责插件的发现、加载和管理。

#### 主要方法

- `discover_plugins()`: 发现插件文件
- `load_plugin(plugin_path)`: 加载单个插件
- `load_all_plugins()`: 加载所有插件

## 使用示例

### 基本转换

```python
from pdf_converter import PDFConverter

# 创建转换器实例
converter = PDFConverter()

# 执行转换
result = converter.convert_file(
    input_path="input.pdf",
    output_path="output.docx",
    input_format="pdf",
    output_format="docx"
)
```

### 自定义插件开发

```python
from converters.converter_interface import ConverterInterface, ConverterMetadata

class CustomConverter(ConverterInterface):
    @property
    def name(self) -> str:
        return "custom_converter"
    
    @property
    def description(self) -> str:
        return "自定义转换器"
    
    # 实现其他必需的方法...
```

## 错误处理

所有转换操作都会返回布尔值表示成功或失败。详细的错误信息会记录在日志中。

## 配置选项

转换器支持多种配置选项，可以通过 `**kwargs` 参数传递：

- `dpi`: 图像分辨率（默认 150）
- `image_format`: 图像格式（'png' 或 'jpeg'）
- `include_text`: 是否包含文本内容
- `start_page`: 起始页码
- `end_page`: 结束页码