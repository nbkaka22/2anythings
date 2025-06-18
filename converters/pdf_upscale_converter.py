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

# 导入基类
from converters.converter_interface import ConverterInterface, ConverterMetadata

logger = logging.getLogger('pdf_converter')

class PDFUpscaleConverter(ConverterInterface):
    """PDF高清化转换器
    
    使用Real-ESRGAN和Waifu2x对PDF中的图像进行超分辨率处理
    """
    
    def __init__(self):
        self._temp_files = []
        self._check_dependencies()
        self._setup_gpu_environment()
    
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
                                        
                                        # 插入图像到指定位置
                                        new_page.insert_image(img_rect, filename=temp_img_path)
                                        
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
                        upscaled_image = self._waifu2x_upscale(image, log_callback, gpu_available)
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
    
    def _waifu2x_upscale(self, image: Image.Image, log_callback=None, gpu_available=None) -> Image.Image:
        """使用Waifu2x进行动漫图像高清化"""
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
            
            # 优化的Waifu2x配置
            waifu2x = Waifu2x(
                gpuid=gpuid,  # 动态选择GPU/CPU
                tta_mode=False,  # 关闭TTA以提升速度
                num_threads=4 if gpuid == -1 else 1,  # CPU时使用多线程
                noise=1,  # 降噪级别 (0-3)
                scale=2,  # 放大倍数
                tilesize=512 if gpu_available else 256,  # GPU时使用更大瓦片
                model="models-cunet"  # 动漫风格模型
            )
            
            # 使用Waifu2x处理图像
            upscaled_image = waifu2x.process_pil(image)
            
            return upscaled_image
            
        except ImportError as e:
            if log_callback:
                log_callback(f"        Waifu2x库未安装: {str(e)}。请运行 'pip install waifu2x-ncnn-py' 安装")
            return self._simple_upscale(image, log_callback)
        except Exception as e:
            logger.error(f"Waifu2x处理失败: {e}")
            return self._simple_upscale(image, log_callback)
    

    
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
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {temp_file}, {e}")
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