#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF高清化转换器

使用Waifu2x对PDF中的图像进行超分辨率处理
"""

import os
import fitz  # PyMuPDF
import tempfile
import logging
from typing import Dict, Any, List
from PIL import Image
import io
import subprocess
import sys
import numpy as np

# 导入基类
from converters.converter_interface import ConverterInterface, ConverterMetadata

# 导入新的模块化组件
from converters.image_processing_toolkit import ImageAnalyzer, ImageProcessingPipeline
from converters.config_manager import get_config_manager, get_processing_config
from converters.enhancement_plugins import get_plugin_manager

logger = logging.getLogger('pdf_converter')

class PDFUpscaleConverter(ConverterInterface):
    """PDF高清化转换器
    
    使用Real-ESRGAN和Waifu2x对PDF中的图像进行超分辨率处理
    """
    
    def __init__(self):
        self._temp_files = []
        self._check_dependencies()
        self._setup_gpu_environment()
        
        # 初始化新的模块化组件
        self.config_manager = get_config_manager()
        self.config = get_processing_config()
        self.image_analyzer = ImageAnalyzer()
        self.plugin_manager = get_plugin_manager()
        
        # 注册内置插件
        self._register_builtin_plugins()
    
    def _register_builtin_plugins(self):
        """注册内置的图像处理插件"""
        from converters.enhancement_plugins import (
            CLAHEPreprocessingPlugin, SmartSharpeningPlugin,
            NoiseReductionPlugin, ColorEnhancementPlugin
        )
        
        # 注册预处理插件
        self.plugin_manager.register_plugin(CLAHEPreprocessingPlugin())
        self.plugin_manager.register_plugin(SmartSharpeningPlugin())
        
        # 注册后处理插件
        self.plugin_manager.register_plugin(NoiseReductionPlugin())
        self.plugin_manager.register_plugin(ColorEnhancementPlugin())
    
    @property
    def name(self) -> str:
        return "pdf_upscale"
    
    @property
    def description(self) -> str:
        return "使用AI算法对PDF中的图像进行高清化处理，支持动漫、照片和文档三种模式"
    
    @property
    def supported_input_formats(self) -> List[str]:
        return ["pdf"]
    
    @property
    def supported_output_formats(self) -> List[str]:
        return ["pdf"]
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def get_metadata(self) -> ConverterMetadata:
        """获取转换器元数据"""
        return ConverterMetadata(
            name=self.name,
            description=self.description,
            version=self.version,
            supported_input_formats=self.supported_input_formats,
            supported_output_formats=self.supported_output_formats,
            author="PDF Converter Team"
        )
    
    def validate_input(self, input_path: str) -> bool:
        """验证PDF文件是否有效"""
        try:
            if not os.path.exists(input_path):
                return False
            
            if not input_path.lower().endswith('.pdf'):
                return False
            
            # 尝试打开PDF文件
            doc = fitz.open(input_path)
            page_count = len(doc)
            doc.close()
            
            return page_count > 0
        except Exception as e:
            logger.error(f"PDF文件验证失败: {e}")
            return False
    
    def convert(self, input_path: str, output_path: str, **kwargs) -> dict:
        """执行PDF高清化转换
        
        Args:
            input_path: 输入PDF文件路径
            output_path: 输出PDF文件路径
            **kwargs: 转换参数，包含upscale_method
            
        Returns:
            dict: 转换结果，包含success字段和可能的error信息
        """
        try:
            upscale_method = kwargs.get('upscale_method', 'photo')
            progress_callback = kwargs.get('progress_callback')
            log_callback = kwargs.get('log_callback')
            enable_gpu = kwargs.get('enable_gpu', True)
            batch_size = kwargs.get('batch_size', 4)
            
            if log_callback:
                log_callback(f"开始PDF高清化处理: {os.path.basename(input_path)}")
                log_callback(f"高清化方式: {self._get_method_description(upscale_method)}")
            
            # 打开PDF文档
            doc = fitz.open(input_path)
            total_pages = len(doc)
            
            if log_callback:
                log_callback(f"PDF共有 {total_pages} 页")
            
            # 创建新的PDF文档
            new_doc = fitz.open()
            
            # GPU内存管理 - 增强双显卡诊断
            if log_callback:
                log_callback("🔧 开始GPU环境检测...")
            gpu_available = self._check_gpu_availability(log_callback) and enable_gpu
            if gpu_available and log_callback:
                try:
                    import torch
                    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                    log_callback(f"🎮 GPU信息: {torch.cuda.get_device_name(0)}, 显存: {gpu_memory:.1f}GB")
                except:
                    pass
            
            for page_num in range(total_pages):
                if progress_callback:
                    progress_callback(int((page_num / total_pages) * 100))
                
                if log_callback:
                    log_callback(f"处理第 {page_num + 1}/{total_pages} 页")
                
                # GPU内存清理（每10页清理一次）
                if gpu_available and page_num % 10 == 0 and page_num > 0:
                    try:
                        import torch
                        torch.cuda.empty_cache()
                        if log_callback:
                            log_callback(f"      🧹 清理GPU内存缓存")
                    except:
                        pass
                
                page = doc[page_num]
                
                # 获取页面中的图像
                image_list = page.get_images(full=True)
                
                # 创建新页面
                new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                
                # 先复制页面的非图像内容（文字、矢量图形等）
                new_page.show_pdf_page(new_page.rect, doc, page_num)
                
                if image_list:
                    if log_callback:
                        log_callback(f"  发现 {len(image_list)} 个图像")
                    
                    # 处理页面中的每个图像
                    for img_index, img in enumerate(image_list):
                        if log_callback:
                            log_callback(f"    处理图像 {img_index + 1}/{len(image_list)}")
                        
                        try:
                            # 提取图像数据
                            xref = img[0]
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            
                            # 获取图像在页面中的位置
                            img_rects = page.get_image_rects(xref)
                            if not img_rects:
                                continue
                            
                            # 高清化处理
                            upscaled_image_bytes = self._upscale_image(
                                image_bytes, upscale_method, log_callback, gpu_available
                            )
                            
                            if upscaled_image_bytes:
                                # 先删除原图像区域
                                for img_rect in img_rects:
                                    # 用白色矩形覆盖原图像位置
                                    new_page.draw_rect(img_rect, color=(1, 1, 1), fill=(1, 1, 1))
                                
                                # 插入高清化后的图像
                                for img_rect in img_rects:
                                    try:
                                        # 创建临时图像文件
                                        import tempfile
                                        temp_img_path = tempfile.mktemp(suffix=f'.{image_ext}')
                                        self._temp_files.append(temp_img_path)
                                        
                                        # 保存高清化图像到临时文件
                                        with open(temp_img_path, 'wb') as f:
                                            f.write(upscaled_image_bytes)
                                        
                                        # 智能调整图像尺寸以减少留白
                                        optimized_rect = self._optimize_image_layout(
                                            img_rect, temp_img_path, page, log_callback
                                        )
                                        
                                        # 使用优化的方法插入高清化图像
                                        self._insert_upscaled_image(
                                            new_page, optimized_rect, temp_img_path, log_callback
                                        )
                                        
                                        if log_callback:
                                            log_callback(f"      ✅ 图像 {img_index + 1} 高清化完成")
                                        
                                    except Exception as e:
                                        if log_callback:
                                            log_callback(f"      ❌ 图像 {img_index + 1} 插入失败: {str(e)}")
                                        logger.error(f"图像插入失败: {e}")
                            else:
                                if log_callback:
                                    log_callback(f"      ⚠️ 图像 {img_index + 1} 高清化失败，保持原图")
                        
                        except Exception as e:
                            if log_callback:
                                log_callback(f"      ❌ 图像 {img_index + 1} 处理失败: {str(e)}")
                            logger.error(f"图像处理失败: {e}")
                            continue
            
            # 保存新文档
            new_doc.save(output_path)
            new_doc.close()
            doc.close()
            
            # 清理临时文件
            self._cleanup_temp_files()
            
            if log_callback:
                log_callback(f"PDF高清化完成: {os.path.basename(output_path)}")
            
            if progress_callback:
                progress_callback(100)
            
            return {"success": True, "output_path": output_path}
            
        except Exception as e:
            logger.error(f"PDF高清化失败: {e}")
            if log_callback:
                log_callback(f"❌ 高清化失败: {str(e)}")
            # 确保异常时也清理临时文件
            self._cleanup_temp_files()
            return {"success": False, "error": str(e)}
    
    def _upscale_image(self, image_bytes: bytes, method: str, log_callback=None, gpu_available=None) -> bytes:
        """对图像进行高清化处理（修复版本）"""
        try:
            # 检查GPU可用性和内存
            if gpu_available is None:
                gpu_available = self._check_gpu_availability(log_callback)
            
            # GPU内存检查和管理
            if gpu_available:
                try:
                    import torch
                    torch.cuda.empty_cache()  # 清理GPU缓存
                    memory_free = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)
                    memory_free_gb = memory_free / 1024**3
                    
                    if memory_free_gb < 2.0:  # 少于2GB可用内存时降级到CPU
                        if log_callback:
                            log_callback(f"      ⚠️ GPU内存不足 ({memory_free_gb:.1f}GB)，切换到CPU模式")
                        gpu_available = False
                except:
                    gpu_available = False
            
            # 将字节数据转换为PIL图像
            image = Image.open(io.BytesIO(image_bytes))
            
            # 图像格式检查和修复
            if image.mode not in ['RGB', 'L']:
                if image.mode == 'RGBA':
                    # 处理透明通道 - 创建白色背景
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1])
                    image = background
                    if log_callback:
                        log_callback(f"      🔧 转换RGBA到RGB格式")
                elif image.mode == 'P':
                    # 处理调色板模式
                    image = image.convert('RGB')
                    if log_callback:
                        log_callback(f"      🔧 转换调色板到RGB格式")
                else:
                    image = image.convert('RGB')
                    if log_callback:
                        log_callback(f"      🔧 转换{image.mode}到RGB格式")
            
            # 图像尺寸检查
            width, height = image.size
            if width * height > 4096 * 4096:  # 超大图像分块处理
                if log_callback:
                    log_callback(f"      📏 图像过大 ({width}x{height})，启用分块处理")
                return self._process_large_image(image, method, log_callback, gpu_available)
            
            original_size = image.size
            if log_callback:
                log_callback(f"      原始尺寸: {original_size[0]}x{original_size[1]}")
            
            # 根据方法选择处理方式（带重试机制，优先使用Waifu2x）
            upscaled_image = None
            max_retries = 3  # 增加重试次数以支持算法回退
            
            # 定义算法优先级：Waifu2x > 简单放大
            algorithm_sequence = ["waifu2x", "simple"]  # 统一使用Waifu2x
            
            for attempt in range(min(max_retries, len(algorithm_sequence))):
                current_algorithm = algorithm_sequence[attempt]
                try:
                    if log_callback:
                        algo_name = {
                            "waifu2x": "Waifu2x (AI高清化)",
                            "simple": "传统算法"
                        }.get(current_algorithm, current_algorithm)
                        log_callback(f"      🔄 尝试算法 {attempt+1}/{len(algorithm_sequence)}: {algo_name}")
                    
                    if current_algorithm == "waifu2x":
                        upscaled_image = self._waifu2x_upscale(image, log_callback, gpu_available, method)
                    else:  # simple
                        upscaled_image = self._simple_upscale(image, log_callback)
                    
                    # 检查输出图像有效性
                    if upscaled_image and self._validate_output_image(upscaled_image):
                        if log_callback:
                            log_callback(f"      ✅ {algo_name} 处理成功")
                        break
                    else:
                        if log_callback:
                            log_callback(f"      ❌ {algo_name} 输出异常，尝试下一个算法...")
                        upscaled_image = None
                        
                except Exception as e:
                    if log_callback:
                        error_msg = str(e)
                        if "404" in error_msg or "Not Found" in error_msg:
                            log_callback(f"      ❌ {algo_name} 模型下载失败，尝试下一个算法")
                        elif "CUDA" in error_msg or "GPU" in error_msg:
                            log_callback(f"      ❌ {algo_name} GPU错误，尝试下一个算法")
                        else:
                            log_callback(f"      ❌ {algo_name} 处理失败: {error_msg[:50]}...")
                    
                    # 如果是GPU相关错误且还有重试机会，尝试CPU模式
                    if "CUDA" in str(e) and gpu_available and attempt < len(algorithm_sequence) - 1:
                        gpu_available = False
                        if log_callback:
                            log_callback(f"      🔄 检测到GPU错误，后续算法将使用CPU模式")
            
            # 如果所有算法都失败，使用简单放大作为最后手段
            if not upscaled_image:
                if log_callback:
                    log_callback(f"      🚨 所有AI算法都失败，使用传统放大算法")
                    log_callback(f"      💡 建议检查网络连接和AI库安装状态")
                upscaled_image = self._simple_upscale(image, log_callback)
            
            if upscaled_image:
                new_size = upscaled_image.size
                if log_callback:
                    log_callback(f"      高清化后: {new_size[0]}x{new_size[1]}")
                
                # 转换回字节数据，优化格式处理
                output_buffer = io.BytesIO()
                
                # 智能格式选择
                try:
                    if hasattr(image, 'format') and image.format == 'JPEG':
                        # 原图是JPEG，保持JPEG格式
                        if upscaled_image.mode != 'RGB':
                            upscaled_image = upscaled_image.convert('RGB')
                        upscaled_image.save(output_buffer, format='JPEG', quality=95, optimize=True)
                    else:
                        # 其他格式使用PNG
                        upscaled_image.save(output_buffer, format='PNG', optimize=True)
                except Exception as save_error:
                    # 备选方案：强制转换为RGB并保存为JPEG
                    if log_callback:
                        log_callback(f"      🔧 格式转换失败，使用JPEG格式")
                    if upscaled_image.mode != 'RGB':
                        upscaled_image = upscaled_image.convert('RGB')
                    upscaled_image.save(output_buffer, format='JPEG', quality=95)
                
                return output_buffer.getvalue()
            
            return image_bytes  # 如果处理失败，返回原图像
            
        except Exception as e:
            logger.error(f"图像高清化失败: {e}")
            if log_callback:
                log_callback(f"      ❌ 图像处理失败，使用原图像: {str(e)}")
            return image_bytes
    
    def _waifu2x_upscale(self, image: Image.Image, log_callback=None, gpu_available=None, method="anime") -> Image.Image:
        """使用Waifu2x进行图像高清化，支持多种优化参数"""
        try:
            if log_callback:
                log_callback(f"        使用Waifu2x算法处理...")
            
            # 导入waifu2x-ncnn-py
            from waifu2x_ncnn_py import Waifu2x
            
            # 检测GPU可用性
            if gpu_available is None:
                gpu_available = self._check_gpu_availability(log_callback)
            gpuid = 0 if gpu_available else -1
            
            if log_callback and gpu_available:
                log_callback(f"        🚀 使用GPU加速处理")
            elif log_callback:
                log_callback(f"        💻 使用CPU处理")
            
            # 图像预处理
            processed_image = self._preprocess_image(image, method, log_callback)
            
            # 根据方法和图像特性选择最优参数
            config = self._get_optimal_waifu2x_config(processed_image, method, gpu_available, log_callback)
            
            # 创建Waifu2x实例
            waifu2x = Waifu2x(
                gpuid=gpuid,
                tta_mode=config['tta_mode'],
                num_threads=config['num_threads'],
                noise=config['noise'],
                scale=config['scale'],
                tilesize=config['tilesize'],
                model=config['model']
            )
            
            if log_callback:
                log_callback(f"        📊 配置: 模型={config['model']}, 降噪={config['noise']}, 瓦片={config['tilesize']}")
            
            # 使用Waifu2x处理图像
            upscaled_image = waifu2x.process_pil(processed_image)
            
            # 后处理和质量验证
            final_image = self._postprocess_image(upscaled_image, processed_image, log_callback)
            
            # 质量评估
            quality_score = self._evaluate_upscale_quality(processed_image, final_image, log_callback)
            if log_callback:
                log_callback(f"        ✨ 质量评分: {quality_score:.2f}/10")
            
            return final_image
            
        except ImportError as e:
            if log_callback:
                log_callback(f"        Waifu2x库未安装: {str(e)}。请运行 'pip install waifu2x-ncnn-py' 安装")
            return self._simple_upscale(image, log_callback)
        except Exception as e:
            logger.error(f"Waifu2x处理失败: {e}")
            if log_callback:
                log_callback(f"        ⚠️ Waifu2x处理失败: {str(e)}")
            return self._simple_upscale(image, log_callback)
    
    def _preprocess_image(self, image: Image.Image, method: str, log_callback=None) -> Image.Image:
        """图像预处理，使用插件架构进行模块化处理"""
        try:
            processed_image = image.copy()
            
            # 转换为RGB模式（如果需要）
            if processed_image.mode not in ['RGB', 'RGBA']:
                if log_callback:
                    log_callback(f"        🔄 转换图像模式: {processed_image.mode} -> RGB")
                processed_image = processed_image.convert('RGB')
            
            # 使用图像分析器分析图像特征
            features = self.image_analyzer.analyze_features(processed_image)
            if log_callback:
                log_callback(f"        🔍 图像分析完成: 边缘密度={features['edge_density']:.3f}, 噪声水平={features['noise_level']:.3f}")
            
            # 创建预处理管道
            pipeline = ImageProcessingPipeline()
            
            # 根据方法和图像特征选择预处理插件
            if method == "photo":
                # 照片类型预处理管道
                if features['contrast'] < 0.5:  # 低对比度图像
                    pipeline.add_processor(self.plugin_manager.get_plugin('clahe_preprocessing'))
                if features['edge_density'] < 0.3:  # 需要锐化
                    pipeline.add_processor(self.plugin_manager.get_plugin('smart_sharpening'))
                if log_callback:
                    log_callback(f"        📸 应用照片优化预处理管道")
            elif method == "document":
                # 文档类型预处理管道
                pipeline.add_processor(self.plugin_manager.get_plugin('clahe_preprocessing'))
                if features['noise_level'] > 0.1:  # 高噪声文档
                    pipeline.add_processor(self.plugin_manager.get_plugin('noise_reduction'))
                if log_callback:
                    log_callback(f"        📄 应用文档优化预处理管道")
            else:
                # 默认预处理
                if features['contrast'] < 0.4:
                    pipeline.add_processor(self.plugin_manager.get_plugin('clahe_preprocessing'))
            
            # 执行预处理管道
            processed_image = pipeline.process(processed_image)
            
            return processed_image
            
        except Exception as e:
            if log_callback:
                log_callback(f"        ⚠️ 预处理失败，使用原图像: {str(e)}")
            return image
    
    def _enhance_photo(self, image: Image.Image) -> Image.Image:
        """照片类型图像增强 - 扩展版"""
        try:
            from PIL import ImageEnhance, ImageFilter
            import cv2
            import numpy as np
            
            # 转换为numpy数组进行高级处理
            img_array = np.array(image)
            
            # 1. CLAHE自适应直方图均衡化（仅对亮度通道）
            if len(img_array.shape) == 3:
                # 转换到LAB色彩空间
                lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                lab[:,:,0] = clahe.apply(lab[:,:,0])  # 只对L通道应用CLAHE
                img_array = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
                enhanced = Image.fromarray(img_array)
            else:
                # 灰度图像直接应用CLAHE
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                img_array = clahe.apply(img_array)
                enhanced = Image.fromarray(img_array)
            
            # 2. 智能锐化（基于图像内容自适应）
            enhanced = self._apply_smart_sharpening(enhanced, strength=1.1)
            
            # 3. 轻微对比度增强
            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(1.05)
            
            # 4. 色彩饱和度微调
            enhancer = ImageEnhance.Color(enhanced)
            enhanced = enhancer.enhance(1.02)
            
            return enhanced
        except Exception as e:
            # 如果高级处理失败，回退到基础增强
            try:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Sharpness(image)
                enhanced = enhancer.enhance(1.1)
                enhancer = ImageEnhance.Contrast(enhanced)
                enhanced = enhancer.enhance(1.05)
                return enhanced
            except:
                return image
    
    def _enhance_document(self, image: Image.Image) -> Image.Image:
        """文档类型图像增强 - 扩展版"""
        try:
            from PIL import ImageEnhance, ImageFilter, ImageOps
            import cv2
            import numpy as np
            
            # 转换为numpy数组
            img_array = np.array(image)
            
            # 1. 文档专用CLAHE（更强的对比度增强）
            if len(img_array.shape) == 3:
                # 转换为灰度进行文档处理
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16,16))
                enhanced_gray = clahe.apply(gray)
                # 转回RGB
                enhanced = Image.fromarray(cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2RGB))
            else:
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(16,16))
                enhanced_gray = clahe.apply(img_array)
                enhanced = Image.fromarray(enhanced_gray)
            
            # 2. 文档去噪（双边滤波）
            img_array = np.array(enhanced)
            if len(img_array.shape) == 3:
                denoised = cv2.bilateralFilter(img_array, 9, 75, 75)
                enhanced = Image.fromarray(denoised)
            
            # 3. 智能锐化（文档专用强度）
            enhanced = self._apply_smart_sharpening(enhanced, strength=1.4)
            
            # 4. 强化对比度
            enhancer = ImageEnhance.Contrast(enhanced)
            enhanced = enhancer.enhance(1.3)
            
            # 5. 文档专用边缘增强
            enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1, percent=120, threshold=3))
            
            return enhanced
        except Exception as e:
            # 回退到基础增强
            try:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(image)
                enhanced = enhancer.enhance(1.2)
                enhancer = ImageEnhance.Sharpness(enhanced)
                enhanced = enhancer.enhance(1.3)
                return enhanced
            except:
                return image
    
    def _apply_smart_sharpening(self, image: Image.Image, strength: float = 1.2) -> Image.Image:
        """智能锐化算法 - 基于图像内容自适应调整"""
        try:
            from PIL import ImageFilter, ImageEnhance
            import cv2
            import numpy as np
            
            # 转换为numpy数组分析图像特征
            img_array = np.array(image)
            
            # 计算图像的边缘密度和噪点水平
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # 1. 边缘检测评估
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
            
            # 2. 噪点水平评估（使用拉普拉斯算子）
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 3. 根据图像特征自适应调整锐化参数
            if edge_density > 0.1:  # 高边缘密度（如文档、线条图）
                # 使用UnsharpMask进行精确锐化
                radius = 1.0
                percent = int(strength * 100)
                threshold = 2
            elif laplacian_var < 100:  # 低对比度图像
                # 温和锐化避免噪点放大
                radius = 0.5
                percent = int(strength * 80)
                threshold = 5
            else:  # 普通图像
                radius = 1.5
                percent = int(strength * 90)
                threshold = 3
            
            # 应用UnsharpMask锐化
            sharpened = image.filter(ImageFilter.UnsharpMask(
                radius=radius, 
                percent=percent, 
                threshold=threshold
            ))
            
            # 4. 多尺度锐化（针对不同频率的细节）
            if strength > 1.3:  # 强锐化模式
                # 添加高频细节增强
                enhancer = ImageEnhance.Sharpness(sharpened)
                sharpened = enhancer.enhance(1.1)
            
            return sharpened
            
        except Exception as e:
            # 回退到基础锐化
            try:
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Sharpness(image)
                return enhancer.enhance(strength)
            except:
                return image
    
    def _get_optimal_waifu2x_config(self, image: Image.Image, method: str, gpu_available: bool, log_callback=None) -> dict:
        """根据图像特性和方法选择最优Waifu2x配置 - 使用配置管理器"""
        width, height = image.size
        pixel_count = width * height
        
        # 使用图像分析器分析图像特征
        image_features = self.image_analyzer.analyze_features(image)
        
        # 从配置管理器获取基础配置
        waifu2x_config = self.config.waifu2x
        
        # 基础配置
        config = {
            'tta_mode': waifu2x_config.tta_mode,
            'num_threads': waifu2x_config.cpu_threads if not gpu_available else waifu2x_config.gpu_threads,
            'scale': waifu2x_config.scale
        }
        
        # 智能瓦片大小选择（基于GPU内存和图像复杂度）
        complexity_factor = image_features.get('complexity', 0.5)
        
        if gpu_available:
            # GPU处理 - 根据图像大小和复杂度动态调整
            if pixel_count > 4000000:  # 超大图像
                config['tilesize'] = max(waifu2x_config.min_tilesize, 
                                       int(waifu2x_config.gpu_tilesize_large * (1 - complexity_factor * 0.3)))
            elif pixel_count > 2000000:  # 大图像
                config['tilesize'] = max(waifu2x_config.min_tilesize, 
                                       int(waifu2x_config.gpu_tilesize_medium * (1 - complexity_factor * 0.2)))
            elif pixel_count > 1000000:  # 中等图像
                config['tilesize'] = max(waifu2x_config.min_tilesize, 
                                       int(waifu2x_config.gpu_tilesize_small * (1 - complexity_factor * 0.1)))
            else:  # 小图像
                config['tilesize'] = waifu2x_config.gpu_tilesize_small
        else:
            # CPU处理 - 使用配置的CPU瓦片大小
            if pixel_count > 2000000:
                config['tilesize'] = waifu2x_config.cpu_tilesize_large
            elif pixel_count > 1000000:
                config['tilesize'] = waifu2x_config.cpu_tilesize_medium
            else:
                config['tilesize'] = waifu2x_config.cpu_tilesize_small
        
        # 智能模型和参数选择
        noise_level = image_features.get('noise_level', 1)
        edge_density = image_features.get('edge_density', 0.05)
        
        if method == "anime":
            config['model'] = waifu2x_config.anime_model
            # 动漫图像根据边缘密度调整降噪
            if edge_density > 0.15:  # 高细节动漫
                config['noise'] = max(1, min(3, int(noise_level * 3) + 1))
            else:
                config['noise'] = max(2, min(3, int(noise_level * 3) + 2))
        elif method == "photo":
            config['model'] = waifu2x_config.photo_model
            # 照片根据噪点水平智能调整
            config['noise'] = max(0, min(3, int(noise_level * 3)))
        elif method == "document":
            config['model'] = waifu2x_config.document_model
            # 文档通常需要强降噪但保持文字清晰
            config['noise'] = 3 if noise_level > 0.33 else 2
        else:
            config['model'] = waifu2x_config.anime_model  # 默认使用动漫模型
            config['noise'] = max(1, min(3, noise_level))
        
        # 高质量模式条件优化
        enable_tta = False
        if gpu_available:
            # 更智能的TTA启用条件
            if pixel_count < 800000:  # 中小图像
                if image_features.get('is_important', False):  # 重要图像
                    enable_tta = True
                elif edge_density > 0.1 and pixel_count < 400000:  # 高细节小图
                    enable_tta = True
        
        config['tta_mode'] = enable_tta
        
        # 动态缩放比例选择
        if pixel_count < 100000:  # 极小图像可以使用更高缩放
            config['scale'] = 4 if gpu_available else 2
        elif pixel_count > 8000000:  # 极大图像使用保守缩放
            config['scale'] = 2
        
        # 日志输出优化信息
        if log_callback:
            if enable_tta:
                log_callback(f"        🎯 启用高质量模式（TTA）")
            log_callback(f"        ⚙️ 瓦片大小: {config['tilesize']}, 降噪: {config['noise']}, 缩放: {config['scale']}x")
            if image_features.get('complexity', 0) > 0.7:
                log_callback(f"        🔍 检测到高复杂度图像，优化处理参数")
        
        return config
    
    # 注意：原有的 _analyze_image_features 方法已被 ImageAnalyzer 类替代
        # 新的图像分析功能通过 self.image_analyzer.analyze_features() 调用
    
    def _postprocess_image(self, upscaled_image: Image.Image, original_image: Image.Image, log_callback=None) -> Image.Image:
        """后处理优化 - 使用插件架构进行模块化处理"""
        try:
            # 分析原图和放大图特征
            original_features = self.image_analyzer.analyze_features(original_image)
            upscaled_features = self.image_analyzer.analyze_features(upscaled_image)
            
            enhanced = upscaled_image
            
            # 1. 色彩模式处理
            if original_image.mode == 'RGBA' and enhanced.mode == 'RGB':
                enhanced = enhanced.convert('RGBA')
            elif original_image.mode == 'L' and enhanced.mode == 'RGB':
                # 如果原图是灰度，可选择保持灰度或转换为彩色
                pass  # 保持RGB以获得更好的显示效果
            
            # 创建后处理管道
            pipeline = ImageProcessingPipeline()
            
            # 2. 根据配置和图像特征选择后处理插件
            config = self.config.postprocessing
            
            # 智能色彩校正
            if (config.color_enhancement.enabled and 
                original_features.get('color_richness', 0) > config.color_enhancement.min_color_richness):
                pipeline.add_processor(self.plugin_manager.get_plugin('color_enhancement'))
                if log_callback:
                    log_callback(f"        🎨 添加智能色彩增强")
            
            # 噪点抑制（检测噪点增加）
            noise_increased = (upscaled_features.get('noise_level', 0) > 
                             original_features.get('noise_level', 0) * 1.2)
            if config.noise_reduction.enabled and noise_increased:
                pipeline.add_processor(self.plugin_manager.get_plugin('noise_reduction'))
                if log_callback:
                    log_callback(f"        🔇 添加噪点抑制")
            
            # 执行后处理管道
            if pipeline.processors:
                enhanced = pipeline.process(enhanced)
                if log_callback:
                    log_callback(f"        ✅ 后处理管道执行完成，共{len(pipeline.processors)}个步骤")
            
            # 最终质量验证
            quality_score = self.image_analyzer.calculate_quality_score(enhanced)
            if log_callback:
                log_callback(f"        📊 最终质量评分: {quality_score:.3f}")
            
            return enhanced
            
        except Exception as e:
            if log_callback:
                log_callback(f"        ⚠️ 高级后处理失败，使用基础处理: {str(e)}")
            # 回退到基础后处理
            try:
                if original_image.mode == 'RGBA' and upscaled_image.mode == 'RGB':
                    return upscaled_image.convert('RGBA')
                return upscaled_image
            except:
                return upscaled_image
    
    def _apply_color_enhancement(self, image: Image.Image, features: dict) -> Image.Image:
        """智能色彩增强"""
        try:
            from PIL import ImageEnhance
            import cv2
            import numpy as np
            
            enhanced = image.copy()
            color_richness = features.get('color_richness', 0)
            
            # 1. 自适应饱和度增强
            if color_richness > 0.5:
                # 高色彩丰富度：轻微增强
                saturation_factor = 1.05 + (color_richness - 0.5) * 0.1
            else:
                # 低色彩丰富度：适度增强
                saturation_factor = 1.1 + (0.5 - color_richness) * 0.2
            
            enhancer = ImageEnhance.Color(enhanced)
            enhanced = enhancer.enhance(min(saturation_factor, 1.3))
            
            # 2. 智能白平衡校正
            if enhanced.mode in ['RGB', 'RGBA']:
                enhanced = self._apply_white_balance(enhanced)
            
            # 3. 色调映射优化
            if color_richness > 0.4:
                enhanced = self._apply_tone_mapping(enhanced)
            
            return enhanced
            
        except Exception:
            return image
    
    def _apply_white_balance(self, image: Image.Image) -> Image.Image:
        """自动白平衡校正"""
        try:
            import cv2
            import numpy as np
            
            # 转换为numpy数组
            img_array = np.array(image)
            if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
                # 计算各通道平均值
                avg_b = np.mean(img_array[:, :, 2])  # PIL中是RGB，所以B是索引2
                avg_g = np.mean(img_array[:, :, 1])
                avg_r = np.mean(img_array[:, :, 0])
                
                # 计算灰度世界假设下的校正因子
                avg_gray = (avg_r + avg_g + avg_b) / 3
                
                if avg_gray > 0:
                    scale_r = avg_gray / avg_r if avg_r > 0 else 1.0
                    scale_g = avg_gray / avg_g if avg_g > 0 else 1.0
                    scale_b = avg_gray / avg_b if avg_b > 0 else 1.0
                    
                    # 限制校正幅度
                    scale_r = np.clip(scale_r, 0.8, 1.2)
                    scale_g = np.clip(scale_g, 0.8, 1.2)
                    scale_b = np.clip(scale_b, 0.8, 1.2)
                    
                    # 应用校正
                    img_array[:, :, 0] = np.clip(img_array[:, :, 0] * scale_r, 0, 255)
                    img_array[:, :, 1] = np.clip(img_array[:, :, 1] * scale_g, 0, 255)
                    img_array[:, :, 2] = np.clip(img_array[:, :, 2] * scale_b, 0, 255)
                    
                    return Image.fromarray(img_array.astype(np.uint8), mode=image.mode)
            
            return image
            
        except Exception:
            return image
    
    def _apply_tone_mapping(self, image: Image.Image) -> Image.Image:
        """色调映射优化"""
        try:
            import cv2
            import numpy as np
            
            img_array = np.array(image)
            if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
                # 转换为LAB色彩空间进行处理
                lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
                l, a, b = cv2.split(lab)
                
                # 对L通道应用自适应直方图均衡化
                clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
                l = clahe.apply(l)
                
                # 重新合并并转换回RGB
                lab = cv2.merge([l, a, b])
                rgb = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
                
                return Image.fromarray(rgb, mode=image.mode)
            
            return image
            
        except Exception:
            return image
    
    def _apply_detail_enhancement(self, image: Image.Image, features: dict) -> Image.Image:
        """细节增强后处理"""
        try:
            from PIL import ImageFilter, ImageEnhance
            import cv2
            import numpy as np
            
            enhanced = image.copy()
            edge_density = features.get('edge_density', 0)
            
            # 1. 自适应锐化
            if edge_density > 0.15:
                # 高边缘密度：轻微锐化
                sharpness_factor = 1.1
            elif edge_density > 0.08:
                # 中等边缘密度：适度锐化
                sharpness_factor = 1.2
            else:
                # 低边缘密度：较强锐化
                sharpness_factor = 1.3
            
            enhancer = ImageEnhance.Sharpness(enhanced)
            enhanced = enhancer.enhance(sharpness_factor)
            
            # 2. 边缘保护的细节增强
            if edge_density > 0.1:
                enhanced = self._apply_edge_preserving_enhancement(enhanced)
            
            # 3. 高频细节增强
            enhanced = self._apply_high_frequency_enhancement(enhanced, edge_density)
            
            return enhanced
            
        except Exception:
            return image
    
    def _apply_edge_preserving_enhancement(self, image: Image.Image) -> Image.Image:
        """边缘保护的细节增强"""
        try:
            import cv2
            import numpy as np
            
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                # 使用双边滤波保护边缘的同时增强细节
                enhanced = cv2.bilateralFilter(img_array, 9, 75, 75)
                
                # 计算细节层
                detail = img_array.astype(np.float32) - enhanced.astype(np.float32)
                
                # 增强细节层
                enhanced_detail = detail * 1.2
                
                # 合并
                result = enhanced.astype(np.float32) + enhanced_detail
                result = np.clip(result, 0, 255).astype(np.uint8)
                
                return Image.fromarray(result, mode=image.mode)
            
            return image
            
        except Exception:
            return image
    
    def _apply_high_frequency_enhancement(self, image: Image.Image, edge_density: float) -> Image.Image:
        """高频细节增强"""
        try:
            import cv2
            import numpy as np
            
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                # 转换为灰度进行高频分析
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                
                # 高斯模糊获取低频
                low_freq = cv2.GaussianBlur(gray, (5, 5), 1.0)
                
                # 计算高频
                high_freq = gray.astype(np.float32) - low_freq.astype(np.float32)
                
                # 根据边缘密度调整增强强度
                enhancement_factor = 0.3 if edge_density > 0.15 else 0.5
                
                # 增强高频
                enhanced_high_freq = high_freq * enhancement_factor
                
                # 应用到原图的每个通道
                result = img_array.copy().astype(np.float32)
                for i in range(3):
                    result[:, :, i] += enhanced_high_freq
                
                result = np.clip(result, 0, 255).astype(np.uint8)
                return Image.fromarray(result, mode=image.mode)
            
            return image
            
        except Exception:
            return image
    
    def _detect_noise_increase(self, original: Image.Image, upscaled: Image.Image) -> bool:
        """检测放大过程中是否产生了噪点增加"""
        try:
            import cv2
            import numpy as np
            
            # 将图像调整到相同尺寸进行比较
            original_resized = original.resize(upscaled.size, Image.Resampling.LANCZOS)
            
            # 转换为灰度
            orig_gray = np.array(original_resized.convert('L'))
            upsc_gray = np.array(upscaled.convert('L'))
            
            # 计算噪点水平（使用拉普拉斯方差）
            orig_noise = cv2.Laplacian(orig_gray, cv2.CV_64F).var()
            upsc_noise = cv2.Laplacian(upsc_gray, cv2.CV_64F).var()
            
            # 如果放大后噪点显著增加，返回True
            noise_increase_ratio = upsc_noise / (orig_noise + 1e-6)
            return noise_increase_ratio > 1.3
            
        except Exception:
            return False
    
    def _apply_noise_reduction(self, image: Image.Image, features: dict) -> Image.Image:
        """智能噪点抑制"""
        try:
            import cv2
            import numpy as np
            
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                # 使用非局部均值去噪
                denoised = cv2.fastNlMeansDenoisingColored(img_array, None, 6, 6, 7, 21)
                
                # 保持边缘锐度
                edge_density = features.get('edge_density', 0)
                if edge_density > 0.1:
                    # 高边缘密度时，混合原图以保持细节
                    alpha = 0.7  # 去噪图像权重
                    result = (alpha * denoised + (1 - alpha) * img_array).astype(np.uint8)
                else:
                    result = denoised
                
                return Image.fromarray(result, mode=image.mode)
            
            return image
            
        except Exception:
            return image
    
    def _apply_tone_adjustment(self, image: Image.Image, features: dict) -> Image.Image:
        """色调和亮度微调"""
        try:
            from PIL import ImageEnhance
            import cv2
            import numpy as np
            
            enhanced = image.copy()
            
            # 1. 自适应对比度调整
            img_array = np.array(enhanced.convert('L'))
            mean_brightness = np.mean(img_array)
            
            if mean_brightness < 100:  # 偏暗图像
                # 轻微提升亮度和对比度
                brightness_enhancer = ImageEnhance.Brightness(enhanced)
                enhanced = brightness_enhancer.enhance(1.05)
                
                contrast_enhancer = ImageEnhance.Contrast(enhanced)
                enhanced = contrast_enhancer.enhance(1.1)
                
            elif mean_brightness > 180:  # 偏亮图像
                # 轻微降低亮度，增加对比度
                brightness_enhancer = ImageEnhance.Brightness(enhanced)
                enhanced = brightness_enhancer.enhance(0.98)
                
                contrast_enhancer = ImageEnhance.Contrast(enhanced)
                enhanced = contrast_enhancer.enhance(1.05)
            
            else:  # 正常亮度
                # 轻微增强对比度
                contrast_enhancer = ImageEnhance.Contrast(enhanced)
                enhanced = contrast_enhancer.enhance(1.03)
            
            # 2. 伽马校正（可选）
            if features.get('complexity', 0) > 0.5:
                enhanced = self._apply_gamma_correction(enhanced, mean_brightness)
            
            return enhanced
            
        except Exception:
            return image
    
    def _apply_gamma_correction(self, image: Image.Image, mean_brightness: float) -> Image.Image:
        """自适应伽马校正"""
        try:
            import numpy as np
            
            # 根据平均亮度确定伽马值
            if mean_brightness < 100:
                gamma = 0.9  # 提亮暗部
            elif mean_brightness > 180:
                gamma = 1.1  # 压暗亮部
            else:
                gamma = 1.0  # 无需调整
            
            if gamma != 1.0:
                img_array = np.array(image).astype(np.float32) / 255.0
                corrected = np.power(img_array, gamma)
                corrected = (corrected * 255).astype(np.uint8)
                return Image.fromarray(corrected, mode=image.mode)
            
            return image
            
        except Exception:
            return image
    
    def _final_quality_check(self, enhanced: Image.Image, original: Image.Image, log_callback=None) -> Image.Image:
        """最终质量验证和修正"""
        try:
            # 1. 尺寸验证
            if enhanced.size != original.size and hasattr(self, 'target_scale'):
                expected_size = (int(original.size[0] * self.target_scale), 
                               int(original.size[1] * self.target_scale))
                if enhanced.size != expected_size:
                    if log_callback:
                        log_callback(f"        📏 修正输出尺寸: {enhanced.size} -> {expected_size}")
                    enhanced = enhanced.resize(expected_size, Image.Resampling.LANCZOS)
            
            # 2. 色彩模式验证
            if enhanced.mode != original.mode and original.mode in ['RGB', 'RGBA', 'L']:
                if log_callback:
                    log_callback(f"        🎨 修正色彩模式: {enhanced.mode} -> {original.mode}")
                enhanced = enhanced.convert(original.mode)
            
            # 3. 质量评估
            quality_score = self._evaluate_quality(enhanced)
            if log_callback:
                log_callback(f"        📊 最终质量评分: {quality_score:.3f}")
            
            return enhanced
            
        except Exception as e:
            if log_callback:
                log_callback(f"        ⚠️ 质量检查失败: {str(e)}")
            return enhanced
    
    def _evaluate_quality(self, image: Image.Image) -> float:
        """评估单张图像质量"""
        try:
            import numpy as np
            import cv2
            
            img_array = np.array(image)
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            scores = []
            
            # 1. 边缘清晰度评分 (0-10)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            edge_score = min(10.0, edge_density * 50)  # 归一化到0-10
            scores.append(edge_score)
            
            # 2. 对比度评分 (0-10)
            contrast = gray.std()
            contrast_score = min(10.0, contrast / 25.5)  # 归一化到0-10
            scores.append(contrast_score)
            
            # 3. 细节丰富度评分 (0-10)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            detail_score = min(10.0, laplacian_var / 500)  # 归一化到0-10
            scores.append(detail_score)
            
            # 4. 噪点控制评分 (0-10，噪点越少分数越高)
            # 使用高频噪点检测
            kernel = np.array([[-1,-1,-1],[-1,8,-1],[-1,-1,-1]])
            noise_response = cv2.filter2D(gray, -1, kernel)
            noise_level = np.std(noise_response)
            noise_score = max(0.0, 10.0 - noise_level / 10)  # 噪点越少分数越高
            scores.append(noise_score)
            
            # 综合评分
            final_score = np.mean(scores)
            return min(10.0, max(0.0, final_score))
            
        except Exception:
            return 5.0  # 默认中等评分
    
    def _evaluate_upscale_quality(self, original: Image.Image, upscaled: Image.Image, log_callback=None) -> float:
        """评估高清化质量"""
        try:
            import numpy as np
            
            # 将原图放大到相同尺寸进行比较
            original_resized = original.resize(upscaled.size, Image.LANCZOS)
            
            # 转换为numpy数组
            orig_array = np.array(original_resized)
            upsc_array = np.array(upscaled)
            
            # 计算多个质量指标
            scores = []
            
            # 1. 边缘清晰度评分
            edge_score = self._calculate_edge_sharpness(upsc_array, orig_array)
            scores.append(edge_score)
            
            # 2. 细节保持评分
            detail_score = self._calculate_detail_preservation(upsc_array, orig_array)
            scores.append(detail_score)
            
            # 3. 噪点控制评分
            noise_score = self._calculate_noise_reduction(upsc_array, orig_array)
            scores.append(noise_score)
            
            # 综合评分
            final_score = np.mean(scores)
            
            return min(10.0, max(0.0, final_score))
            
        except Exception as e:
            if log_callback:
                log_callback(f"        ⚠️ 质量评估失败: {str(e)}")
            return 5.0  # 默认中等评分
    
    def _calculate_edge_sharpness(self, upscaled: np.ndarray, original: np.ndarray) -> float:
        """计算边缘清晰度评分"""
        try:
            from scipy import ndimage
            
            # 计算梯度
            if len(upscaled.shape) == 3:
                upscaled_gray = np.mean(upscaled, axis=2)
                original_gray = np.mean(original, axis=2)
            else:
                upscaled_gray = upscaled
                original_gray = original
            
            # Sobel边缘检测
            upscaled_edges = ndimage.sobel(upscaled_gray)
            original_edges = ndimage.sobel(original_gray)
            
            # 计算边缘强度
            upscaled_edge_strength = np.mean(np.abs(upscaled_edges))
            original_edge_strength = np.mean(np.abs(original_edges))
            
            # 边缘增强比率
            if original_edge_strength > 0:
                edge_ratio = upscaled_edge_strength / original_edge_strength
                return min(10.0, edge_ratio * 5.0)
            else:
                return 5.0
                
        except:
            return 5.0
    
    def _calculate_detail_preservation(self, upscaled: np.ndarray, original: np.ndarray) -> float:
        """计算细节保持评分"""
        try:
            # 计算标准差（细节丰富度指标）
            upscaled_std = np.std(upscaled)
            original_std = np.std(original)
            
            if original_std > 0:
                detail_ratio = upscaled_std / original_std
                return min(10.0, detail_ratio * 5.0)
            else:
                return 5.0
                
        except:
            return 5.0
    
    def _calculate_noise_reduction(self, upscaled: np.ndarray, original: np.ndarray) -> float:
        """计算噪点控制评分"""
        try:
            # 简单的噪点评估：计算高频成分
            from scipy import ndimage
            
            if len(upscaled.shape) == 3:
                upscaled_gray = np.mean(upscaled, axis=2)
                original_gray = np.mean(original, axis=2)
            else:
                upscaled_gray = upscaled
                original_gray = original
            
            # 高通滤波检测噪点
            kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
            upscaled_noise = np.abs(ndimage.convolve(upscaled_gray, kernel))
            original_noise = np.abs(ndimage.convolve(original_gray, kernel))
            
            upscaled_noise_level = np.mean(upscaled_noise)
            original_noise_level = np.mean(original_noise)
            
            # 噪点减少比率
            if original_noise_level > 0:
                noise_reduction = 1.0 - (upscaled_noise_level / original_noise_level)
                return max(0.0, min(10.0, (noise_reduction + 0.5) * 10.0))
            else:
                return 7.0
                
        except:
            return 5.0
    

    
    def _simple_upscale(self, image: Image.Image, log_callback=None) -> Image.Image:
        """简单的图像放大"""
        try:
            if log_callback:
                log_callback(f"        使用传统算法处理...")
            
            width, height = image.size
            new_size = (width * 2, height * 2)
            return image.resize(new_size, Image.LANCZOS)
            
        except Exception as e:
            logger.error(f"简单放大失败: {e}")
            return image
    
    def _validate_output_image(self, image: Image.Image) -> bool:
        """验证输出图像的有效性"""
        try:
            if not image or image.size[0] == 0 or image.size[1] == 0:
                return False
            
            # 转换为numpy数组检查
            import numpy as np
            img_array = np.array(image)
            
            # 检查是否为全黑图像
            if np.all(img_array == 0):
                return False
            
            # 检查是否为异常图像（标准差过小可能是雪花状态）
            if np.std(img_array) < 5:
                return False
            
            # 检查图像是否有合理的像素值分布
            unique_values = len(np.unique(img_array))
            if unique_values < 10:  # 颜色过少可能是异常图像
                return False
            
            return True
            
        except Exception:
            return False
    
    def _process_large_image(self, image: Image.Image, method: str, log_callback=None, gpu_available=None) -> bytes:
        """处理超大图像的分块处理"""
        try:
            if log_callback:
                log_callback(f"      🔄 启动分块处理模式")
            
            width, height = image.size
            # 计算分块大小
            block_size = 2048 if gpu_available else 1024
            
            # 创建输出图像
            output_width = width * 2
            output_height = height * 2
            output_image = Image.new('RGB', (output_width, output_height))
            
            # 分块处理
            blocks_x = (width + block_size - 1) // block_size
            blocks_y = (height + block_size - 1) // block_size
            
            for y in range(blocks_y):
                for x in range(blocks_x):
                    # 计算块的边界
                    left = x * block_size
                    top = y * block_size
                    right = min(left + block_size, width)
                    bottom = min(top + block_size, height)
                    
                    # 提取块
                    block = image.crop((left, top, right, bottom))
                    
                    # 处理块
                    block_bytes = io.BytesIO()
                    block.save(block_bytes, format='PNG')
                    
                    # 递归调用（但不会再次触发大图像处理）
                    processed_block_bytes = self._upscale_image(
                        block_bytes.getvalue(), method, None, gpu_available
                    )
                    
                    # 将处理后的块放回输出图像
                    processed_block = Image.open(io.BytesIO(processed_block_bytes))
                    output_left = left * 2
                    output_top = top * 2
                    output_image.paste(processed_block, (output_left, output_top))
                    
                    if log_callback:
                        progress = ((y * blocks_x + x + 1) / (blocks_x * blocks_y)) * 100
                        log_callback(f"      📊 分块进度: {progress:.1f}%")
            
            # 转换为字节数据
            output_buffer = io.BytesIO()
            output_image.save(output_buffer, format='PNG', optimize=True)
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"大图像分块处理失败: {e}")
            if log_callback:
                log_callback(f"      ❌ 分块处理失败，使用简单放大")
            # 降级到简单放大
            simple_result = self._simple_upscale(image, log_callback)
            output_buffer = io.BytesIO()
            simple_result.save(output_buffer, format='PNG', optimize=True)
            return output_buffer.getvalue()
    
    def _replace_image_in_page(self, page, xref: int, new_image_bytes: bytes):
        """替换页面中的图像"""
        try:
            # 获取文档对象
            doc = page.parent
            
            # 更新图像对象
            doc.update_stream(xref, new_image_bytes)
            
            # 刷新页面以应用更改
            page.clean_contents()
            
        except Exception as e:
            logger.error(f"图像替换失败: {e}")
    
    def _get_method_description(self, method: str) -> str:
        """获取方法描述"""
        descriptions = {
            "anime": "动漫/插图（Waifu2x）",
            "photo": "照片/写真（Waifu2x）",
            "document": "扫描文档（Waifu2x）"
        }
        return descriptions.get(method, "通用处理")
    
    def _check_dependencies(self):
        """检查依赖项"""
        try:
            import fitz
            from PIL import Image
        except ImportError as e:
            logger.warning(f"PDF高清化插件依赖项缺失: {e}")
    
    def _setup_gpu_environment(self):
        """设置GPU环境，解决双显卡问题"""
        import os
        
        # 强制使用CUDA设备（如果可用）
        os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # 默认使用第一个GPU
        
        # 设置PyTorch CUDA设备顺序
        os.environ['CUDA_DEVICE_ORDER'] = 'PCI_BUS_ID'
        
        # 禁用CPU回退警告
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'
    
    def _check_gpu_availability(self, log_callback=None) -> bool:
        """检测GPU可用性 - 增强双显卡支持"""
        try:
            import torch
            
            # 基础GPU检查
            if not torch.cuda.is_available():
                if log_callback:
                    log_callback("🚫 CUDA不可用，使用CPU模式")
                return False
            
            device_count = torch.cuda.device_count()
            if device_count == 0:
                if log_callback:
                    log_callback("🚫 未检测到CUDA设备，使用CPU模式")
                return False
            
            # 双显卡环境诊断
            if log_callback:
                log_callback(f"🔍 检测到 {device_count} 个GPU设备:")
                for i in range(device_count):
                    try:
                        props = torch.cuda.get_device_properties(i)
                        memory_gb = props.total_memory / 1024**3
                        log_callback(f"  GPU {i}: {props.name} ({memory_gb:.1f}GB)")
                        
                        # 检查GPU是否可用于计算
                        torch.cuda.set_device(i)
                        test_tensor = torch.tensor([1.0]).cuda()
                        _ = test_tensor + 1
                        log_callback(f"  ✅ GPU {i} 可用于CUDA计算")
                    except Exception as e:
                        log_callback(f"  ❌ GPU {i} 不可用: {str(e)}")
            
            # 选择最佳GPU（优先选择显存最大的独立显卡）
            best_gpu = self._select_best_gpu(log_callback)
            if best_gpu is not None:
                torch.cuda.set_device(best_gpu)
                if log_callback:
                    log_callback(f"🎯 选择GPU {best_gpu}作为主要计算设备")
                return True
            
            return False
            
        except ImportError:
            if log_callback:
                log_callback("❌ PyTorch未安装，无法使用GPU加速")
            return False
        except Exception as e:
            if log_callback:
                log_callback(f"❌ GPU检测失败: {str(e)}")
            return False
    
    def _select_best_gpu(self, log_callback=None) -> int:
        """选择最佳GPU设备（双显卡环境优化）"""
        try:
            import torch
            device_count = torch.cuda.device_count()
            
            if device_count == 1:
                return 0
            
            best_device = 0
            max_memory = 0
            
            for i in range(device_count):
                try:
                    props = torch.cuda.get_device_properties(i)
                    memory = props.total_memory
                    
                    # 优先选择独立显卡（通常显存更大）
                    # NVIDIA独立显卡通常名称包含GTX、RTX、Tesla等
                    is_discrete = any(keyword in props.name.upper() for keyword in 
                                    ['GTX', 'RTX', 'TESLA', 'QUADRO', 'TITAN'])
                    
                    if log_callback:
                        gpu_type = "独立显卡" if is_discrete else "集成显卡"
                        log_callback(f"  GPU {i}: {props.name} - {gpu_type}, {memory/1024**3:.1f}GB")
                    
                    # 选择策略：优先独立显卡，其次显存大的
                    if is_discrete and memory > max_memory:
                        best_device = i
                        max_memory = memory
                    elif not is_discrete and max_memory == 0:
                        # 如果没有独立显卡，选择显存最大的集成显卡
                        if memory > max_memory:
                            best_device = i
                            max_memory = memory
                            
                except Exception as e:
                    if log_callback:
                        log_callback(f"  GPU {i} 信息获取失败: {str(e)}")
                    continue
            
            return best_device
            
        except Exception as e:
            if log_callback:
                log_callback(f"GPU选择失败: {str(e)}")
            return 0
    
    def _optimize_image_layout(self, original_rect, image_path, page, log_callback=None):
        """智能优化图像布局，考虑高清化后的实际尺寸
        
        Args:
            original_rect: 原始图像矩形区域
            image_path: 高清化后的图像文件路径
            page: PDF页面对象
            log_callback: 日志回调函数
            
        Returns:
            优化后的图像矩形区域
        """
        try:
            # 获取页面尺寸
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # 获取高清化后的图像尺寸
            with Image.open(image_path) as img:
                upscaled_width, upscaled_height = img.size
                img_aspect_ratio = upscaled_width / upscaled_height
            
            # 计算原始图像的理论尺寸（用于比较）
            original_width = original_rect.width
            original_height = original_rect.height
            
            if log_callback:
                scale_factor_w = upscaled_width / original_width if original_width > 0 else 1
                scale_factor_h = upscaled_height / original_height if original_height > 0 else 1
                log_callback(f"        📏 图像已放大: {original_width:.0f}x{original_height:.0f} -> {upscaled_width}x{upscaled_height} (缩放: {scale_factor_w:.1f}x)")
            
            # 分析页面布局，检测可用空间
            available_space = self._analyze_page_layout(page, original_rect, log_callback)
            
            # 计算最佳显示尺寸（考虑高清化后的实际尺寸）
            optimized_rect = self._calculate_display_rect(
                original_rect, upscaled_width, upscaled_height, 
                available_space, page_width, page_height, log_callback
            )
            
            if log_callback:
                orig_area = (original_rect.width * original_rect.height)
                new_area = (optimized_rect.width * optimized_rect.height)
                size_increase = ((new_area - orig_area) / orig_area) * 100
                log_callback(f"        📐 显示尺寸优化: {size_increase:.1f}% 增大")
            
            return optimized_rect
            
        except Exception as e:
            if log_callback:
                log_callback(f"        ⚠️ 布局优化失败，使用原始尺寸: {str(e)}")
            return original_rect
    
    def _analyze_page_layout(self, page, current_rect, log_callback=None):
        """分析页面布局，检测可用的空白区域
        
        Args:
            page: PDF页面对象
            current_rect: 当前图像矩形
            log_callback: 日志回调函数
            
        Returns:
            可用空间信息字典
        """
        page_rect = page.rect
        
        # 获取页面中的所有文本块和图像
        text_blocks = page.get_text("dict")["blocks"]
        image_list = page.get_images()
        
        # 计算页面边距（基于内容分布）
        content_bounds = self._calculate_content_bounds(text_blocks, image_list, page)
        
        # 检测当前图像周围的空白区域
        available_space = {
            'left_margin': max(0, current_rect.x0 - content_bounds['left']),
            'right_margin': max(0, content_bounds['right'] - current_rect.x1),
            'top_margin': max(0, current_rect.y0 - content_bounds['top']),
            'bottom_margin': max(0, content_bounds['bottom'] - current_rect.y1),
            'page_width': page_rect.width,
            'page_height': page_rect.height,
            'content_bounds': content_bounds
        }
        
        return available_space
    
    def _calculate_content_bounds(self, text_blocks, image_list, page):
        """计算页面内容的边界
        
        Args:
            text_blocks: 文本块列表
            image_list: 图像列表
            page: PDF页面对象
            
        Returns:
            内容边界字典
        """
        page_rect = page.rect
        
        # 默认边界（页面边缘）
        bounds = {
            'left': page_rect.x0,
            'right': page_rect.x1,
            'top': page_rect.y0,
            'bottom': page_rect.y1
        }
        
        # 分析文本内容边界
        text_rects = []
        for block in text_blocks:
            if 'lines' in block:  # 文本块
                for line in block['lines']:
                    for span in line['spans']:
                        bbox = span['bbox']
                        text_rects.append(bbox)
        
        # 分析图像边界
        for img in image_list:
            img_rects = page.get_image_rects(img[0])
            for rect in img_rects:
                text_rects.append([rect.x0, rect.y0, rect.x1, rect.y1])
        
        # 计算实际内容边界
        if text_rects:
            all_x0 = [rect[0] for rect in text_rects]
            all_y0 = [rect[1] for rect in text_rects]
            all_x1 = [rect[2] for rect in text_rects]
            all_y1 = [rect[3] for rect in text_rects]
            
            content_left = min(all_x0)
            content_top = min(all_y0)
            content_right = max(all_x1)
            content_bottom = max(all_y1)
            
            # 智能边距分析：检测可用的白空间
            page_width = page_rect.x1 - page_rect.x0
            page_height = page_rect.y1 - page_rect.y0
            
            # 计算各方向的空白空间
            left_margin = content_left - page_rect.x0
            right_margin = page_rect.x1 - content_right
            top_margin = content_top - page_rect.y0
            bottom_margin = page_rect.y1 - content_bottom
            
            # 白空间利用策略：如果某个方向有足够空间，可以更积极地利用
            margin_threshold = min(page_width, page_height) * 0.05  # 5%页面尺寸作为阈值
            
            # 更新边界，考虑可利用的白空间
            if left_margin > margin_threshold:
                bounds['left'] = content_left - left_margin * 0.3  # 利用30%的左边距
            else:
                bounds['left'] = content_left
                
            if right_margin > margin_threshold:
                bounds['right'] = content_right + right_margin * 0.3  # 利用30%的右边距
            else:
                bounds['right'] = content_right
                
            if top_margin > margin_threshold:
                bounds['top'] = content_top - top_margin * 0.3  # 利用30%的上边距
            else:
                bounds['top'] = content_top
                
            if bottom_margin > margin_threshold:
                bounds['bottom'] = content_bottom + bottom_margin * 0.3  # 利用30%的下边距
            else:
                bounds['bottom'] = content_bottom
        
        return bounds
    
    def _calculate_display_rect(self, original_rect, upscaled_width, upscaled_height, 
                              available_space, page_width, page_height, log_callback=None):
        """计算高清化图像的最佳显示矩形
        
        Args:
            original_rect: 原始图像矩形
            upscaled_width: 高清化后的图像宽度
            upscaled_height: 高清化后的图像高度
            available_space: 可用空间信息
            page_width: 页面宽度
            page_height: 页面高度
            log_callback: 日志回调函数
            
        Returns:
            优化后的图像矩形
        """
        import fitz
        
        # 计算图像的宽高比
        img_aspect_ratio = upscaled_width / upscaled_height
        
        # 计算可用的最大显示区域（更积极的空间利用）
        max_display_width = min(
            page_width * 0.98,  # 提升到98%页面宽度利用率
            original_rect.width + available_space['left_margin'] + available_space['right_margin'] * 1.5  # 更积极利用右边距
        )
        
        max_display_height = min(
            page_height * 0.98,  # 提升到98%页面高度利用率
            original_rect.height + available_space['top_margin'] + available_space['bottom_margin'] * 1.5  # 更积极利用下边距
        )
        
        # 策略1: 智能显示密度优化
        # 目标显示密度: 1.5-2.0 像素/点 (最佳视觉效果)
        optimal_density = 1.8  # 最佳显示密度
        min_density = 1.2      # 最小可接受密度
        max_density = 3.0      # 最大可接受密度
        
        # 计算基于最佳密度的目标显示尺寸
        optimal_display_width = upscaled_width / optimal_density
        optimal_display_height = upscaled_height / optimal_density
        
        # 初始目标尺寸（优先考虑最佳显示密度）
        target_width = optimal_display_width
        target_height = optimal_display_height
        
        # 如果最佳尺寸超出可用空间，则按比例缩放
        if target_width > max_display_width or target_height > max_display_height:
            # 计算缩放比例，保持宽高比
            scale_w = max_display_width / target_width
            scale_h = max_display_height / target_height
            scale = min(scale_w, scale_h)
            
            target_width = target_width * scale
            target_height = target_height * scale
            
            # 检查缩放后的显示密度
            final_density_x = upscaled_width / target_width
            final_density_y = upscaled_height / target_height
            avg_density = (final_density_x + final_density_y) / 2
            
            if log_callback:
                log_callback(f"        🔄 空间限制缩放: 比例 {scale:.2f}, 显示密度 {avg_density:.1f} 像素/点")
        else:
            if log_callback:
                log_callback(f"        ✨ 最佳密度显示: {optimal_density:.1f} 像素/点")
        
        # 智能最小尺寸保证（基于显示密度和原始尺寸）
        # 确保显示密度不会过高，同时保证视觉改善
        max_acceptable_density = max_density
        min_width_by_density = upscaled_width / max_acceptable_density
        min_height_by_density = upscaled_height / max_acceptable_density
        
        # 原始尺寸的智能放大（至少1.2倍，最多2.5倍）
        min_width_by_original = original_rect.width * 1.2  # 至少比原始大20%
        min_height_by_original = original_rect.height * 1.2
        max_width_by_original = original_rect.width * 2.5  # 最多放大2.5倍
        max_height_by_original = original_rect.height * 2.5
        
        # 选择更合理的最小尺寸
        min_width = max(min_width_by_density, min_width_by_original)
        min_height = max(min_height_by_density, min_height_by_original)
        
        # 应用最小尺寸约束
        if target_width < min_width or target_height < min_height:
            # 按比例放大到至少最小尺寸
            scale_w = min_width / target_width if target_width < min_width else 1.0
            scale_h = min_height / target_height if target_height < min_height else 1.0
            scale = max(scale_w, scale_h)
            
            target_width = target_width * scale
            target_height = target_height * scale
            
            if log_callback:
                log_callback(f"        📏 应用最小尺寸约束: 缩放 {scale:.2f}x")
        
        # 应用最大尺寸约束（防止过度放大）
        if target_width > max_width_by_original or target_height > max_height_by_original:
            scale_w = max_width_by_original / target_width if target_width > max_width_by_original else 1.0
            scale_h = max_height_by_original / target_height if target_height > max_height_by_original else 1.0
            scale = min(scale_w, scale_h)
            
            target_width = target_width * scale
            target_height = target_height * scale
            
            if log_callback:
                log_callback(f"        🔒 应用最大尺寸限制: 缩放 {scale:.2f}x")
        
        # 智能居中策略：优先考虑页面可用空间
        # 计算可用显示区域的中心点
        available_left = max(0, available_space.get('left_margin', 0))
        available_right = min(page_width, page_width - available_space.get('right_margin', 0))
        available_top = max(0, available_space.get('top_margin', 0))
        available_bottom = min(page_height, page_height - available_space.get('bottom_margin', 0))
        
        available_center_x = (available_left + available_right) / 2
        available_center_y = (available_top + available_bottom) / 2
        
        # 如果可用空间太小，则使用页面中心
        if (available_right - available_left) < target_width * 1.1 or (available_bottom - available_top) < target_height * 1.1:
            # 使用页面中心作为参考
            center_x = page_width / 2
            center_y = page_height / 2
            if log_callback:
                log_callback(f"        🎯 使用页面中心定位 ({center_x:.0f}, {center_y:.0f})")
        else:
            # 使用可用空间中心，但考虑原始位置的偏好
            original_center_x = original_rect.x0 + original_rect.width / 2
            original_center_y = original_rect.y0 + original_rect.height / 2
            
            # 在可用空间中心和原始中心之间找平衡
            center_x = (available_center_x + original_center_x) / 2
            center_y = (available_center_y + original_center_y) / 2
            
            # 确保中心点在合理范围内
            center_x = max(target_width/2, min(page_width - target_width/2, center_x))
            center_y = max(target_height/2, min(page_height - target_height/2, center_y))
            
            if log_callback:
                log_callback(f"        🎯 使用智能居中定位 ({center_x:.0f}, {center_y:.0f})")
        
        new_x0 = center_x - target_width / 2
        new_y0 = center_y - target_height / 2
        new_x1 = new_x0 + target_width
        new_y1 = new_y0 + target_height
        
        # 智能边界检查和尺寸调整
        # 添加安全边距，确保图片不会紧贴页面边缘
        safety_margin = 10  # 10pt 安全边距
        safe_page_width = page_width - 2 * safety_margin
        safe_page_height = page_height - 2 * safety_margin
        
        # 如果图片尺寸超出安全页面范围，需要先缩放再居中
        if target_width > safe_page_width or target_height > safe_page_height:
            # 计算适应安全页面的缩放比例
            scale_w = safe_page_width / target_width if target_width > safe_page_width else 1.0
            scale_h = safe_page_height / target_height if target_height > safe_page_height else 1.0
            boundary_scale = min(scale_w, scale_h) * 0.95  # 额外5%的安全系数
            
            # 应用边界缩放
            target_width = target_width * boundary_scale
            target_height = target_height * boundary_scale
            
            if log_callback:
                log_callback(f"        🔒 边界约束缩放: {boundary_scale:.2f}x (含安全边距)")
        
        # 重新计算居中位置（基于调整后的尺寸）
        # 使用之前计算的智能中心位置，而不是原始图片中心
        new_x0 = center_x - target_width / 2
        new_y0 = center_y - target_height / 2
        new_x1 = new_x0 + target_width
        new_y1 = new_y0 + target_height
        
        # 边界微调（确保完全在安全区域内且尽量居中）
        # 水平方向调整
        if new_x0 < safety_margin:
            new_x0 = safety_margin
            new_x1 = new_x0 + target_width
        elif new_x1 > page_width - safety_margin:
            new_x1 = page_width - safety_margin
            new_x0 = new_x1 - target_width
        
        # 垂直方向调整
        if new_y0 < safety_margin:
            new_y0 = safety_margin
            new_y1 = new_y0 + target_height
        elif new_y1 > page_height - safety_margin:
            new_y1 = page_height - safety_margin
            new_y0 = new_y1 - target_height
        
        # 最终尺寸确认
        final_width = new_x1 - new_x0
        final_height = new_y1 - new_y0
        
        # 验证最终位置
        if log_callback:
            if (new_x0 >= safety_margin and new_y0 >= safety_margin and 
                new_x1 <= page_width - safety_margin and new_y1 <= page_height - safety_margin):
                log_callback(f"        ✅ 位置验证: 图片完全在安全区域内")
            elif new_x0 >= 0 and new_y0 >= 0 and new_x1 <= page_width and new_y1 <= page_height:
                log_callback(f"        📍 位置验证: 图片在页面范围内但接近边缘")
            else:
                log_callback(f"        ⚠️  位置警告: 图片可能超出页面边界")
        
        # 计算最终显示效果统计
        if log_callback:
            scale_factor_x = final_width / original_rect.width if original_rect.width > 0 else 1
            scale_factor_y = final_height / original_rect.height if original_rect.height > 0 else 1
            avg_scale = (scale_factor_x + scale_factor_y) / 2
            
            # 计算最终显示密度
            final_density_x = upscaled_width / final_width if final_width > 0 else 0
            final_density_y = upscaled_height / final_height if final_height > 0 else 0
            avg_final_density = (final_density_x + final_density_y) / 2
            
            # 计算页面覆盖率改善
            original_area = original_rect.width * original_rect.height
            final_area = final_width * final_height
            page_area = page_width * page_height
            coverage_improvement = (final_area - original_area) / page_area * 100 if page_area > 0 else 0
            
            log_callback(f"        📺 最终显示: {final_width:.0f}x{final_height:.0f}pt (放大 {avg_scale:.1f}x)")
            log_callback(f"        🎯 显示密度: {avg_final_density:.1f} 像素/点")
            log_callback(f"        📈 页面覆盖提升: +{coverage_improvement:.1f}%")
        
        return fitz.Rect(new_x0, new_y0, new_x1, new_y1)
    
    def _calculate_optimized_rect(self, original_rect, available_space, img_aspect_ratio, 
                                page_width, page_height, log_callback=None):
        """计算优化后的图像矩形（保留用于兼容性）
        
        Args:
            original_rect: 原始图像矩形
            available_space: 可用空间信息
            img_aspect_ratio: 图像宽高比
            page_width: 页面宽度
            page_height: 页面高度
            log_callback: 日志回调函数
            
        Returns:
            优化后的图像矩形
        """
        import fitz
        
        # 设置最小和最大缩放比例
        min_scale = 1.0  # 不缩小
        max_scale = 3.0  # 最大放大3倍
        
        # 计算可以扩展的最大尺寸
        max_width = min(
            page_width * 0.9,  # 不超过页面宽度的90%
            original_rect.width + available_space['left_margin'] + available_space['right_margin']
        )
        
        max_height = min(
            page_height * 0.9,  # 不超过页面高度的90%
            original_rect.height + available_space['top_margin'] + available_space['bottom_margin']
        )
        
        # 根据图像宽高比计算最佳尺寸
        if img_aspect_ratio > 1:  # 横向图像
            new_width = min(max_width, original_rect.width * max_scale)
            new_height = new_width / img_aspect_ratio
            
            if new_height > max_height:
                new_height = min(max_height, original_rect.height * max_scale)
                new_width = new_height * img_aspect_ratio
        else:  # 纵向图像
            new_height = min(max_height, original_rect.height * max_scale)
            new_width = new_height * img_aspect_ratio
            
            if new_width > max_width:
                new_width = min(max_width, original_rect.width * max_scale)
                new_height = new_width / img_aspect_ratio
        
        # 确保不小于原始尺寸
        new_width = max(new_width, original_rect.width)
        new_height = max(new_height, original_rect.height)
        
        # 计算新的位置（尽量居中，但考虑页面布局）
        center_x = original_rect.x0 + original_rect.width / 2
        center_y = original_rect.y0 + original_rect.height / 2
        
        new_x0 = center_x - new_width / 2
        new_y0 = center_y - new_height / 2
        new_x1 = new_x0 + new_width
        new_y1 = new_y0 + new_height
        
        # 确保不超出页面边界
        if new_x0 < 0:
            new_x1 -= new_x0
            new_x0 = 0
        elif new_x1 > page_width:
            new_x0 -= (new_x1 - page_width)
            new_x1 = page_width
        
        if new_y0 < 0:
            new_y1 -= new_y0
            new_y0 = 0
        elif new_y1 > page_height:
            new_y0 -= (new_y1 - page_height)
            new_y1 = page_height
        
        return fitz.Rect(new_x0, new_y0, new_x1, new_y1)
    
    def _insert_upscaled_image(self, page, rect, image_path, log_callback=None):
        """优化的图像插入方法，直接使用优化后的矩形尺寸显示高清化图像"""
        try:
            # 获取图像实际尺寸
            with Image.open(image_path) as img:
                img_width, img_height = img.size
            
            # 直接使用传入的矩形区域（这个矩形已经通过_calculate_display_rect优化过）
            # 不再进行额外的缩放计算，让高清化图像以优化后的尺寸显示
            page.insert_image(rect, filename=image_path)
            
            if log_callback:
                log_callback(f"        📐 高清化图像插入: {img_width}x{img_height} 显示为 {rect.width:.0f}x{rect.height:.0f}")
                
        except Exception as e:
            logger.error(f"优化图像插入失败: {e}")
            # 回退到原始方法
            page.insert_image(rect, filename=image_path)
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {temp_file}, 错误: {e}")
        self._temp_files.clear()
    
    def _optimize_batch_processing(self, image_list, upscale_method, log_callback=None):
        """批处理优化 - 对多个图像进行批量处理以提升GPU利用率"""
        if not image_list or len(image_list) < 2:
            return None
            
        try:
            # 检查是否可以进行批处理
            gpu_available = self._check_gpu_availability()
            if not gpu_available:
                return None
                
            if log_callback:
                log_callback(f"      🔄 启用批处理模式，处理 {len(image_list)} 个图像")
                
            # 这里可以实现批处理逻辑
            # 目前返回None，使用单个处理模式
            return None
            
        except Exception as e:
            logger.error(f"批处理优化失败: {e}")
            return None
    
    def get_default_options(self) -> Dict[str, Any]:
        """获取默认转换选项"""
        return {
            'upscale_method': 'photo',
            'scale_factor': 2,
            'quality': 95,
            'enable_gpu': True,
            'batch_size': 4  # GPU批处理大小
        }
    
    def cleanup(self):
        """清理临时文件"""
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
        self._temp_files.clear()

# 插件注册函数
def register_converter():
    """注册转换器插件"""
    return PDFUpscaleConverter()

# 插件元数据
CONVERTER_METADATA = ConverterMetadata(
    name="pdf_upscale",
    description="PDF高清化转换器 - 使用AI算法提升PDF中图像的分辨率和质量",
    version="1.0.0",
    author="PDF Converter Team",
    supported_input_formats=["pdf"],
    supported_output_formats=["pdf"],
    dependencies=["PyMuPDF", "Pillow"],
    priority=10
)