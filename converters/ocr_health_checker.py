"""OCR健康检查器模块

提供OCR系统的健康监控和状态检查功能。
"""

import time
import threading
from typing import Dict, List, Any
from collections import deque
import logging

logger = logging.getLogger(__name__)

class OCRHealthChecker:
    """OCR健康检查器
    
    监控OCR操作的成功率、响应时间等指标，
    提供系统健康状态评估。
    """
    
    def __init__(self, max_history: int = 100):
        """初始化健康检查器
        
        Args:
            max_history: 保留的历史记录数量
        """
        self.max_history = max_history
        self.operation_history = deque(maxlen=max_history)
        self.start_time = time.time()
        self.monitoring_active = False
        self.lock = threading.Lock()
        
        # 统计数据
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.total_response_time = 0.0
        
    def start_monitoring(self):
        """开始监控"""
        with self.lock:
            self.monitoring_active = True
            self.start_time = time.time()
            logger.info("OCR健康监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        with self.lock:
            self.monitoring_active = False
            logger.info("OCR健康监控已停止")
    
    def update_stats(self, response_time: float, success: bool):
        """更新统计数据
        
        Args:
            response_time: 响应时间（秒）
            success: 操作是否成功
        """
        if not self.monitoring_active:
            return
            
        with self.lock:
            # 记录操作
            operation_record = {
                'timestamp': time.time(),
                'response_time': response_time,
                'success': success
            }
            self.operation_history.append(operation_record)
            
            # 更新统计
            self.total_operations += 1
            self.total_response_time += response_time
            
            if success:
                self.successful_operations += 1
            else:
                self.failed_operations += 1
    
    def check_ocr_health(self) -> Dict[str, Any]:
        """检查OCR系统健康状态
        
        Returns:
            包含健康状态信息的字典
        """
        with self.lock:
            current_time = time.time()
            uptime = current_time - self.start_time
            
            # 计算成功率
            success_rate = 0.0
            if self.total_operations > 0:
                success_rate = self.successful_operations / self.total_operations
            
            # 计算平均响应时间
            avg_response_time = 0.0
            if self.total_operations > 0:
                avg_response_time = self.total_response_time / self.total_operations
            
            # 计算最近操作的成功率（最近10次）
            recent_success_rate = 0.0
            recent_operations = list(self.operation_history)[-10:]
            if recent_operations:
                recent_successes = sum(1 for op in recent_operations if op['success'])
                recent_success_rate = recent_successes / len(recent_operations)
            
            # 确定健康状态
            status = self._determine_health_status(
                success_rate, recent_success_rate, avg_response_time
            )
            
            # 生成警报
            alerts = self._generate_alerts(
                success_rate, recent_success_rate, avg_response_time
            )
            
            return {
                'status': status,
                'uptime': uptime,
                'total_operations': self.total_operations,
                'successful_operations': self.successful_operations,
                'failed_operations': self.failed_operations,
                'success_rate': success_rate,
                'recent_success_rate': recent_success_rate,
                'avg_response_time': avg_response_time,
                'alerts': alerts,
                'monitoring_active': self.monitoring_active
            }
    
    def _determine_health_status(self, success_rate: float, 
                               recent_success_rate: float, 
                               avg_response_time: float) -> str:
        """确定健康状态
        
        Args:
            success_rate: 总体成功率
            recent_success_rate: 最近成功率
            avg_response_time: 平均响应时间
            
        Returns:
            健康状态: 'healthy', 'warning', 'critical'
        """
        # 如果没有操作记录，认为是健康的
        if self.total_operations == 0:
            return 'healthy'
        
        # 严重状态：最近成功率很低或响应时间过长
        if recent_success_rate < 0.3 or avg_response_time > 30.0:
            return 'critical'
        
        # 警告状态：成功率较低或响应时间较长
        if success_rate < 0.7 or recent_success_rate < 0.6 or avg_response_time > 10.0:
            return 'warning'
        
        return 'healthy'
    
    def _generate_alerts(self, success_rate: float, 
                        recent_success_rate: float, 
                        avg_response_time: float) -> List[Dict[str, str]]:
        """生成警报信息
        
        Args:
            success_rate: 总体成功率
            recent_success_rate: 最近成功率
            avg_response_time: 平均响应时间
            
        Returns:
            警报列表
        """
        alerts = []
        
        if self.total_operations == 0:
            return alerts
        
        # 成功率警报
        if success_rate < 0.3:
            alerts.append({
                'level': 'critical',
                'type': 'success_rate',
                'message': f'总体成功率过低: {success_rate:.1%}'
            })
        elif success_rate < 0.7:
            alerts.append({
                'level': 'warning',
                'type': 'success_rate',
                'message': f'总体成功率较低: {success_rate:.1%}'
            })
        
        # 最近成功率警报
        if recent_success_rate < 0.3:
            alerts.append({
                'level': 'critical',
                'type': 'recent_success_rate',
                'message': f'最近成功率过低: {recent_success_rate:.1%}'
            })
        elif recent_success_rate < 0.6:
            alerts.append({
                'level': 'warning',
                'type': 'recent_success_rate',
                'message': f'最近成功率较低: {recent_success_rate:.1%}'
            })
        
        # 响应时间警报
        if avg_response_time > 30.0:
            alerts.append({
                'level': 'critical',
                'type': 'response_time',
                'message': f'平均响应时间过长: {avg_response_time:.1f}秒'
            })
        elif avg_response_time > 10.0:
            alerts.append({
                'level': 'warning',
                'type': 'response_time',
                'message': f'平均响应时间较长: {avg_response_time:.1f}秒'
            })
        
        return alerts
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取详细统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            return {
                'total_operations': self.total_operations,
                'successful_operations': self.successful_operations,
                'failed_operations': self.failed_operations,
                'success_rate': self.successful_operations / max(1, self.total_operations),
                'avg_response_time': self.total_response_time / max(1, self.total_operations),
                'uptime': time.time() - self.start_time,
                'monitoring_active': self.monitoring_active,
                'history_size': len(self.operation_history)
            }
    
    def reset_statistics(self):
        """重置统计数据"""
        with self.lock:
            self.operation_history.clear()
            self.total_operations = 0
            self.successful_operations = 0
            self.failed_operations = 0
            self.total_response_time = 0.0
            self.start_time = time.time()
            logger.info("OCR健康检查统计数据已重置")