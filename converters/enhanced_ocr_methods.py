"""增强OCR方法模块

提供增强的OCR处理方法，包括批量处理和单图像处理。
"""

import logging
from typing import List, Dict, Any, Optional, Union
from PIL import Image
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

logger = logging.getLogger(__name__)

class EnhancedOCRMethods:
    """增强OCR方法类
    
    提供批量处理、并发处理等增强功能。
    """
    
    def __init__(self, converter_instance):
        """初始化增强OCR方法
        
        Args:
            converter_instance: OCR转换器实例
        """
        self.converter = converter_instance
        self.lock = threading.Lock()
        
        # 批量处理配置
        self.batch_size = 5
        self.max_workers = 3
        self.timeout_per_image = 30.0
        
    def extract_text_from_image(self, image: Union[Image.Image, str, np.ndarray]) -> Dict[str, Any]:
        """从单个图像提取文本
        
        Args:
            image: PIL图像对象、图像路径或numpy数组
            
        Returns:
            包含OCR结果的字典
        """
        try:
            # 标准化图像输入
            pil_image = self._normalize_image_input(image)
            
            # 图像预处理
            processed_image = self._preprocess_image(pil_image)
            
            # 执行OCR
            ocr_result = self._perform_ocr(processed_image)
            
            # 后处理结果
            processed_result = self._postprocess_result(ocr_result)
            
            return {
                'success': True,
                'text': processed_result.get('text', ''),
                'confidence': processed_result.get('confidence', 0.0),
                'boxes': processed_result.get('boxes', []),
                'processing_time': processed_result.get('processing_time', 0.0),
                'method': 'enhanced_single'
            }
            
        except Exception as e:
            logger.error(f"单图像OCR处理失败: {e}")
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'boxes': [],
                'error': str(e),
                'method': 'enhanced_single'
            }
    
    def batch_process_images(self, images: List[Union[Image.Image, str, np.ndarray]]) -> List[Dict[str, Any]]:
        """批量处理图像
        
        Args:
            images: 图像列表
            
        Returns:
            OCR结果列表
        """
        if not images:
            return []
        
        logger.info(f"开始批量OCR处理，共 {len(images)} 张图像")
        start_time = time.time()
        
        results = []
        
        # 分批处理
        for i in range(0, len(images), self.batch_size):
            batch = images[i:i + self.batch_size]
            batch_results = self._process_batch_concurrent(batch, i)
            results.extend(batch_results)
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.get('success', False))
        
        logger.info(f"批量OCR处理完成: {success_count}/{len(images)} 成功, 耗时: {total_time:.2f}秒")
        
        return results
    
    def _process_batch_concurrent(self, batch: List[Union[Image.Image, str, np.ndarray]], 
                                batch_index: int) -> List[Dict[str, Any]]:
        """并发处理一批图像
        
        Args:
            batch: 图像批次
            batch_index: 批次索引
            
        Returns:
            批次处理结果
        """
        results = [None] * len(batch)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任务
            future_to_index = {
                executor.submit(self._process_single_with_timeout, img, batch_index * self.batch_size + idx): idx
                for idx, img in enumerate(batch)
            }
            
            # 收集结果
            for future in as_completed(future_to_index, timeout=self.timeout_per_image * len(batch)):
                index = future_to_index[future]
                try:
                    result = future.result(timeout=self.timeout_per_image)
                    results[index] = result
                except Exception as e:
                    logger.error(f"批次 {batch_index} 图像 {index} 处理失败: {e}")
                    results[index] = {
                        'success': False,
                        'text': '',
                        'confidence': 0.0,
                        'boxes': [],
                        'error': str(e),
                        'method': 'enhanced_batch'
                    }
        
        # 确保所有位置都有结果
        for i, result in enumerate(results):
            if result is None:
                results[i] = {
                    'success': False,
                    'text': '',
                    'confidence': 0.0,
                    'boxes': [],
                    'error': 'Processing timeout or failed',
                    'method': 'enhanced_batch'
                }
        
        return results
    
    def _process_single_with_timeout(self, image: Union[Image.Image, str, np.ndarray], 
                                   image_index: int) -> Dict[str, Any]:
        """带超时的单图像处理
        
        Args:
            image: 图像
            image_index: 图像索引
            
        Returns:
            处理结果
        """
        try:
            result = self.extract_text_from_image(image)
            result['image_index'] = image_index
            return result
        except Exception as e:
            logger.error(f"图像 {image_index} 处理失败: {e}")
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'boxes': [],
                'error': str(e),
                'image_index': image_index,
                'method': 'enhanced_batch'
            }
    
    def _normalize_image_input(self, image: Union[Image.Image, str, np.ndarray]) -> Image.Image:
        """标准化图像输入
        
        Args:
            image: 各种格式的图像输入
            
        Returns:
            PIL图像对象
        """
        if isinstance(image, Image.Image):
            return image
        elif isinstance(image, str):
            return Image.open(image)
        elif isinstance(image, np.ndarray):
            return Image.fromarray(image)
        else:
            raise ValueError(f"不支持的图像类型: {type(image)}")
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """图像预处理
        
        Args:
            image: PIL图像对象
            
        Returns:
            预处理后的图像
        """
        try:
            # 转换为RGB模式
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 检查图像尺寸，如果太大则缩放
            max_size = 2048
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.debug(f"图像已缩放至: {new_size}")
            
            return image
            
        except Exception as e:
            logger.warning(f"图像预处理失败，使用原图: {e}")
            return image
    
    def _perform_ocr(self, image: Image.Image) -> Dict[str, Any]:
        """执行OCR识别
        
        Args:
            image: 预处理后的图像
            
        Returns:
            OCR原始结果
        """
        start_time = time.time()
        
        try:
            # 获取OCR引擎
            ocr_engine = self.converter._get_paddle_ocr()
            
            # 转换图像为numpy数组
            img_array = np.array(image)
            
            # 执行OCR
            ocr_result = ocr_engine.ocr(img_array, cls=True)
            
            processing_time = time.time() - start_time
            
            return {
                'raw_result': ocr_result,
                'processing_time': processing_time,
                'success': True
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"OCR识别失败: {e}")
            return {
                'raw_result': None,
                'processing_time': processing_time,
                'success': False,
                'error': str(e)
            }
    
    def _postprocess_result(self, ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        """后处理OCR结果
        
        Args:
            ocr_result: OCR原始结果
            
        Returns:
            处理后的结果
        """
        if not ocr_result.get('success', False):
            return {
                'text': '',
                'confidence': 0.0,
                'boxes': [],
                'processing_time': ocr_result.get('processing_time', 0.0)
            }
        
        try:
            raw_result = ocr_result.get('raw_result', [])
            
            if not raw_result or not raw_result[0]:
                return {
                    'text': '',
                    'confidence': 0.0,
                    'boxes': [],
                    'processing_time': ocr_result.get('processing_time', 0.0)
                }
            
            # 提取文本和置信度
            texts = []
            confidences = []
            boxes = []
            
            for line in raw_result[0]:
                if line and len(line) >= 2:
                    box = line[0]
                    text_info = line[1]
                    
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                        text = text_info[0]
                        confidence = text_info[1]
                    else:
                        text = str(text_info)
                        confidence = 0.8  # 默认置信度
                    
                    if text and text.strip():
                        texts.append(text.strip())
                        confidences.append(float(confidence))
                        boxes.append(box)
            
            # 合并文本
            combined_text = '\n'.join(texts)
            
            # 计算平均置信度
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                'text': combined_text,
                'confidence': avg_confidence,
                'boxes': boxes,
                'processing_time': ocr_result.get('processing_time', 0.0)
            }
            
        except Exception as e:
            logger.error(f"OCR结果后处理失败: {e}")
            return {
                'text': '',
                'confidence': 0.0,
                'boxes': [],
                'processing_time': ocr_result.get('processing_time', 0.0)
            }
    
    def set_batch_config(self, batch_size: int = None, max_workers: int = None, 
                        timeout_per_image: float = None):
        """设置批量处理配置
        
        Args:
            batch_size: 批次大小
            max_workers: 最大工作线程数
            timeout_per_image: 单图像超时时间
        """
        if batch_size is not None:
            self.batch_size = max(1, batch_size)
        if max_workers is not None:
            self.max_workers = max(1, max_workers)
        if timeout_per_image is not None:
            self.timeout_per_image = max(1.0, timeout_per_image)
        
        logger.info(f"批量处理配置已更新: batch_size={self.batch_size}, "
                   f"max_workers={self.max_workers}, timeout={self.timeout_per_image}s")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'batch_size': self.batch_size,
            'max_workers': self.max_workers,
            'timeout_per_image': self.timeout_per_image
        }