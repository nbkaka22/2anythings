"""重试管理模块

提供重试装饰器和熔断器，用于处理OCR操作的失败重试。
"""

import time
import functools
import logging
from typing import Callable, Any, Tuple, Type, Optional
from threading import Lock

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """熔断器
    
    当失败次数超过阈值时，暂时停止调用，避免系统过载。
    """
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: float = 60.0,
                 expected_exception: Tuple[Type[Exception], ...] = (Exception,)):
        """初始化熔断器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
            expected_exception: 预期的异常类型
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self.lock = Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """通过熔断器调用函数
        
        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数返回值
            
        Raises:
            CircuitBreakerOpenException: 熔断器开启时
        """
        with self.lock:
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                    logger.info("熔断器进入半开状态")
                else:
                    raise CircuitBreakerOpenException("熔断器开启，拒绝调用")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置熔断器"""
        return (self.last_failure_time is not None and 
                time.time() - self.last_failure_time >= self.recovery_timeout)
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        if self.state == 'HALF_OPEN':
            self.state = 'CLOSED'
            logger.info("熔断器重置为关闭状态")
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(f"熔断器开启，失败次数: {self.failure_count}")
    
    def reset(self):
        """手动重置熔断器"""
        with self.lock:
            self.failure_count = 0
            self.last_failure_time = None
            self.state = 'CLOSED'
            logger.info("熔断器已手动重置")
    
    def get_state(self) -> dict:
        """获取熔断器状态"""
        with self.lock:
            return {
                'state': self.state,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'last_failure_time': self.last_failure_time,
                'recovery_timeout': self.recovery_timeout
            }

class CircuitBreakerOpenException(Exception):
    """熔断器开启异常"""
    pass

def retry_ocr_init(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """OCR初始化重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (RuntimeError, ImportError, OSError, Exception) as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(f"OCR初始化失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                        logger.info(f"等待 {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"OCR初始化最终失败，已尝试 {max_retries + 1} 次: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator

def retry_file_processing(max_retries: int = 2, delay: float = 0.5, backoff: float = 1.5):
    """文件处理重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (IOError, OSError, RuntimeError) as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(f"文件处理失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                        logger.info(f"等待 {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"文件处理最终失败，已尝试 {max_retries + 1} 次: {e}")
                except Exception as e:
                    # 对于其他类型的异常，不重试
                    logger.error(f"文件处理遇到不可重试的错误: {e}")
                    raise
            
            raise last_exception
        
        return wrapper
    return decorator

def retry_with_circuit_breaker(circuit_breaker: CircuitBreaker, 
                              max_retries: int = 3, 
                              delay: float = 1.0, 
                              backoff: float = 2.0):
    """带熔断器的重试装饰器
    
    Args:
        circuit_breaker: 熔断器实例
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return circuit_breaker.call(func, *args, **kwargs)
                except CircuitBreakerOpenException:
                    logger.error("熔断器开启，停止重试")
                    raise
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(f"操作失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}")
                        logger.info(f"等待 {current_delay:.1f} 秒后重试...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"操作最终失败，已尝试 {max_retries + 1} 次: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator

class RetryManager:
    """重试管理器
    
    提供更灵活的重试控制
    """
    
    def __init__(self, max_retries: int = 3, 
                 base_delay: float = 1.0, 
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0,
                 jitter: bool = True):
        """初始化重试管理器
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟时间
            max_delay: 最大延迟时间
            backoff_factor: 退避因子
            jitter: 是否添加随机抖动
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """执行带重试的函数调用
        
        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数返回值
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"操作失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                    logger.info(f"等待 {delay:.1f} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"操作最终失败，已尝试 {self.max_retries + 1} 次: {e}")
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """计算延迟时间
        
        Args:
            attempt: 当前尝试次数
            
        Returns:
            延迟时间（秒）
        """
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            # 添加±25%的随机抖动
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)
        
        return delay