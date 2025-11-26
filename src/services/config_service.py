"""
配置服务 - 动态配置管理

提供配置读取和更新的业务逻辑服务。
基于 common/settings_service.py + bot_admin/config_manager.py
"""
from typing import Optional, Any, Dict
import logging

from ..common.settings_service import (
    get_order_timeout_minutes,
    get_address_cooldown_minutes,
)
from ..database import SessionLocal

logger = logging.getLogger(__name__)


class ConfigService:
    """配置服务类"""
    
    def __init__(self):
        """初始化配置服务"""
        pass
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            db = SessionLocal()
            from ..database import Config
            
            config = db.query(Config).filter_by(key=key).first()
            if config:
                return config.value
            return default
            
        except Exception as e:
            logger.error(f"获取配置失败: {key}, {e}")
            return default
        finally:
            db.close()
    
    def set_config(self, key: str, value: Any, updated_by: int = 0) -> bool:
        """
        设置配置值
        
        Args:
            key: 配置键名
            value: 配置值
            updated_by: 更新者用户 ID
            
        Returns:
            是否设置成功
        """
        try:
            db = SessionLocal()
            from ..database import Config
            from datetime import datetime
            
            config = db.query(Config).filter_by(key=key).first()
            
            if config:
                config.value = str(value)
                config.updated_at = datetime.now()
            else:
                config = Config(
                    key=key,
                    value=str(value),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(config)
            
            db.commit()
            logger.info(f"配置已更新: {key}={value} (by user {updated_by})")
            return True
            
        except Exception as e:
            logger.error(f"设置配置失败: {key}, {e}")
            return False
        finally:
            db.close()
    
    def get_order_timeout(self) -> int:
        """
        获取订单超时时间（分钟）
        
        Returns:
            超时分钟数
        """
        return get_order_timeout_minutes()
    
    def get_address_cooldown(self) -> int:
        """
        获取地址查询冷却时间（分钟）
        
        Returns:
            冷却分钟数
        """
        return get_address_cooldown_minutes()
    
    def get_price(self, package_id: str) -> Optional[float]:
        """
        获取套餐价格
        
        Args:
            package_id: 套餐 ID
            
        Returns:
            价格或 None
        """
        price_key = f"price_{package_id}"
        value = self.get_config(price_key)
        
        if value is not None:
            try:
                return float(value)
            except ValueError:
                return None
        return None
    
    def set_price(self, package_id: str, price: float, updated_by: int = 0) -> bool:
        """
        设置套餐价格
        
        Args:
            package_id: 套餐 ID
            price: 价格
            updated_by: 更新者用户 ID
            
        Returns:
            是否设置成功
        """
        price_key = f"price_{package_id}"
        return self.set_config(price_key, price, updated_by)
    
    def get_all_configs(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            配置字典
        """
        try:
            db = SessionLocal()
            from ..database import Config
            
            configs = db.query(Config).all()
            return {c.key: c.value for c in configs}
            
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            return {}
        finally:
            db.close()


# 全局服务实例（可选）
config_service = ConfigService()
