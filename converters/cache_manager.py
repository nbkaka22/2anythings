#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存管理模块
提供OCR结果缓存和内存管理功能
"""

import os
import json
import hashlib
import logging
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """缓存统计信息"""
    total_entries: int = 0
    total_size_mb: float = 0.0
    hit_count: int = 0
    miss_count: int = 0
    hit_rate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_entries': self.total_entries,
            'total_size_mb': self.total_size_mb,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': self.hit_rate
        }


class CacheManager:
    """缓存管理器
    
    提供OCR结果缓存、内存管理和性能优化功能
    """
    
    def __init__(self, cache_dir: Optional[str] = None, max_cache_size_mb: int = 500):
        # 缓存目录
        if cache_dir is None:
            self.cache_dir = Path(tempfile.gettempdir()) / "pdf_converter_cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        self.cache_dir.mkdir(exist_ok=True)
        
        # 配置
        self.max_cache_size_mb = max_cache_size_mb
        self.max_entries = 1000
        self.cleanup_threshold = 0.8  # 当缓存达到80%时开始清理
        
        # 统计信息
        self.stats = CacheStats()
        
        # 内存缓存（用于频繁访问的小数据）
        self._memory_cache: Dict[str, Any] = {}
        self._access_times: Dict[str, float] = {}
        
        # 初始化
        self._load_stats()
        
    def _generate_cache_key(self, data: Any) -> str:
        """生成缓存键
        
        Args:
            data: 要缓存的数据
            
        Returns:
            str: 缓存键
        """
        if isinstance(data, (str, bytes)):
            content = data if isinstance(data, bytes) else data.encode('utf-8')
        else:
            content = str(data).encode('utf-8')
        
        return hashlib.md5(content).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """获取缓存文件路径
        
        Args:
            cache_key: 缓存键
            
        Returns:
            Path: 缓存文件路径
        """
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_stats(self):
        """加载缓存统计信息"""
        stats_file = self.cache_dir / "cache_stats.json"
        try:
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats_data = json.load(f)
                    self.stats = CacheStats(**stats_data)
        except Exception as e:
            logger.warning(f"加载缓存统计失败: {e}")
            self.stats = CacheStats()
    
    def _save_stats(self):
        """保存缓存统计信息"""
        stats_file = self.cache_dir / "cache_stats.json"
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"保存缓存统计失败: {e}")
    
    def _update_hit_rate(self):
        """更新命中率"""
        total_requests = self.stats.hit_count + self.stats.miss_count
        if total_requests > 0:
            self.stats.hit_rate = self.stats.hit_count / total_requests
        else:
            self.stats.hit_rate = 0.0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            Optional[Any]: 缓存的数据，如果不存在则返回None
        """
        # 先检查内存缓存
        if key in self._memory_cache:
            self._access_times[key] = time.time()
            self.stats.hit_count += 1
            self._update_hit_rate()
            return self._memory_cache[key]
        
        # 检查文件缓存
        cache_file = self._get_cache_file_path(key)
        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 更新访问时间
                self._access_times[key] = time.time()
                
                # 如果数据较小，加载到内存缓存
                if len(str(data)) < 10240:  # 10KB以下
                    self._memory_cache[key] = data
                
                self.stats.hit_count += 1
                self._update_hit_rate()
                return data
        except Exception as e:
            logger.warning(f"读取缓存失败 {key}: {e}")
        
        self.stats.miss_count += 1
        self._update_hit_rate()
        return None
    
    def set(self, key: str, value: Any, memory_only: bool = False) -> bool:
        """设置缓存数据
        
        Args:
            key: 缓存键
            value: 要缓存的数据
            memory_only: 是否只存储在内存中
            
        Returns:
            bool: 是否成功
        """
        try:
            # 更新访问时间
            self._access_times[key] = time.time()
            
            # 存储到内存缓存
            self._memory_cache[key] = value
            
            # 如果不是仅内存模式，也存储到文件
            if not memory_only:
                cache_file = self._get_cache_file_path(key)
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(value, f, ensure_ascii=False, indent=2)
                
                # 更新统计
                self.stats.total_entries += 1
                file_size = cache_file.stat().st_size / (1024 * 1024)  # MB
                self.stats.total_size_mb += file_size
            
            # 检查是否需要清理
            if self.stats.total_size_mb > self.max_cache_size_mb * self.cleanup_threshold:
                self._cleanup_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            bool: 是否成功
        """
        try:
            # 从内存缓存删除
            if key in self._memory_cache:
                del self._memory_cache[key]
            
            if key in self._access_times:
                del self._access_times[key]
            
            # 从文件缓存删除
            cache_file = self._get_cache_file_path(key)
            if cache_file.exists():
                file_size = cache_file.stat().st_size / (1024 * 1024)  # MB
                cache_file.unlink()
                
                # 更新统计
                self.stats.total_entries = max(0, self.stats.total_entries - 1)
                self.stats.total_size_mb = max(0, self.stats.total_size_mb - file_size)
            
            return True
            
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False
    
    def _cleanup_cache(self):
        """清理缓存"""
        try:
            # 获取所有缓存文件
            cache_files = list(self.cache_dir.glob("*.json"))
            if not cache_files:
                return
            
            # 按访问时间排序（最久未访问的在前）
            cache_files.sort(key=lambda f: self._access_times.get(f.stem, 0))
            
            # 删除最久未访问的文件，直到缓存大小降到阈值以下
            target_size = self.max_cache_size_mb * 0.6  # 清理到60%
            
            for cache_file in cache_files:
                if self.stats.total_size_mb <= target_size:
                    break
                
                key = cache_file.stem
                self.delete(key)
            
            logger.info(f"缓存清理完成，当前大小: {self.stats.total_size_mb:.2f}MB")
            
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")
    
    def clear_all(self) -> bool:
        """清空所有缓存
        
        Returns:
            bool: 是否成功
        """
        try:
            # 清空内存缓存
            self._memory_cache.clear()
            self._access_times.clear()
            
            # 删除所有缓存文件
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name != "cache_stats.json":
                    cache_file.unlink()
            
            # 重置统计
            self.stats = CacheStats()
            self._save_stats()
            
            logger.info("所有缓存已清空")
            return True
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 更新当前大小
        current_size = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name != "cache_stats.json":
                    current_size += cache_file.stat().st_size
            self.stats.total_size_mb = current_size / (1024 * 1024)
        except Exception as e:
            logger.warning(f"计算缓存大小失败: {e}")
        
        stats = self.stats.to_dict()
        stats.update({
            'memory_cache_entries': len(self._memory_cache),
            'max_cache_size_mb': self.max_cache_size_mb,
            'cache_dir': str(self.cache_dir)
        })
        
        return stats
    
    def optimize_cache(self) -> Dict[str, Any]:
        """优化缓存
        
        Returns:
            Dict[str, Any]: 优化结果
        """
        try:
            initial_size = self.stats.total_size_mb
            initial_entries = self.stats.total_entries
            
            # 清理过期和无效的缓存
            self._cleanup_cache()
            
            # 保存统计信息
            self._save_stats()
            
            final_size = self.stats.total_size_mb
            final_entries = self.stats.total_entries
            
            result = {
                'success': True,
                'initial_size_mb': initial_size,
                'final_size_mb': final_size,
                'size_reduced_mb': initial_size - final_size,
                'initial_entries': initial_entries,
                'final_entries': final_entries,
                'entries_removed': initial_entries - final_entries
            }
            
            logger.info(f"缓存优化完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"缓存优化失败: {e}")
            return {'success': False, 'error': str(e)}


# 全局缓存管理器实例
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例
    
    Returns:
        CacheManager: 缓存管理器实例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# 导出全局实例
cache_manager = get_cache_manager()