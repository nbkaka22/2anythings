"""图像增强插件架构

提供可扩展的插件系统，支持动态加载和管理不同的图像增强算法。
"""

import importlib
import inspect
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Callable
from PIL import Image
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    category: str
    priority: int = 50  # 优先级，数值越小优先级越高
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class EnhancementPlugin(ABC):
    """图像增强插件抽象基类"""
    
    @abstractmethod
    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        pass
    
    @abstractmethod
    def is_applicable(self, image: Image.Image, features: Dict[str, Any], method: str) -> bool:
        """判断插件是否适用于当前图像和方法"""
        pass
    
    @abstractmethod
    def process(self, image: Image.Image, features: Dict[str, Any], 
                config: Dict[str, Any], **kwargs) -> Image.Image:
        """处理图像"""
        pass
    
    @abstractmethod
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置有效性"""
        return True
    
    def get_processing_time_estimate(self, image: Image.Image) -> float:
        """估算处理时间（秒）"""
        # 基于图像尺寸的简单估算
        pixels = image.size[0] * image.size[1]
        return pixels / 1000000  # 每百万像素约1秒


class PreprocessingPlugin(EnhancementPlugin):
    """预处理插件基类"""
    pass


class PostprocessingPlugin(EnhancementPlugin):
    """后处理插件基类"""
    pass


class UpscalingPlugin(EnhancementPlugin):
    """放大算法插件基类"""
    
    @abstractmethod
    def upscale(self, image: Image.Image, scale: int, **kwargs) -> Image.Image:
        """放大图像"""
        pass


# 内置插件实现

class CLAHEPreprocessingPlugin(PreprocessingPlugin):
    """CLAHE预处理插件"""
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="CLAHE",
            version="1.0.0",
            description="自适应直方图均衡化预处理",
            author="System",
            category="preprocessing",
            priority=10
        )
    
    def is_applicable(self, image: Image.Image, features: Dict[str, Any], method: str) -> bool:
        # 对所有图像都适用
        return True
    
    def process(self, image: Image.Image, features: Dict[str, Any], 
                config: Dict[str, Any], **kwargs) -> Image.Image:
        try:
            import cv2
            import numpy as np
            
            clip_limit = config.get('clip_limit', 2.0)
            tile_size = config.get('tile_grid_size', (8, 8))
            
            img_array = np.array(image)
            
            if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
                # 彩色图像：在LAB色彩空间处理
                lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
                l, a, b = cv2.split(lab)
                
                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
                l = clahe.apply(l)
                
                lab = cv2.merge([l, a, b])
                result = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
                return Image.fromarray(result, mode=image.mode)
            else:
                # 灰度图像
                if len(img_array.shape) == 3:
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img_array
                
                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
                enhanced = clahe.apply(gray)
                
                if image.mode == 'RGB':
                    result = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
                    return Image.fromarray(result, mode='RGB')
                else:
                    return Image.fromarray(enhanced, mode='L')
        except Exception:
            return image
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            'clip_limit': 2.0,
            'tile_grid_size': (8, 8)
        }


class SmartSharpeningPlugin(PreprocessingPlugin):
    """智能锐化插件"""
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="SmartSharpening",
            version="1.0.0",
            description="基于图像特征的智能锐化",
            author="System",
            category="preprocessing",
            priority=20
        )
    
    def is_applicable(self, image: Image.Image, features: Dict[str, Any], method: str) -> bool:
        # 对边缘密度较低的图像更有效
        edge_density = features.get('edge_density', 0)
        return edge_density < 0.3
    
    def process(self, image: Image.Image, features: Dict[str, Any], 
                config: Dict[str, Any], **kwargs) -> Image.Image:
        try:
            import cv2
            import numpy as np
            
            base_strength = config.get('base_strength', 1.2)
            edge_density = features.get('edge_density', 0.1)
            noise_level = features.get('noise_level', 0.1)
            
            # 自适应强度调整
            if edge_density > 0.15:
                strength = base_strength * 0.8
            elif noise_level > 0.3:
                strength = base_strength * 0.6
            else:
                strength = base_strength
            
            img_array = np.array(image)
            blurred = cv2.GaussianBlur(img_array, (0, 0), 1.0)
            sharpened = cv2.addWeighted(img_array, 1.0 + strength, blurred, -strength, 0)
            sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
            
            return Image.fromarray(sharpened, mode=image.mode)
        except Exception:
            return image
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            'base_strength': 1.2,
            'radius': 1.0
        }


class NoiseReductionPlugin(PostprocessingPlugin):
    """噪点抑制插件"""
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="NoiseReduction",
            version="1.0.0",
            description="智能噪点抑制",
            author="System",
            category="postprocessing",
            priority=30
        )
    
    def is_applicable(self, image: Image.Image, features: Dict[str, Any], method: str) -> bool:
        # 对高噪点图像更有效
        noise_level = features.get('noise_level', 0)
        return noise_level > 0.2
    
    def process(self, image: Image.Image, features: Dict[str, Any], 
                config: Dict[str, Any], **kwargs) -> Image.Image:
        try:
            import cv2
            import numpy as np
            
            strength = config.get('strength', 6)
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                denoised = cv2.fastNlMeansDenoisingColored(img_array, None, 
                                                         strength, strength, 7, 21)
            else:
                denoised = cv2.fastNlMeansDenoising(img_array, None, strength, 7, 21)
            
            return Image.fromarray(denoised, mode=image.mode)
        except Exception:
            return image
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            'strength': 6,
            'template_window_size': 7,
            'search_window_size': 21
        }


class ColorEnhancementPlugin(PostprocessingPlugin):
    """色彩增强插件"""
    
    def get_info(self) -> PluginInfo:
        return PluginInfo(
            name="ColorEnhancement",
            version="1.0.0",
            description="智能色彩增强",
            author="System",
            category="postprocessing",
            priority=40
        )
    
    def is_applicable(self, image: Image.Image, features: Dict[str, Any], method: str) -> bool:
        # 对彩色图像有效
        return image.mode in ['RGB', 'RGBA'] and features.get('color_richness', 0) > 0.1
    
    def process(self, image: Image.Image, features: Dict[str, Any], 
                config: Dict[str, Any], **kwargs) -> Image.Image:
        try:
            from PIL import ImageEnhance
            
            saturation_factor = config.get('saturation_factor', 1.1)
            contrast_factor = config.get('contrast_factor', 1.05)
            color_richness = features.get('color_richness', 0.3)
            
            enhanced = image.copy()
            
            # 自适应饱和度
            if color_richness > 0.5:
                saturation = saturation_factor * 0.9
            else:
                saturation = saturation_factor * 1.1
            
            enhancer = ImageEnhance.Color(enhanced)
            enhanced = enhancer.enhance(min(saturation, 1.3))
            
            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(contrast_factor)
            
            return enhanced
        except Exception:
            return image
    
    def get_default_config(self) -> Dict[str, Any]:
        return {
            'saturation_factor': 1.1,
            'contrast_factor': 1.05
        }


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, EnhancementPlugin] = {}
        self.preprocessing_plugins: List[EnhancementPlugin] = []
        self.postprocessing_plugins: List[EnhancementPlugin] = []
        self.upscaling_plugins: List[EnhancementPlugin] = []
        
        # 注册内置插件
        self._register_builtin_plugins()
    
    def _register_builtin_plugins(self):
        """注册内置插件"""
        builtin_plugins = [
            CLAHEPreprocessingPlugin(),
            SmartSharpeningPlugin(),
            NoiseReductionPlugin(),
            ColorEnhancementPlugin()
        ]
        
        for plugin in builtin_plugins:
            self.register_plugin(plugin)
    
    def register_plugin(self, plugin: EnhancementPlugin) -> bool:
        """注册插件"""
        try:
            info = plugin.get_info()
            
            # 检查依赖
            if not self._check_dependencies(info.dependencies):
                print(f"插件 {info.name} 依赖检查失败")
                return False
            
            # 注册插件
            self.plugins[info.name] = plugin
            
            # 按类型分类
            if isinstance(plugin, PreprocessingPlugin):
                self.preprocessing_plugins.append(plugin)
                self.preprocessing_plugins.sort(key=lambda p: p.get_info().priority)
            elif isinstance(plugin, PostprocessingPlugin):
                self.postprocessing_plugins.append(plugin)
                self.postprocessing_plugins.sort(key=lambda p: p.get_info().priority)
            elif isinstance(plugin, UpscalingPlugin):
                self.upscaling_plugins.append(plugin)
                self.upscaling_plugins.sort(key=lambda p: p.get_info().priority)
            
            print(f"插件 {info.name} v{info.version} 注册成功")
            return True
            
        except Exception as e:
            print(f"插件注册失败: {e}")
            return False
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        """注销插件"""
        try:
            if plugin_name in self.plugins:
                plugin = self.plugins[plugin_name]
                
                # 从分类列表中移除
                if isinstance(plugin, PreprocessingPlugin):
                    self.preprocessing_plugins.remove(plugin)
                elif isinstance(plugin, PostprocessingPlugin):
                    self.postprocessing_plugins.remove(plugin)
                elif isinstance(plugin, UpscalingPlugin):
                    self.upscaling_plugins.remove(plugin)
                
                del self.plugins[plugin_name]
                print(f"插件 {plugin_name} 注销成功")
                return True
            else:
                print(f"插件 {plugin_name} 不存在")
                return False
                
        except Exception as e:
            print(f"插件注销失败: {e}")
            return False
    
    def get_applicable_plugins(self, image: Image.Image, features: Dict[str, Any], 
                             method: str, category: str = None) -> List[EnhancementPlugin]:
        """获取适用的插件"""
        applicable = []
        
        if category == "preprocessing" or category is None:
            for plugin in self.preprocessing_plugins:
                if plugin.is_applicable(image, features, method):
                    applicable.append(plugin)
        
        if category == "postprocessing" or category is None:
            for plugin in self.postprocessing_plugins:
                if plugin.is_applicable(image, features, method):
                    applicable.append(plugin)
        
        if category == "upscaling" or category is None:
            for plugin in self.upscaling_plugins:
                if plugin.is_applicable(image, features, method):
                    applicable.append(plugin)
        
        return applicable
    
    def process_with_plugins(self, image: Image.Image, features: Dict[str, Any], 
                           method: str, config: Dict[str, Any], 
                           category: str, log_callback=None) -> Image.Image:
        """使用插件处理图像"""
        result = image.copy()
        applicable_plugins = self.get_applicable_plugins(image, features, method, category)
        
        for plugin in applicable_plugins:
            try:
                info = plugin.get_info()
                plugin_config = config.get(info.name, plugin.get_default_config())
                
                if plugin.validate_config(plugin_config):
                    result = plugin.process(result, features, plugin_config)
                    if log_callback:
                        log_callback(f"        ✅ 应用插件: {info.name}")
                else:
                    if log_callback:
                        log_callback(f"        ⚠️ 插件配置无效: {info.name}")
                        
            except Exception as e:
                if log_callback:
                    log_callback(f"        ❌ 插件处理失败: {plugin.get_info().name} - {str(e)}")
                continue
        
        return result
    
    def get_plugin(self, plugin_name: str) -> Optional[EnhancementPlugin]:
        """根据名称获取插件实例"""
        return self.plugins.get(plugin_name)
    
    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        if plugin_name in self.plugins:
            return self.plugins[plugin_name].get_info()
        return None
    
    def list_plugins(self, category: str = None) -> List[PluginInfo]:
        """列出插件"""
        plugins_info = []
        
        for plugin in self.plugins.values():
            info = plugin.get_info()
            if category is None or info.category == category:
                plugins_info.append(info)
        
        return sorted(plugins_info, key=lambda x: (x.category, x.priority))
    
    def load_external_plugins(self, plugin_dir: str) -> int:
        """加载外部插件"""
        loaded_count = 0
        plugin_path = Path(plugin_dir)
        
        if not plugin_path.exists():
            return loaded_count
        
        for py_file in plugin_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找插件类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, EnhancementPlugin) and 
                        obj != EnhancementPlugin):
                        
                        plugin_instance = obj()
                        if self.register_plugin(plugin_instance):
                            loaded_count += 1
                            
            except Exception as e:
                print(f"加载插件文件失败 {py_file}: {e}")
                continue
        
        return loaded_count
    
    def _check_dependencies(self, dependencies: List[str]) -> bool:
        """检查依赖"""
        for dep in dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                return False
        return True


# 全局插件管理器实例
_plugin_manager = None

def get_plugin_manager() -> PluginManager:
    """获取全局插件管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager