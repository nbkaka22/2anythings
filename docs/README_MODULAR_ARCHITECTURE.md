# PDF高清化转换器 - 模块化架构说明

## 概述

本项目已完成模块化重构，将图像处理算法抽取为独立的工具类，实现了配置管理和插件架构，大幅提高了代码的复用性、可维护性和可扩展性。

## 架构组件

### 1. 图像处理工具包 (`image_processing_toolkit.py`)

#### 核心类
- **`ImageAnalyzer`**: 图像特征分析器
  - 分析图像的边缘密度、对比度、噪声水平等特征
  - 计算图像质量评分
  - 支持复杂度评估和色彩丰富度分析

- **`ImageProcessor`**: 抽象基类
  - 定义图像处理器的标准接口
  - 支持参数配置和处理结果验证

- **`ImageProcessingPipeline`**: 处理管道
  - 管理多个图像处理器的执行顺序
  - 支持动态添加和移除处理器
  - 提供统一的处理接口

#### 内置处理器
- **`CLAHEProcessor`**: 自适应直方图均衡化
- **`SmartSharpeningProcessor`**: 智能锐化
- **`NoiseReductionProcessor`**: 噪声抑制
- **`ColorEnhancementProcessor`**: 色彩增强

### 2. 配置管理器 (`config_manager.py`)

#### 功能特性
- **外部化配置**: 所有算法参数存储在JSON配置文件中
- **类型安全**: 使用dataclass定义配置结构
- **动态加载**: 支持运行时重新加载配置
- **配置验证**: 自动验证配置参数的有效性
- **配置导入导出**: 支持配置的备份和恢复

#### 配置类别
- **预处理配置**: CLAHE、锐化等参数
- **后处理配置**: 噪声抑制、色彩增强等参数
- **Waifu2x配置**: 模型选择、瓦片大小等参数
- **质量评估配置**: 评分权重和阈值设置

### 3. 插件架构 (`enhancement_plugins.py`)

#### 插件类型
- **`PreprocessingPlugin`**: 预处理插件基类
- **`PostprocessingPlugin`**: 后处理插件基类
- **`UpscalingPlugin`**: 放大算法插件基类

#### 插件管理器
- **动态注册**: 支持运行时注册和注销插件
- **插件发现**: 自动加载外部插件模块
- **类型管理**: 按插件类型分类管理
- **批量处理**: 支持按类型批量执行插件

#### 内置插件
- **`CLAHEPreprocessingPlugin`**: CLAHE预处理插件
- **`SmartSharpeningPlugin`**: 智能锐化插件
- **`NoiseReductionPlugin`**: 噪声抑制插件
- **`ColorEnhancementPlugin`**: 色彩增强插件

## 使用方法

### 1. 基本使用

```python
from converters.pdf_upscale_converter import PDFUpscaleConverter

# 创建转换器实例（自动加载配置和插件）
converter = PDFUpscaleConverter()

# 正常使用转换功能
result = converter.convert(input_path, output_path, options)
```

### 2. 配置管理

```python
from converters.config_manager import get_config_manager

# 获取配置管理器
config_manager = get_config_manager()

# 修改配置
config = config_manager.get_config()
config.waifu2x.scale = 4
config.preprocessing.clahe.clip_limit = 3.0

# 保存配置
config_manager.save_config()

# 重置为默认配置
config_manager.reset_to_default()
```

### 3. 自定义插件开发

```python
from converters.enhancement_plugins import PreprocessingPlugin
from PIL import Image

class CustomPreprocessingPlugin(PreprocessingPlugin):
    def __init__(self):
        super().__init__()
        self.name = "custom_preprocessing"
        self.description = "自定义预处理插件"
    
    def process(self, image: Image.Image, **kwargs) -> Image.Image:
        # 实现自定义处理逻辑
        processed_image = image.copy()
        # ... 处理代码 ...
        return processed_image

# 注册插件
from converters.enhancement_plugins import get_plugin_manager
plugin_manager = get_plugin_manager()
plugin_manager.register_plugin('custom_preprocessing', CustomPreprocessingPlugin())
```

### 4. 外部插件加载

```python
# 创建外部插件文件 my_plugin.py
class MyEnhancementPlugin(PreprocessingPlugin):
    # ... 插件实现 ...
    pass

# 加载外部插件
from converters.enhancement_plugins import load_external_plugin
load_external_plugin('path/to/my_plugin.py')
```

## 配置文件说明

配置文件位于 `converters/processing_config.json`，包含以下主要部分：

### 预处理配置
```json
{
  "preprocessing": {
    "clahe": {
      "enabled": true,
      "clip_limit": 2.0,
      "tile_grid_size": [8, 8],
      "adaptive_clip_limit": true
    },
    "sharpening": {
      "enabled": true,
      "base_strength": 1.1,
      "adaptive_strength": true
    }
  }
}
```

### Waifu2x配置
```json
{
  "waifu2x": {
    "scale": 2,
    "anime_model": "models-cunet",
    "photo_model": "models-cunet",
    "gpu_tilesize_small": 640,
    "cpu_tilesize_small": 256
  }
}
```

## 优势

### 1. 模块化设计
- **高内聚低耦合**: 每个模块职责单一，相互独立
- **易于测试**: 可以单独测试每个组件
- **代码复用**: 图像处理算法可在其他项目中复用

### 2. 配置管理
- **参数外部化**: 无需修改代码即可调整算法参数
- **环境适配**: 可为不同环境提供不同配置
- **版本控制**: 配置文件可独立进行版本管理

### 3. 插件架构
- **动态扩展**: 支持运行时添加新的处理算法
- **向后兼容**: 新插件不影响现有功能
- **第三方集成**: 便于集成第三方图像处理算法

### 4. 可维护性
- **清晰结构**: 代码组织更加清晰
- **易于调试**: 问题定位更加精确
- **文档完善**: 每个组件都有详细的文档说明

## 扩展指南

### 添加新的图像处理算法
1. 继承 `ImageProcessor` 基类
2. 实现 `process` 方法
3. 在配置文件中添加相应参数
4. 注册为插件

### 添加新的配置项
1. 在相应的配置dataclass中添加字段
2. 更新默认配置文件
3. 在处理逻辑中使用新配置

### 性能优化
1. 使用图像分析器识别处理需求
2. 根据图像特征动态选择算法
3. 利用配置管理器调整性能参数

## 注意事项

1. **配置文件格式**: 确保JSON格式正确，避免语法错误
2. **插件兼容性**: 自定义插件需要遵循接口规范
3. **性能考虑**: 过多的插件可能影响处理速度
4. **错误处理**: 插件异常不应影响主流程

## 未来规划

1. **Web界面**: 提供基于Web的配置管理界面
2. **插件市场**: 建立插件分享和下载平台
3. **自动调优**: 基于机器学习的参数自动优化
4. **分布式处理**: 支持多机器协同处理大型文档