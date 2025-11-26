"""
错误收集器
用于收集和分析生产环境中的错误
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json
import traceback

logger = logging.getLogger(__name__)


class ErrorCollector:
    """错误收集器"""
    
    def __init__(self, max_errors: int = 100, auto_save_interval: int = 300):
        """
        初始化错误收集器
        
        Args:
            max_errors: 最大保存错误数
            auto_save_interval: 自动保存间隔（秒）
        """
        self.errors: List[Dict[str, Any]] = []
        self.max_errors = max_errors
        self.auto_save_interval = auto_save_interval
        self.error_counts = defaultdict(int)  # 错误类型计数
        self.last_save_time = datetime.now()
        
    def collect(self, 
                error_type: str, 
                message: str, 
                context: Optional[Dict] = None,
                exception: Optional[Exception] = None) -> None:
        """
        收集错误
        
        Args:
            error_type: 错误类型
            message: 错误消息
            context: 上下文信息
            exception: 异常对象
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": message,
            "context": context or {}
        }
        
        # 如果有异常对象，记录堆栈
        if exception:
            error_info["traceback"] = traceback.format_exc()
            error_info["exception_class"] = type(exception).__name__
        
        # 添加到错误列表
        self.errors.append(error_info)
        
        # 更新错误计数
        self.error_counts[error_type] += 1
        
        # 限制错误数量
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
        
        # 记录到日志
        logger.error(f"[{error_type}] {message}")
        
        # 检查是否需要自动保存
        if (datetime.now() - self.last_save_time).seconds > self.auto_save_interval:
            self.save_to_file()
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取错误摘要
        
        Returns:
            错误摘要信息
        """
        if not self.errors:
            return {
                "total": 0,
                "types": {},
                "recent": [],
                "status": "healthy"
            }
        
        # 计算时间范围
        oldest_error = datetime.fromisoformat(self.errors[0]["timestamp"])
        newest_error = datetime.fromisoformat(self.errors[-1]["timestamp"])
        time_range = newest_error - oldest_error
        
        # 计算错误率
        error_rate = len(self.errors) / max(time_range.total_seconds() / 3600, 1)  # 每小时错误数
        
        # 判断健康状态
        if error_rate > 10:
            status = "critical"
        elif error_rate > 5:
            status = "warning"
        else:
            status = "normal"
        
        return {
            "total": len(self.errors),
            "types": dict(self.error_counts),
            "recent": self.errors[-10:],  # 最近10个错误
            "error_rate": round(error_rate, 2),
            "time_range": str(time_range),
            "status": status,
            "most_common": self._get_most_common_errors()
        }
    
    def _get_most_common_errors(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        获取最常见的错误
        
        Args:
            top_n: 返回前N个
            
        Returns:
            最常见错误列表
        """
        sorted_errors = sorted(
            self.error_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return [
            {"type": error_type, "count": count}
            for error_type, count in sorted_errors[:top_n]
        ]
    
    def get_errors_by_type(self, error_type: str) -> List[Dict[str, Any]]:
        """
        获取特定类型的错误
        
        Args:
            error_type: 错误类型
            
        Returns:
            错误列表
        """
        return [
            error for error in self.errors
            if error["type"] == error_type
        ]
    
    def get_errors_in_timerange(self, 
                                hours: int = 1) -> List[Dict[str, Any]]:
        """
        获取指定时间范围内的错误
        
        Args:
            hours: 小时数
            
        Returns:
            错误列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            error for error in self.errors
            if datetime.fromisoformat(error["timestamp"]) > cutoff_time
        ]
    
    def clear_old_errors(self, days: int = 7) -> int:
        """
        清理旧错误
        
        Args:
            days: 保留天数
            
        Returns:
            清理的错误数
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        original_count = len(self.errors)
        
        self.errors = [
            error for error in self.errors
            if datetime.fromisoformat(error["timestamp"]) > cutoff_time
        ]
        
        removed_count = original_count - len(self.errors)
        if removed_count > 0:
            logger.info(f"Cleared {removed_count} old errors")
        
        return removed_count
    
    def save_to_file(self, filename: str = "error_log.json") -> bool:
        """
        保存错误到文件
        
        Args:
            filename: 文件名
            
        Returns:
            是否成功
        """
        try:
            from pathlib import Path
            
            # 创建logs目录
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # 保存文件
            filepath = log_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "summary": self.get_summary(),
                    "errors": self.errors
                }, f, ensure_ascii=False, indent=2)
            
            self.last_save_time = datetime.now()
            logger.info(f"Errors saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save errors: {e}")
            return False
    
    def load_from_file(self, filename: str = "error_log.json") -> bool:
        """
        从文件加载错误
        
        Args:
            filename: 文件名
            
        Returns:
            是否成功
        """
        try:
            from pathlib import Path
            
            filepath = Path("logs") / filename
            if not filepath.exists():
                return False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.errors = data.get("errors", [])
            
            # 重建错误计数
            self.error_counts.clear()
            for error in self.errors:
                self.error_counts[error["type"]] += 1
            
            logger.info(f"Loaded {len(self.errors)} errors from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load errors: {e}")
            return False


# 全局错误收集器实例
error_collector = ErrorCollector()


def collect_error(error_type: str, 
                 message: str, 
                 context: Optional[Dict] = None,
                 exception: Optional[Exception] = None) -> None:
    """
    便捷函数：收集错误到全局收集器
    
    Args:
        error_type: 错误类型
        message: 错误消息
        context: 上下文信息
        exception: 异常对象
    """
    error_collector.collect(error_type, message, context, exception)
