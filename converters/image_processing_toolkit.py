"""图像处理工具包

独立的图像处理算法工具类，提供可复用的图像增强功能。
"""

from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
from typing import Dict, Tuple, Optional, Any
from abc import ABC, abstractmethod


class ImageProcessor(ABC):
    """图像处理器抽象基类"""
    
    @abstractmethod
    def process(self, image: Image.Image, **kwargs) -> Image.Image:
        """处理图像"""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """获取处理器名称"""
        pass


class ImageAnalyzer:
    """图像分析工具类"""
    
    @staticmethod
    def analyze_features(image: Image.Image) -> Dict[str, float]:
        """分析图像特征"""
        try:
            import cv2
            import numpy as np
            
            # 转换为numpy数组
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                height, width, channels = img_array.shape
            else:
                gray = img_array
                height, width = img_array.shape
                channels = 1
            
            features = {}
            
            # 1. 边缘密度分析
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            features['edge_density'] = edge_density
            
            # 2. 噪点水平分析
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            noise_level = min(1.0, laplacian_var / 1000)
            features['noise_level'] = noise_level
            
            # 3. 复杂度分析
            complexity = min(1.0, (edge_density * 2 + noise_level) / 3)
            features['complexity'] = complexity
            
            # 4. 文本检测
            # 使用形态学操作检测文本特征
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            morph = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            text_features = np.sum(morph > 0) / morph.size
            features['has_text'] = text_features > 0.1
            
            # 5. 图像重要性（基于中心区域的复杂度）
            center_y, center_x = height // 2, width // 2
            center_region = gray[center_y-height//4:center_y+height//4, 
                               center_x-width//4:center_x+width//4]
            if center_region.size > 0:
                center_edges = cv2.Canny(center_region, 50, 150)
                center_importance = np.sum(center_edges > 0) / center_edges.size
            else:
                center_importance = 0
            features['importance'] = center_importance
            
            # 6. 色彩丰富度
            if channels >= 3:
                # 计算色彩分布的标准差
                color_std = np.std(img_array.reshape(-1, channels), axis=0)
                color_richness = np.mean(color_std) / 255.0
            else:
                color_richness = 0
            features['color_richness'] = color_richness
            
            # 7. 对比度分析
            contrast = gray.std() / 255.0  # 归一化到0-1范围
            features['contrast'] = contrast

            return features
            
        except Exception as e:
            # 返回默认特征
            return {
                'edge_density': 0.1,
                'noise_level': 0.1,
                'complexity': 0.3,
                'has_text': False,
                'importance': 0.5,
                'color_richness': 0.3
            }
    
    @staticmethod
    def analyze_image_features(image: Image.Image) -> Dict[str, float]:
        """分析图像特征 - analyze_features方法的别名"""
        return ImageAnalyzer.analyze_features(image)
    
    @staticmethod
    def calculate_quality_score(image: Image.Image) -> float:
        """计算图像质量评分"""
        try:
            import cv2
            import numpy as np
            
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            scores = []
            
            # 1. 边缘清晰度评分 (0-10)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            edge_score = min(10.0, edge_density * 50)
            scores.append(edge_score)
            
            # 2. 对比度评分 (0-10)
            contrast = gray.std()
            contrast_score = min(10.0, contrast / 25.5)
            scores.append(contrast_score)
            
            # 3. 细节丰富度评分 (0-10)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            detail_score = min(10.0, laplacian_var / 500)
            scores.append(detail_score)
            
            # 4. 噪点控制评分 (0-10)
            kernel = np.array([[-1,-1,-1],[-1,8,-1],[-1,-1,-1]])
            noise_response = cv2.filter2D(gray, -1, kernel)
            noise_level = np.std(noise_response)
            noise_score = max(0.0, 10.0 - noise_level / 10)
            scores.append(noise_score)
            
            return min(10.0, max(0.0, np.mean(scores)))
            
        except Exception:
            return 5.0


class CLAHEProcessor(ImageProcessor):
    """CLAHE自适应直方图均衡化处理器"""
    
    def __init__(self, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)):
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size
    
    def process(self, image: Image.Image, **kwargs) -> Image.Image:
        """应用CLAHE处理"""
        try:
            import cv2
            import numpy as np
            
            img_array = np.array(image)
            
            if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
                # 彩色图像：在LAB色彩空间处理L通道
                lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
                l, a, b = cv2.split(lab)
                
                clahe = cv2.createCLAHE(clipLimit=self.clip_limit, 
                                      tileGridSize=self.tile_grid_size)
                l = clahe.apply(l)
                
                lab = cv2.merge([l, a, b])
                result = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
                return Image.fromarray(result, mode=image.mode)
            else:
                # 灰度图像：直接处理
                if len(img_array.shape) == 3:
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img_array
                
                clahe = cv2.createCLAHE(clipLimit=self.clip_limit, 
                                      tileGridSize=self.tile_grid_size)
                enhanced = clahe.apply(gray)
                
                if image.mode == 'RGB':
                    result = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
                    return Image.fromarray(result, mode='RGB')
                else:
                    return Image.fromarray(enhanced, mode='L')
            
        except Exception:
            return image
    
    def get_name(self) -> str:
        return "CLAHE"


