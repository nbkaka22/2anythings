"""性能监控模块

提供性能监控装饰器，用于跟踪函数执行时间、内存使用和GPU状态。
"""

import time
import functools
import psutil
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

def monitor_performance(track_memory: bool = False, track_gpu: bool = False):
    """性能监控装饰器
    
    Args:
        track_memory: 是否跟踪内存使用
        track_gpu: 是否跟踪GPU状态
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            start_memory = None
            gpu_info_start = None
            
            # 记录开始状态
            if track_memory:
                try:
                    process = psutil.Process()
                    start_memory = process.memory_info().rss / 1024 / 1024  # MB
                except Exception as e:
                    logger.warning(f"无法获取内存信息: {e}")
            
            if track_gpu:
                gpu_info_start = _get_gpu_info()
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录结束状态
                end_time = time.time()
                execution_time = end_time - start_time
                
                # 内存使用情况
                memory_info = ""
                if track_memory and start_memory is not None:
                    try:
                        process = psutil.Process()
                        end_memory = process.memory_info().rss / 1024 / 1024  # MB
                        memory_diff = end_memory - start_memory
                        memory_info = f", 内存: {start_memory:.1f}MB -> {end_memory:.1f}MB ({memory_diff:+.1f}MB)"
                    except Exception as e:
                        logger.warning(f"无法获取结束内存信息: {e}")
                
                # GPU信息
                gpu_info = ""
                if track_gpu and gpu_info_start:
                    gpu_info_end = _get_gpu_info()
                    if gpu_info_end:
                        gpu_info = f", GPU: {gpu_info_end}"
                
                logger.info(f"[性能] {func.__name__} 执行时间: {execution_time:.2f}秒{memory_info}{gpu_info}")
                
                return result
                
            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time
                logger.error(f"[性能] {func.__name__} 执行失败，耗时: {execution_time:.2f}秒，错误: {e}")
                raise
        
        return wrapper
    return decorator

def _get_gpu_info() -> Optional[str]:
    """获取GPU信息
    
    Returns:
        GPU信息字符串，如果无法获取则返回None
    """
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]  # 使用第一个GPU
            return f"使用率: {gpu.load*100:.1f}%, 内存: {gpu.memoryUsed}MB/{gpu.memoryTotal}MB"
    except ImportError:
        # GPUtil未安装，尝试使用nvidia-ml-py
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            return f"使用率: {util.gpu}%, 内存: {info.used//1024//1024}MB/{info.total//1024//1024}MB"
        except (ImportError, Exception):
            pass
    except Exception as e:
        logger.debug(f"获取GPU信息失败: {e}")
    
    return None

def log_system_info():
    """记录系统信息"""
    try:
        # CPU信息
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存信息
        memory = psutil.virtual_memory()
        memory_total = memory.total / 1024 / 1024 / 1024  # GB
        memory_available = memory.available / 1024 / 1024 / 1024  # GB
        memory_percent = memory.percent
        
        # 磁盘信息
        disk = psutil.disk_usage('/')
        disk_total = disk.total / 1024 / 1024 / 1024  # GB
        disk_free = disk.free / 1024 / 1024 / 1024  # GB
        disk_percent = disk.percent
        
        logger.info(f"[系统] CPU: {cpu_count}核 {cpu_percent}%, "
                   f"内存: {memory_available:.1f}GB/{memory_total:.1f}GB ({memory_percent}%), "
                   f"磁盘: {disk_free:.1f}GB/{disk_total:.1f}GB ({disk_percent}%)")
        
        # GPU信息
        gpu_info = _get_gpu_info()
        if gpu_info:
            logger.info(f"[系统] GPU: {gpu_info}")
        else:
            logger.info("[系统] GPU: 未检测到或无法访问")
            
    except Exception as e:
        logger.warning(f"获取系统信息失败: {e}")

class PerformanceTracker:
    """性能跟踪器
    
    用于手动跟踪性能指标
    """
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
        self.start_memory = None
        
    def start(self):
        """开始跟踪"""
        self.start_time = time.time()
        try:
            process = psutil.Process()
            self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
        except Exception:
            self.start_memory = None
    
    def stop(self) -> dict:
        """停止跟踪并返回结果
        
        Returns:
            包含性能指标的字典
        """
        if self.start_time is None:
            raise ValueError("必须先调用 start() 方法")
        
        end_time = time.time()
        execution_time = end_time - self.start_time
        
        result = {
            'name': self.name,
            'execution_time': execution_time
        }
        
        # 内存使用情况
        if self.start_memory is not None:
            try:
                process = psutil.Process()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                result['start_memory'] = self.start_memory
                result['end_memory'] = end_memory
                result['memory_diff'] = end_memory - self.start_memory
            except Exception:
                pass
        
        logger.info(f"[性能跟踪] {self.name}: {execution_time:.2f}秒")
        
        return result