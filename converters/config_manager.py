"""配置管理模块

提供统一的配置管理功能，支持参数外部化和动态调优。
"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class CLAHEConfig:
    """CLAHE配置"""
    clip_limit: float = 2.0
    tile_grid_size_x: int = 8
    tile_grid_size_y: int = 8
    photo_clip_limit: float = 1.5
    document_clip_limit: float = 3.0


@dataclass
class SharpeningConfig:
    """锐化配置"""
    enabled: bool = True
    base_strength: float = 1.2
    high_edge_factor: float = 0.8
    high_noise_factor: float = 0.6
    unsharp_radius: float = 1.0
    multi_scale_enabled: bool = True
    multi_scale_factors: list = None
    
    def __post_init__(self):
        if self.multi_scale_factors is None:
            self.multi_scale_factors = [0.5, 1.0, 2.0]


@dataclass
class NoiseReductionConfig:
    """噪点抑制配置"""
    enabled: bool = True
    strength: int = 6
    template_window_size: int = 7
    search_window_size: int = 21
    edge_preservation_threshold: float = 0.1
    edge_preservation_alpha: float = 0.7


@dataclass
class ColorEnhancementConfig:
    """色彩增强配置"""
    enabled: bool = True
    saturation_factor: float = 1.1
    contrast_factor: float = 1.05
    min_color_richness: float = 0.3
    high_richness_saturation_factor: float = 0.9
    low_richness_saturation_factor: float = 1.1
    max_saturation_limit: float = 1.3
    white_balance_enabled: bool = True
    white_balance_limit: float = 0.2
    tone_mapping_enabled: bool = True
    tone_mapping_threshold: float = 0.4


@dataclass
class Waifu2xConfig:
    """Waifu2x配置"""
    # 基础配置
    default_scale: int = 2
    default_noise: int = 1
    default_model: str = "models-cunet"
    tta_enabled: bool = False
    tta_mode: bool = False
    
    # 线程配置
    gpu_threads: int = 1
    cpu_threads: int = 4
    
    # 缩放配置
    scale: int = 2
    
    # 动态配置阈值
    small_image_threshold: int = 400000  # 像素数
    large_image_threshold: int = 2000000
    high_complexity_threshold: float = 0.6
    high_edge_threshold: float = 0.15
    high_noise_threshold: float = 0.3
    
    # 瓦片大小配置
    min_tilesize: int = 128
    gpu_tile_size: int = 400
    cpu_tile_size: int = 200
    small_image_tile_size: int = 512
    large_image_tile_size: int = 256
    complex_image_tile_size: int = 200
    
    # GPU瓦片大小配置
    gpu_tilesize_small: int = 512
    gpu_tilesize_medium: int = 400
    gpu_tilesize_large: int = 256
    
    # CPU瓦片大小配置
    cpu_tilesize_small: int = 256
    cpu_tilesize_medium: int = 200
    cpu_tilesize_large: int = 128
    
    # 模型选择配置
    anime_model: str = "models-cunet"
    photo_model: str = "models-real-cunet"
    document_model: str = "models-cunet"
    
    # 噪点级别配置
    low_noise_level: int = 0
    medium_noise_level: int = 1
    high_noise_level: int = 2
    
    # TTA配置
    tta_complexity_threshold: float = 0.7
    tta_importance_threshold: float = 0.6


@dataclass
class QualityAssessmentConfig:
    """质量评估配置"""
    edge_detection_low_threshold: int = 50
    edge_detection_high_threshold: int = 150
    edge_score_multiplier: float = 50.0
    contrast_score_divisor: float = 25.5
    detail_score_divisor: float = 500.0
    noise_score_divisor: float = 10.0
    edge_weight: float = 0.3
    contrast_weight: float = 0.25
    detail_weight: float = 0.25
    noise_weight: float = 0.2

@dataclass
class OutputOptimizationConfig:
    """输出优化配置"""
    jpeg_quality_range: list = None
    png_compression_level: int = 9
    enable_progressive_jpeg: bool = True
    max_file_size_mb: float = 5.0
    quality_vs_size_balance: float = 0.8
    adaptive_quality_enabled: bool = True
    size_priority_mode: bool = False
    webp_enabled: bool = False
    webp_quality: int = 85
    auto_format_selection: bool = True
    
    def __post_init__(self):
        if self.jpeg_quality_range is None:
            self.jpeg_quality_range = [80, 95]


@dataclass
class PostprocessingConfig:
    """后处理配置"""
    enabled: bool = True
    color_enhancement: ColorEnhancementConfig = None
    noise_reduction: NoiseReductionConfig = None
    sharpening: SharpeningConfig = None
    
    def __post_init__(self):
        if self.color_enhancement is None:
            self.color_enhancement = ColorEnhancementConfig()
        if self.noise_reduction is None:
            self.noise_reduction = NoiseReductionConfig()
        if self.sharpening is None:
            self.sharpening = SharpeningConfig()

@dataclass
class ProcessingConfig:
    """处理配置"""
    clahe: CLAHEConfig = None
    sharpening: SharpeningConfig = None
    noise_reduction: NoiseReductionConfig = None
    color_enhancement: ColorEnhancementConfig = None
    waifu2x: Waifu2xConfig = None
    quality_assessment: QualityAssessmentConfig = None
    postprocessing: PostprocessingConfig = None
    output_optimization: OutputOptimizationConfig = None
    
    def __post_init__(self):
        if self.clahe is None:
            self.clahe = CLAHEConfig()
        if self.sharpening is None:
            self.sharpening = SharpeningConfig()
        if self.noise_reduction is None:
            self.noise_reduction = NoiseReductionConfig()
        if self.color_enhancement is None:
            self.color_enhancement = ColorEnhancementConfig()
        if self.waifu2x is None:
            self.waifu2x = Waifu2xConfig()
        if self.quality_assessment is None:
            self.quality_assessment = QualityAssessmentConfig()
        if self.postprocessing is None:
            self.postprocessing = PostprocessingConfig()
        if self.output_optimization is None:
            self.output_optimization = OutputOptimizationConfig()


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # 默认配置目录
            self.config_dir = Path(__file__).parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "processing_config.json"
        self._config = None
    
    def load_config(self) -> ProcessingConfig:
        """加载配置"""
        if self._config is not None:
            return self._config
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                self._config = self._dict_to_config(config_dict)
            else:
                # 创建默认配置
                self._config = ProcessingConfig()
                self.save_config(self._config)
        except Exception as e:
            print(f"配置加载失败，使用默认配置: {e}")
            self._config = ProcessingConfig()
        
        return self._config
    
    def save_config(self, config: ProcessingConfig) -> bool:
        """保存配置"""
        try:
            config_dict = self._config_to_dict(config)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            self._config = config
            return True
        except Exception as e:
            print(f"配置保存失败: {e}")
            return False
    
    def update_config(self, **kwargs) -> bool:
        """更新配置"""
        try:
            config = self.load_config()
            
            # 支持嵌套更新
            for key, value in kwargs.items():
                if hasattr(config, key):
                    if isinstance(value, dict):
                        # 更新子配置
                        sub_config = getattr(config, key)
                        for sub_key, sub_value in value.items():
                            if hasattr(sub_config, sub_key):
                                setattr(sub_config, sub_key, sub_value)
                    else:
                        setattr(config, key, value)
            
            return self.save_config(config)
        except Exception as e:
            print(f"配置更新失败: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            default_config = ProcessingConfig()
            return self.save_config(default_config)
        except Exception as e:
            print(f"重置配置失败: {e}")
            return False
    
    def get_config(self) -> ProcessingConfig:
        """获取当前配置"""
        return self.load_config()
    
    def get_config_for_method(self, method: str) -> Dict[str, Any]:
        """获取特定方法的配置"""
        config = self.load_config()
        
        if method == "anime":
            return {
                'clahe': asdict(config.clahe),
                'sharpening': asdict(config.sharpening),
                'color_enhancement': asdict(config.color_enhancement),
                'waifu2x': {**asdict(config.waifu2x), 'model': config.waifu2x.anime_model}
            }
        elif method == "photo":
            return {
                'clahe': {**asdict(config.clahe), 'clip_limit': config.clahe.photo_clip_limit},
                'sharpening': asdict(config.sharpening),
                'color_enhancement': asdict(config.color_enhancement),
                'noise_reduction': asdict(config.noise_reduction),
                'waifu2x': {**asdict(config.waifu2x), 'model': config.waifu2x.photo_model}
            }
        elif method == "document":
            return {
                'clahe': {**asdict(config.clahe), 'clip_limit': config.clahe.document_clip_limit},
                'sharpening': {**asdict(config.sharpening), 'base_strength': 1.4},
                'waifu2x': {**asdict(config.waifu2x), 'model': config.waifu2x.document_model}
            }
        else:
            return asdict(config)
    
    def _config_to_dict(self, config: ProcessingConfig) -> Dict[str, Any]:
        """配置对象转字典"""
        return {
            'clahe': asdict(config.clahe),
            'sharpening': asdict(config.sharpening),
            'noise_reduction': asdict(config.noise_reduction),
            'color_enhancement': asdict(config.color_enhancement),
            'waifu2x': asdict(config.waifu2x),
            'quality_assessment': asdict(config.quality_assessment),
            'postprocessing': asdict(config.postprocessing),
            'output_optimization': asdict(config.output_optimization)
        }
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> ProcessingConfig:
        """字典转配置对象"""
        # 处理后处理配置的嵌套结构
        postprocessing_dict = config_dict.get('postprocessing', {})
        postprocessing_config = PostprocessingConfig(
            enabled=postprocessing_dict.get('enabled', True),
            color_enhancement=ColorEnhancementConfig(**postprocessing_dict.get('color_enhancement', {})),
            noise_reduction=NoiseReductionConfig(**postprocessing_dict.get('noise_reduction', {})),
            sharpening=SharpeningConfig(**postprocessing_dict.get('sharpening', {}))
        )
        
        return ProcessingConfig(
            clahe=CLAHEConfig(**config_dict.get('clahe', {})),
            sharpening=SharpeningConfig(**config_dict.get('sharpening', {})),
            noise_reduction=NoiseReductionConfig(**config_dict.get('noise_reduction', {})),
            color_enhancement=ColorEnhancementConfig(**config_dict.get('color_enhancement', {})),
            waifu2x=Waifu2xConfig(**config_dict.get('waifu2x', {})),
            quality_assessment=QualityAssessmentConfig(**config_dict.get('quality_assessment', {})),
            postprocessing=postprocessing_config,
            output_optimization=OutputOptimizationConfig(**config_dict.get('output_optimization', {}))
        )
    
    def export_config(self, export_path: str) -> bool:
        """导出配置到指定路径"""
        try:
            config = self.load_config()
            config_dict = self._config_to_dict(config)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"配置导出失败: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """从指定路径导入配置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            config = self._dict_to_config(config_dict)
            return self.save_config(config)
        except Exception as e:
            print(f"配置导入失败: {e}")
            return False


# 全局配置管理器实例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_processing_config() -> ProcessingConfig:
    """获取处理配置"""
    return get_config_manager().load_config()