class SmartSharpeningProcessor(ImageProcessor):
    """智能锐化处理器"""
    
    def __init__(self, base_strength: float = 1.2):
        self.base_strength = base_strength
    
    def process(self, image: Image.Image, **kwargs) -> Image.Image:
        """应用智能锐化"""
        try:
            import cv2
            import numpy as np
            
            # 获取图像特征
            features = kwargs.get('features', ImageAnalyzer.analyze_features(image))
            edge_density = features.get('edge_density', 0.1)
            noise_level = features.get('noise_level', 0.1)
            
            # 根据特征调整锐化强度
            if edge_density > 0.15:
                strength = self.base_strength * 0.8  # 高边缘密度，降低锐化
            elif noise_level > 0.3:
                strength = self.base_strength * 0.6  # 高噪点，大幅降低锐化
            else:
                strength = self.base_strength
            
            # 应用Unsharp Mask锐化
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                # 彩色图像
                blurred = cv2.GaussianBlur(img_array, (0, 0), 1.0)
                sharpened = cv2.addWeighted(img_array, 1.0 + strength, blurred, -strength, 0)
            else:
                # 灰度图像
                blurred = cv2.GaussianBlur(img_array, (0, 0), 1.0)
                sharpened = cv2.addWeighted(img_array, 1.0 + strength, blurred, -strength, 0)
            
            sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
            return Image.fromarray(sharpened, mode=image.mode)
            
        except Exception:
            return image
    
    def get_name(self) -> str:
        return "SmartSharpening"


class NoiseReductionProcessor(ImageProcessor):
    """噪点抑制处理器"""
    
    def __init__(self, strength: int = 6):
        self.strength = strength
    
    def process(self, image: Image.Image, **kwargs) -> Image.Image:
        """应用噪点抑制"""
        try:
            import cv2
            import numpy as np
            
            img_array = np.array(image)
            
            if len(img_array.shape) == 3:
                # 彩色图像使用非局部均值去噪
                denoised = cv2.fastNlMeansDenoisingColored(img_array, None, 
                                                         self.strength, self.strength, 7, 21)
            else:
                # 灰度图像
                denoised = cv2.fastNlMeansDenoising(img_array, None, self.strength, 7, 21)
            
            return Image.fromarray(denoised, mode=image.mode)
            
        except Exception:
            return image
    
    def get_name(self) -> str:
        return "NoiseReduction"


class ColorEnhancementProcessor(ImageProcessor):
    """色彩增强处理器"""
    
    def __init__(self, saturation_factor: float = 1.1, contrast_factor: float = 1.05):
        self.saturation_factor = saturation_factor
        self.contrast_factor = contrast_factor
    
    def process(self, image: Image.Image, **kwargs) -> Image.Image:
        """应用色彩增强"""
        try:
            features = kwargs.get('features', ImageAnalyzer.analyze_features(image))
            color_richness = features.get('color_richness', 0.3)
            
            enhanced = image.copy()
            
            # 根据色彩丰富度调整饱和度
            if color_richness > 0.5:
                saturation = self.saturation_factor * 0.9  # 高色彩丰富度，轻微增强
            else:
                saturation = self.saturation_factor * 1.1  # 低色彩丰富度，适度增强
            
            # 应用饱和度增强
            if enhanced.mode in ['RGB', 'RGBA']:
                enhancer = ImageEnhance.Color(enhanced)
                enhanced = enhancer.enhance(min(saturation, 1.3))
            
            # 应用对比度增强
            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(self.contrast_factor)
            
            return enhanced
            
        except Exception:
            return image
    
    def get_name(self) -> str:
        return "ColorEnhancement"


class ImageProcessingPipeline:
    """图像处理流水线"""
    
    def __init__(self):
        self.processors = []
        self.analyzer = ImageAnalyzer()
    
    def add_processor(self, processor: ImageProcessor) -> 'ImageProcessingPipeline':
        """添加处理器"""
        self.processors.append(processor)
        return self
    
    def process(self, image: Image.Image, log_callback=None) -> Image.Image:
        """执行处理流水线"""
        try:
            # 分析图像特征
            features = self.analyzer.analyze_features(image)
            
            result = image.copy()
            
            for processor in self.processors:
                try:
                    result = processor.process(result, features=features)
                    if log_callback:
                        log_callback(f"        ✅ 应用 {processor.get_name()} 处理")
                except Exception as e:
                    if log_callback:
                        log_callback(f"        ⚠️ {processor.get_name()} 处理失败: {str(e)}")
                    continue
            
            return result
            
        except Exception as e:
            if log_callback:
                log_callback(f"        ❌ 处理流水线失败: {str(e)}")
            return image
    
    def clear(self) -> 'ImageProcessingPipeline':
        """清空处理器"""
        self.processors.clear()
        return self