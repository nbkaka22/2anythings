#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF高清化转换器 - 模块化架构使用示例

本示例展示如何使用新的模块化架构进行PDF高清化处理，
包括配置管理、插件使用和自定义扩展。
"""

import os
from PIL import Image
from pdf_upscale_converter import PDFUpscaleConverter
from config_manager import get_config_manager, get_processing_config
from enhancement_plugins import get_plugin_manager, PreprocessingPlugin
from image_processing_toolkit import ImageAnalyzer, ImageProcessingPipeline

def basic_usage_example():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建转换器实例（自动加载配置和插件）
    converter = PDFUpscaleConverter()
    
    # 转换PDF文件
    input_path = "input.pdf"
    output_path = "output_upscaled.pdf"
    
    if os.path.exists(input_path):
        options = {
            'method': 'photo',  # 或 'anime', 'document'
            'scale': 2,
            'quality': 95
        }
        
        result = converter.convert(input_path, output_path, options)
        print(f"转换完成: {result}")
    else:
        print(f"输入文件不存在: {input_path}")

def config_management_example():
    """配置管理示例"""
    print("\n=== 配置管理示例 ===")
    
    # 获取配置管理器
    config_manager = get_config_manager()
    config = get_processing_config()
    
    # 查看当前配置
    print(f"当前Waifu2x缩放倍数: {config.waifu2x.scale}")
    print(f"CLAHE剪切限制: {config.preprocessing.clahe.clip_limit}")
    
    # 修改配置
    config.waifu2x.scale = 4
    config.preprocessing.clahe.clip_limit = 3.0
    config.postprocessing.color_enhancement.saturation_boost = 1.1
    
    # 保存配置
    config_manager.save_config()
    print("配置已保存")
    
    # 导出配置到文件
    config_manager.export_config("my_custom_config.json")
    print("配置已导出到 my_custom_config.json")
    
    # 重置为默认配置
    # config_manager.reset_to_default()
    # print("配置已重置为默认值")

def plugin_usage_example():
    """插件使用示例"""
    print("\n=== 插件使用示例 ===")
    
    # 获取插件管理器
    plugin_manager = get_plugin_manager()
    
    # 列出所有已注册的插件
    plugins = plugin_manager.list_plugins()
    print("已注册的插件:")
    for plugin_type, plugin_list in plugins.items():
        print(f"  {plugin_type}: {[p.name for p in plugin_list]}")
    
    # 使用图像分析器
    analyzer = ImageAnalyzer()
    
    # 创建一个示例图像（实际使用中从文件加载）
    sample_image = Image.new('RGB', (800, 600), color='white')
    
    # 分析图像特征
    features = analyzer.analyze_features(sample_image)
    print(f"\n图像特征分析结果:")
    for key, value in features.items():
        print(f"  {key}: {value}")
    
    # 计算质量评分
    quality_score = analyzer.calculate_quality_score(sample_image)
    print(f"图像质量评分: {quality_score:.3f}")

def custom_plugin_example():
    """自定义插件示例"""
    print("\n=== 自定义插件示例 ===")
    
    class CustomVintagePlugin(PreprocessingPlugin):
        """自定义复古风格预处理插件"""
        
        def __init__(self):
            super().__init__()
            self.name = "vintage_effect"
            self.description = "添加复古风格效果"
        
        def process(self, image: Image.Image, **kwargs) -> Image.Image:
            """应用复古效果"""
            from PIL import ImageEnhance
            
            # 降低饱和度
            enhancer = ImageEnhance.Color(image)
            vintage_image = enhancer.enhance(0.7)
            
            # 增加对比度
            enhancer = ImageEnhance.Contrast(vintage_image)
            vintage_image = enhancer.enhance(1.2)
            
            # 调整亮度
            enhancer = ImageEnhance.Brightness(vintage_image)
            vintage_image = enhancer.enhance(0.9)
            
            return vintage_image
    
    # 注册自定义插件
    plugin_manager = get_plugin_manager()
    custom_plugin = CustomVintagePlugin()
    plugin_manager.register_plugin('vintage_effect', custom_plugin)
    
    print(f"已注册自定义插件: {custom_plugin.name}")
    
    # 使用自定义插件
    sample_image = Image.new('RGB', (400, 300), color='red')
    processed_image = custom_plugin.process(sample_image)
    
    print("自定义插件处理完成")

def pipeline_example():
    """处理管道示例"""
    print("\n=== 处理管道示例 ===")
    
    # 创建处理管道
    pipeline = ImageProcessingPipeline()
    
    # 获取插件管理器
    plugin_manager = get_plugin_manager()
    
    # 添加多个处理器到管道
    pipeline.add_processor(plugin_manager.get_plugin('clahe_preprocessing'))
    pipeline.add_processor(plugin_manager.get_plugin('smart_sharpening'))
    pipeline.add_processor(plugin_manager.get_plugin('color_enhancement'))
    
    print(f"管道中的处理器数量: {len(pipeline.processors)}")
    
    # 创建示例图像
    sample_image = Image.new('RGB', (600, 400), color='blue')
    
    # 执行管道处理
    processed_image = pipeline.process(sample_image)
    
    print("管道处理完成")
    
    # 清空管道
    pipeline.clear()
    print("管道已清空")

def advanced_configuration_example():
    """高级配置示例"""
    print("\n=== 高级配置示例 ===")
    
    config_manager = get_config_manager()
    
    # 为不同类型的图像创建专门的配置
    anime_config = config_manager.get_config_for_method('anime')
    photo_config = config_manager.get_config_for_method('photo')
    document_config = config_manager.get_config_for_method('document')
    
    print("动漫图像配置:")
    print(f"  模型: {anime_config['waifu2x']['model']}")
    print(f"  降噪: {anime_config['waifu2x'].get('noise', 'auto')}")
    
    print("照片图像配置:")
    print(f"  模型: {photo_config['waifu2x']['model']}")
    print(f"  色彩增强: {photo_config['postprocessing']['color_enhancement']}")
    
    print("文档图像配置:")
    print(f"  模型: {document_config['waifu2x']['model']}")
    print(f"  CLAHE设置: {document_config['preprocessing']['clahe']}")

def performance_monitoring_example():
    """性能监控示例"""
    print("\n=== 性能监控示例 ===")
    
    import time
    
    # 创建图像分析器
    analyzer = ImageAnalyzer()
    
    # 创建测试图像
    test_sizes = [(400, 300), (800, 600), (1600, 1200)]
    
    for width, height in test_sizes:
        test_image = Image.new('RGB', (width, height), color='green')
        
        # 测量分析时间
        start_time = time.time()
        features = analyzer.analyze_features(test_image)
        analysis_time = time.time() - start_time
        
        print(f"图像尺寸 {width}x{height}:")
        print(f"  分析时间: {analysis_time:.3f}秒")
        print(f"  边缘密度: {features['edge_density']:.3f}")
        print(f"  复杂度: {features['complexity']:.3f}")

def main():
    """主函数 - 运行所有示例"""
    print("PDF高清化转换器 - 模块化架构使用示例")
    print("=" * 50)
    
    try:
        # 运行各种示例
        basic_usage_example()
        config_management_example()
        plugin_usage_example()
        custom_plugin_example()
        pipeline_example()
        advanced_configuration_example()
        performance_monitoring_example()
        
        print("\n=== 所有示例运行完成 ===")
        
    except Exception as e:
        print(f"运行示例时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()