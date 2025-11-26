"""
地址服务 - 地址验证和区块链浏览器链接

提供 TRON 地址相关的业务逻辑服务。
"""
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import logging

from ..legacy.address_query.validator import AddressValidator
from ..legacy.address_query.explorer import explorer_links, get_tronscan_link
from ..database import SessionLocal, AddressQueryLog
from ..common.settings_service import get_address_cooldown_minutes

logger = logging.getLogger(__name__)


class AddressService:
    """地址服务类"""
    
    def __init__(self):
        """初始化地址服务"""
        self._validator = AddressValidator()
    
    def validate_address(self, address: str) -> Tuple[bool, Optional[str]]:
        """
        验证 TRON 地址格式
        
        Args:
            address: 待验证的地址
            
        Returns:
            (是否有效, 错误消息)
        """
        return self._validator.validate(address)
    
    def is_valid_address(self, address: str) -> bool:
        """
        检查地址是否有效（简化版）
        
        Args:
            address: 待验证的地址
            
        Returns:
            是否有效
        """
        is_valid, _ = self.validate_address(address)
        return is_valid
    
    def get_explorer_links(self, address: str) -> Dict[str, str]:
        """
        获取区块链浏览器链接
        
        Args:
            address: TRON 地址
            
        Returns:
            包含 overview 和 txs 链接的字典
        """
        return explorer_links(address)
    
    def get_tronscan_link(self, address: str) -> str:
        """
        获取 TronScan 地址链接
        
        Args:
            address: TRON 地址
            
        Returns:
            TronScan 链接
        """
        return get_tronscan_link(address)
    
    def check_rate_limit(self, user_id: int) -> Tuple[bool, int]:
        """
        检查用户查询限频
        
        Args:
            user_id: 用户 ID
            
        Returns:
            (是否可以查询, 剩余等待分钟数)
        """
        cooldown_minutes = get_address_cooldown_minutes()
        
        try:
            db = SessionLocal()
            last_query = db.query(AddressQueryLog).filter_by(
                user_id=user_id
            ).order_by(
                AddressQueryLog.last_query_at.desc()
            ).first()
            
            if last_query and last_query.last_query_at:
                time_since_last = datetime.now() - last_query.last_query_at
                if time_since_last < timedelta(minutes=cooldown_minutes):
                    remaining = cooldown_minutes - int(time_since_last.total_seconds() / 60)
                    return False, remaining
            
            return True, 0
            
        except Exception as e:
            logger.error(f"检查限频失败: {e}")
            return True, 0  # 出错时允许查询
        finally:
            db.close()
    
    def record_query(self, user_id: int, address: str) -> bool:
        """
        记录查询日志
        
        Args:
            user_id: 用户 ID
            address: 查询的地址
            
        Returns:
            是否记录成功
        """
        try:
            db = SessionLocal()
            
            # 查找现有记录
            log = db.query(AddressQueryLog).filter_by(user_id=user_id).first()
            
            if log:
                log.address = address
                log.last_query_at = datetime.now()
            else:
                log = AddressQueryLog(
                    user_id=user_id,
                    address=address,
                    last_query_at=datetime.now()
                )
                db.add(log)
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"记录查询日志失败: {e}")
            return False
        finally:
            db.close()


# 全局服务实例（可选）
address_service = AddressService()
