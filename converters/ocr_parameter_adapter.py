#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR参数适配器模块
用于适配不同版本的OCR引擎参数
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OCRParameterAdapter:
    """OCR参数适配器
    
    负责适配不同版本的OCR引擎参数，确保兼容性
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # PaddleOCR版本兼容性映射
        self.paddleocr_version_compatibility = {
            '2.6.0': {
                'supports_gpu_available': True,
                'supports_use_gpu': True,
                'supports_device': False,
                'default_params': {
                    'use_angle_cls': True,
                    'lang': 'ch'
                }
            },
            '2.7.0': {
                'supports_gpu_available': False,
                'supports_use_gpu': True,
                'supports_device': True,
                'default_params': {
                    'use_angle_cls': True,
                    'lang': 'ch'
                }
            },
            '3.0.2': {
                'supports_gpu_available': False,
                'supports_use_gpu': False,
                'supports_device': True,
                'default_params': {
                    'use_textline_orientation': True,
                    'lang': 'ch'
                }
            },
            'default': {
                'supports_gpu_available': False,
                'supports_use_gpu': False,
                'supports_device': True,
                'default_params': {
                    'use_textline_orientation': True,
                    'lang': 'ch'
                }
            }
        }
    
    def adapt_paddleocr_parameters(self, base_params: Dict[str, Any], 
                                 version: str, gpu_available: bool) -> Dict[str, Any]:
        """适配PaddleOCR参数
        
        Args:
            base_params: 基础参数
            version: PaddleOCR版本
            gpu_available: GPU是否可用
            
        Returns:
            Dict[str, Any]: 适配后的参数
        """
        # 获取版本兼容性信息
        version_info = self.paddleocr_version_compatibility.get(
            version, self.paddleocr_version_compatibility['default']
        )
        
        # 从默认参数开始
        adapted_params = version_info['default_params'].copy()
        
        # 添加基础参数
        for key, value in base_params.items():
            if key != 'gpu_available':  # 特殊处理GPU参数
                adapted_params[key] = value
        
        # 处理GPU相关参数
        if gpu_available:
            if version_info['supports_gpu_available']:
                adapted_params['gpu_available'] = True
            elif version_info['supports_use_gpu']:
                adapted_params['use_gpu'] = True
            
            if version_info['supports_device']:
                adapted_params['device'] = 'gpu'
        else:
            if version_info['supports_gpu_available']:
                adapted_params['gpu_available'] = False
            elif version_info['supports_use_gpu']:
                adapted_params['use_gpu'] = False
            
            if version_info['supports_device']:
                adapted_params['device'] = 'cpu'
        
        self.logger.debug(f"适配PaddleOCR v{version}参数: {adapted_params}")
        return adapted_params
    
    def adapt_easyocr_parameters(self, languages: list, gpu_available: bool) -> Dict[str, Any]:
        """适配EasyOCR参数
        
        Args:
            languages: 支持的语言列表
            gpu_available: GPU是否可用
            
        Returns:
            Dict[str, Any]: 适配后的参数
        """
        params = {
            'lang_list': languages,
            'gpu': gpu_available
        }
        
        self.logger.debug(f"适配EasyOCR参数: {params}")
        return params
    
    def get_optimal_batch_size(self, gpu_available: bool, image_size: tuple) -> int:
        """获取最优批处理大小
        
        Args:
            gpu_available: GPU是否可用
            image_size: 图像尺寸 (width, height)
            
        Returns:
            int: 最优批处理大小
        """
        if not gpu_available:
            return 1
        
        # 根据图像尺寸计算最优批处理大小
        width, height = image_size
        pixels = width * height
        
        if pixels > 2048 * 2048:  # 大图像
            return 1
        elif pixels > 1024 * 1024:  # 中等图像
            return 2
        else:  # 小图像
            return 4
    
    def get_memory_optimization_params(self, available_memory_gb: float) -> Dict[str, Any]:
        """获取内存优化参数
        
        Args:
            available_memory_gb: 可用内存（GB）
            
        Returns:
            Dict[str, Any]: 内存优化参数
        """
        params = {}
        
        if available_memory_gb < 2.0:
            # 低内存模式
            params.update({
                'max_batch_size': 1,
                'enable_memory_cleanup': True,
                'force_cpu_fallback': True
            })
        elif available_memory_gb < 4.0:
            # 中等内存模式
            params.update({
                'max_batch_size': 2,
                'enable_memory_cleanup': True,
                'force_cpu_fallback': False
            })
        else:
            # 高内存模式
            params.update({
                'max_batch_size': 4,
                'enable_memory_cleanup': False,
                'force_cpu_fallback': False
            })
        
        self.logger.debug(f"内存优化参数 (可用: {available_memory_gb:.1f}GB): {params}")
        return params
    
    def validate_parameters(self, params: Dict[str, Any], engine: str) -> bool:
        """验证参数有效性
        
        Args:
            params: 参数字典
            engine: OCR引擎名称 ('paddle' 或 'easy')
            
        Returns:
            bool: 参数是否有效
        """
        try:
            if engine == 'paddle':
                # 验证PaddleOCR参数
                required_keys = ['lang']
                for key in required_keys:
                    if key not in params:
                        self.logger.warning(f"PaddleOCR缺少必需参数: {key}")
                        return False
                        
            elif engine == 'easy':
                # 验证EasyOCR参数
                if 'lang_list' not in params:
                    self.logger.warning("EasyOCR缺少必需参数: lang_list")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"参数验证失败: {e}")
            return False
    
    def get_fallback_parameters(self, engine: str) -> Dict[str, Any]:
        """获取回退参数
        
        Args:
            engine: OCR引擎名称
            
        Returns:
            Dict[str, Any]: 回退参数
        """
        if engine == 'paddle':
            return {
                'use_textline_orientation': True,
                'lang': 'ch',
                'device': 'cpu'
            }
        elif engine == 'easy':
            return {
                'lang_list': ['ch_sim', 'en'],
                'gpu': False
            }
        else:
            return {}