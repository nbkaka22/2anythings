# 开发指南

## 项目结构

```
2anythings/
├── assets/                        # 资源文件目录
│   └── icon.ico                   # 应用程序图标
├── docs/                          # 文档目录
│   ├── API_DOCUMENTATION.md       # API 文档
│   ├── DEVELOPMENT_GUIDE.md        # 开发指南
│   └── README_PLUGIN_ARCHITECTURE.md # 插件架构文档
├── converters/                    # 转换器插件目录
│   ├── __init__.py
│   ├── converter_interface.py     # 转换器接口定义
│   ├── converter_factory.py       # 转换器工厂
│   ├── plugin_manager.py          # 插件管理器
│   ├── pdf_to_docx_converter.py   # PDF转DOCX转换器
│   ├── pdf_to_ppt_converter.py    # PDF转PPT转换器
│   └── word_to_ppt_converter.py   # Word转PPT转换器
├── config.py                      # 配置文件
├── pdf_converter.py              # 主程序文件
├── pdf_operations.py             # PDF操作工具
├── utils.py                      # 工具函数
├── requirements.txt              # Python依赖
├── environment.yml               # Conda环境配置
├── scripts/                      # 脚本目录
│   ├── dependency_checker.py     # 依赖检查器
│   ├── setup.py                  # 安装脚本
│   └── install_dependencies.bat  # Windows批处理安装脚本
└── README.md                     # 项目说明
```

## 开发环境设置

### 1. 克隆项目

```bash
git clone <repository-url>
cd 2anythings
```

### 2. 安装依赖

#### 使用 pip

```bash
pip install -r requirements.txt
```

#### 使用 conda

```bash
conda env create -f environment.yml
conda activate pdf-converter
```

#### 自动安装

```bash
python scripts/setup.py
```

### 3. 运行程序

```bash
python pdf_converter.py
```

## 插件开发

### 1. 创建新的转换器插件

1. 在 `converters/` 目录下创建新的 Python 文件
2. 继承 `ConverterInterface` 基类
3. 实现所有必需的方法和属性
4. 文件名必须以 `_converter.py` 结尾

### 2. 插件模板

```python
from converters.converter_interface import ConverterInterface, ConverterMetadata
import logging

logger = logging.getLogger('pdf_converter')

class MyConverter(ConverterInterface):
    def __init__(self):
        self._temp_files = []
    
    @property
    def name(self) -> str:
        return "my_converter"
    
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
        # 实现输入验证逻辑
        return True
    
    def convert(self, input_path: str, output_path: str, **kwargs) -> bool:
        # 实现转换逻辑
        try:
            # 转换代码
            return True
        except Exception as e:
            logger.error(f"转换失败: {e}")
            return False
    
    def cleanup(self):
        # 清理临时文件
        for temp_file in self._temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        self._temp_files.clear()

# 可选：定义元数据
MY_CONVERTER_METADATA = ConverterMetadata(
    name="my_converter",
    description="我的自定义转换器",
    version="1.0.0",
    author="Your Name",
    supported_input_formats=["input_format"],
    supported_output_formats=["output_format"],
    dependencies=["required_package"],
    priority=5
)
```

## 代码规范

### 1. 命名规范

- 类名使用 PascalCase
- 函数和变量名使用 snake_case
- 常量使用 UPPER_CASE
- 私有成员以下划线开头

### 2. 文档字符串

所有公共方法都应该包含文档字符串：

```python
def convert(self, input_path: str, output_path: str, **kwargs) -> bool:
    """执行文件转换
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        **kwargs: 转换选项
    
    Returns:
        bool: 转换是否成功
    """
```

### 3. 错误处理

- 使用具体的异常类型而不是通用的 Exception
- 记录详细的错误信息到日志
- 在适当的地方进行资源清理

### 4. 日志记录

```python
import logging

logger = logging.getLogger('pdf_converter')

# 使用适当的日志级别
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

## 测试

### 1. 单元测试

为每个转换器创建对应的测试文件：

```python
import unittest
from converters.my_converter import MyConverter

class TestMyConverter(unittest.TestCase):
    def setUp(self):
        self.converter = MyConverter()
    
    def test_validate_input(self):
        # 测试输入验证
        pass
    
    def test_convert(self):
        # 测试转换功能
        pass
    
    def tearDown(self):
        self.converter.cleanup()
```

### 2. 集成测试

测试完整的转换流程和插件系统。

## 发布流程

1. 更新版本号
2. 运行所有测试
3. 更新文档
4. 创建发布标签
5. 构建分发包

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request
5. 等待代码审查

## 常见问题

### Q: 插件加载失败怎么办？

A: 检查以下几点：
- 文件名是否以 `_converter.py` 结尾
- 是否正确继承了 `ConverterInterface`
- 导入语句是否使用绝对导入
- 是否实现了所有必需的方法

### Q: 如何调试转换问题？

A: 
- 启用调试日志
- 检查输入文件是否有效
- 验证输出路径是否可写
- 查看详细的错误日志