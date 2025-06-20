"""配置验证模块

提供配置文件的验证、修复和保存功能。
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigValidator:
    """配置验证器
    
    负责验证、修复和保存配置文件。
    """
    
    def __init__(self):
        """初始化配置验证器"""
        self.default_config = {
            "gpu_memory_limit": 4096,
            "cpu_threads": 4,
            "batch_size": 5,
            "max_image_size": 2048,
            "ocr_confidence_threshold": 0.6,
            "enable_gpu": True,
            "fallback_to_cpu": True,
            "cache_enabled": True,
            "cache_size_mb": 512,
            "timeout_seconds": 300,
            "retry_attempts": 3,
            "log_level": "INFO"
        }
        
        self.validation_rules = {
            "gpu_memory_limit": {"type": int, "min": 512, "max": 32768},
            "cpu_threads": {"type": int, "min": 1, "max": 32},
            "batch_size": {"type": int, "min": 1, "max": 20},
            "max_image_size": {"type": int, "min": 512, "max": 4096},
            "ocr_confidence_threshold": {"type": float, "min": 0.0, "max": 1.0},
            "enable_gpu": {"type": bool},
            "fallback_to_cpu": {"type": bool},
            "cache_enabled": {"type": bool},
            "cache_size_mb": {"type": int, "min": 64, "max": 2048},
            "timeout_seconds": {"type": int, "min": 30, "max": 3600},
            "retry_attempts": {"type": int, "min": 1, "max": 10},
            "log_level": {"type": str, "choices": ["DEBUG", "INFO", "WARNING", "ERROR"]}
        }
    
    def validate_gpu_memory_config(self, config_path: str) -> Dict[str, Any]:
        """验证GPU内存配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            验证结果字典
        """
        try:
            # 加载配置
            config = self._load_config(config_path)
            
            # 验证结果
            validation_result = {
                'valid': True,
                'issues': [],
                'warnings': [],
                'config': config
            }
            
            # 检查GPU内存配置
            gpu_memory = config.get('gpu_memory_limit', self.default_config['gpu_memory_limit'])
            
            if not isinstance(gpu_memory, int):
                validation_result['issues'].append({
                    'field': 'gpu_memory_limit',
                    'issue': 'GPU内存限制必须是整数',
                    'current_value': gpu_memory,
                    'suggested_value': self.default_config['gpu_memory_limit']
                })
                validation_result['valid'] = False
            elif gpu_memory < 512:
                validation_result['warnings'].append({
                    'field': 'gpu_memory_limit',
                    'warning': 'GPU内存限制过低，可能影响性能',
                    'current_value': gpu_memory,
                    'suggested_value': 2048
                })
            elif gpu_memory > 16384:
                validation_result['warnings'].append({
                    'field': 'gpu_memory_limit',
                    'warning': 'GPU内存限制过高，可能超出硬件限制',
                    'current_value': gpu_memory,
                    'suggested_value': 8192
                })
            
            # 检查其他关键配置
            self._validate_all_fields(config, validation_result)
            
            logger.info(f"配置验证完成: {len(validation_result['issues'])} 个问题, {len(validation_result['warnings'])} 个警告")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return {
                'valid': False,
                'issues': [{
                    'field': 'general',
                    'issue': f'配置验证失败: {e}',
                    'current_value': None,
                    'suggested_value': None
                }],
                'warnings': [],
                'config': self.default_config.copy()
            }
    
    def _validate_all_fields(self, config: Dict[str, Any], validation_result: Dict[str, Any]):
        """验证所有配置字段
        
        Args:
            config: 配置字典
            validation_result: 验证结果字典
        """
        for field, rules in self.validation_rules.items():
            if field == 'gpu_memory_limit':  # 已经单独验证过
                continue
                
            value = config.get(field)
            
            # 检查字段是否存在
            if value is None:
                validation_result['issues'].append({
                    'field': field,
                    'issue': f'缺少必需的配置字段: {field}',
                    'current_value': None,
                    'suggested_value': self.default_config.get(field)
                })
                validation_result['valid'] = False
                continue
            
            # 检查类型
            expected_type = rules['type']
            if not isinstance(value, expected_type):
                validation_result['issues'].append({
                    'field': field,
                    'issue': f'字段类型错误，期望 {expected_type.__name__}',
                    'current_value': value,
                    'suggested_value': self.default_config.get(field)
                })
                validation_result['valid'] = False
                continue
            
            # 检查数值范围
            if expected_type in (int, float):
                if 'min' in rules and value < rules['min']:
                    validation_result['issues'].append({
                        'field': field,
                        'issue': f'值过小，最小值为 {rules["min"]}',
                        'current_value': value,
                        'suggested_value': rules['min']
                    })
                    validation_result['valid'] = False
                elif 'max' in rules and value > rules['max']:
                    validation_result['issues'].append({
                        'field': field,
                        'issue': f'值过大，最大值为 {rules["max"]}',
                        'current_value': value,
                        'suggested_value': rules['max']
                    })
                    validation_result['valid'] = False
            
            # 检查选择项
            if 'choices' in rules and value not in rules['choices']:
                validation_result['issues'].append({
                    'field': field,
                    'issue': f'无效的选择，可选值: {rules["choices"]}',
                    'current_value': value,
                    'suggested_value': rules['choices'][0]
                })
                validation_result['valid'] = False
    
    def fix_config_issues(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """修复配置问题
        
        Args:
            config: 原始配置
            
        Returns:
            修复后的配置
        """
        fixed_config = config.copy()
        
        try:
            # 验证并修复每个字段
            for field, rules in self.validation_rules.items():
                value = fixed_config.get(field)
                default_value = self.default_config.get(field)
                
                # 如果字段不存在，使用默认值
                if value is None:
                    fixed_config[field] = default_value
                    logger.info(f"添加缺失字段 {field}: {default_value}")
                    continue
                
                # 检查并修复类型
                expected_type = rules['type']
                if not isinstance(value, expected_type):
                    fixed_config[field] = default_value
                    logger.info(f"修复字段类型 {field}: {value} -> {default_value}")
                    continue
                
                # 修复数值范围
                if expected_type in (int, float):
                    if 'min' in rules and value < rules['min']:
                        fixed_config[field] = rules['min']
                        logger.info(f"修复字段最小值 {field}: {value} -> {rules['min']}")
                    elif 'max' in rules and value > rules['max']:
                        fixed_config[field] = rules['max']
                        logger.info(f"修复字段最大值 {field}: {value} -> {rules['max']}")
                
                # 修复选择项
                if 'choices' in rules and value not in rules['choices']:
                    fixed_config[field] = rules['choices'][0]
                    logger.info(f"修复字段选择 {field}: {value} -> {rules['choices'][0]}")
            
            logger.info("配置修复完成")
            return fixed_config
            
        except Exception as e:
            logger.error(f"配置修复失败: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any], config_path: str) -> bool:
        """保存配置到文件
        
        Args:
            config: 配置字典
            config_path: 配置文件路径
            
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            config_dir = os.path.dirname(config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已保存到: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"配置已从 {config_path} 加载")
                return config
            else:
                logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
                return self.default_config.copy()
                
        except Exception as e:
            logger.error(f"加载配置失败: {e}，使用默认配置")
            return self.default_config.copy()
    
    def create_default_config(self, config_path: str) -> bool:
        """创建默认配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            是否创建成功
        """
        try:
            return self.save_config(self.default_config, config_path)
        except Exception as e:
            logger.error(f"创建默认配置失败: {e}")
            return False
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置
        
        Returns:
            默认配置字典
        """
        return self.default_config.copy()
    
    def validate_config_file(self, config_path: str) -> bool:
        """验证配置文件是否有效
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置是否有效
        """
        try:
            validation_result = self.validate_gpu_memory_config(config_path)
            return validation_result['valid']
        except Exception as e:
            logger.error(f"配置文件验证失败: {e}")
            return False

# 创建全局实例
config_validator = ConfigValidator()