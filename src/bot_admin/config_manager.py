"""
配置管理器

动态读写配置文件，支持热更新。
价格配置存储在 SQLite 数据库中，避免修改代码。
"""
import os
import logging
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger(__name__)

Base = declarative_base()


class PriceConfig(Base):
    """价格配置表"""
    __tablename__ = "price_configs"
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(50), unique=True, nullable=False, comment="配置键")
    config_value = Column(Float, nullable=False, comment="配置值")
    description = Column(String(200), comment="描述")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    updated_by = Column(Integer, comment="更新者 user_id")


class ContentConfig(Base):
    """文案配置表"""
    __tablename__ = "content_configs"
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(50), unique=True, nullable=False, comment="配置键")
    config_value = Column(Text, nullable=False, comment="配置值")
    description = Column(String(200), comment="描述")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    updated_by = Column(Integer, comment="更新者 user_id")


class SettingConfig(Base):
    """系统设置表"""
    __tablename__ = "setting_configs"
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(50), unique=True, nullable=False, comment="配置键")
    config_value = Column(String(200), nullable=False, comment="配置值")
    description = Column(String(200), comment="描述")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    updated_by = Column(Integer, comment="更新者 user_id")


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, db_path: str = None):
        """初始化配置管理器"""
        if db_path is None:
            db_path = os.getenv("DATABASE_URL", "sqlite:///./tg_bot.db")
        
        # 确保数据库目录存在
        if db_path.startswith("sqlite:///"):
            db_file_path = db_path.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_file_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def _get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    # ==================== 价格配置 ====================
    
    def get_price(self, key: str, default: float = 0.0) -> float:
        """获取价格配置"""
        session = self._get_session()
        try:
            config = session.query(PriceConfig).filter_by(config_key=key).first()
            if config:
                return config.config_value
            return default
        finally:
            session.close()
    
    def set_price(self, key: str, value: float, user_id: int, description: str = "") -> bool:
        """设置价格配置"""
        session = self._get_session()
        try:
            config = session.query(PriceConfig).filter_by(config_key=key).first()
            
            if config:
                config.config_value = value
                config.updated_by = user_id
                config.updated_at = datetime.now()
            else:
                config = PriceConfig(
                    config_key=key,
                    config_value=value,
                    description=description,
                    updated_by=user_id
                )
                session.add(config)
            
            session.commit()
            logger.info(f"Price config updated: {key}={value} by user {user_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to set price config: {e}")
            return False
        finally:
            session.close()
    
    def get_all_prices(self) -> Dict[str, float]:
        """获取所有价格配置"""
        session = self._get_session()
        try:
            configs = session.query(PriceConfig).all()
            return {c.config_key: c.config_value for c in configs}
        finally:
            session.close()
    
    # ==================== 文案配置 ====================
    
    def get_content(self, key: str, default: str = "") -> str:
        """获取文案配置"""
        session = self._get_session()
        try:
            config = session.query(ContentConfig).filter_by(config_key=key).first()
            if config:
                return config.config_value
            return default
        finally:
            session.close()
    
    def set_content(self, key: str, value: str, user_id: int, description: str = "") -> bool:
        """设置文案配置"""
        session = self._get_session()
        try:
            config = session.query(ContentConfig).filter_by(config_key=key).first()
            
            if config:
                config.config_value = value
                config.updated_by = user_id
                config.updated_at = datetime.now()
            else:
                config = ContentConfig(
                    config_key=key,
                    config_value=value,
                    description=description,
                    updated_by=user_id
                )
                session.add(config)
            
            session.commit()
            logger.info(f"Content config updated: {key} by user {user_id}")
            
            # 清除缓存，确保下次读取最新值
            try:
                from src.utils.content_helper import clear_content_cache
                clear_content_cache(key)
                logger.debug(f"配置缓存已清除: {key}")
            except Exception as cache_error:
                logger.warning(f"清除缓存失败 ({key}): {cache_error}")
            
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to set content config: {e}")
            return False
        finally:
            session.close()
    
    # ==================== 系统设置 ====================
    
    def get_setting(self, key: str, default: str = "") -> str:
        """获取系统设置"""
        session = self._get_session()
        try:
            config = session.query(SettingConfig).filter_by(config_key=key).first()
            if config:
                return config.config_value
            return default
        finally:
            session.close()
    
    def set_setting(self, key: str, value: str, user_id: int, description: str = "") -> bool:
        """设置系统设置"""
        session = self._get_session()
        try:
            config = session.query(SettingConfig).filter_by(config_key=key).first()
            
            if config:
                config.config_value = value
                config.updated_by = user_id
                config.updated_at = datetime.now()
            else:
                config = SettingConfig(
                    config_key=key,
                    config_value=value,
                    description=description,
                    updated_by=user_id
                )
                session.add(config)
            
            session.commit()
            logger.info(f"Setting config updated: {key}={value} by user {user_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to set setting config: {e}")
            return False
        finally:
            session.close()
    
    # ==================== 初始化默认配置 ====================
    
    def init_defaults(self):
        """初始化默认配置"""
        # Premium 价格
        self.set_price("premium_3_months", 10.0, 0, "Premium 3个月价格")
        self.set_price("premium_6_months", 18.0, 0, "Premium 6个月价格")
        self.set_price("premium_12_months", 30.0, 0, "Premium 12个月价格")
        
        # TRX 汇率
        self.set_price("trx_exchange_rate", 3.05, 0, "TRX 兑换汇率")
        
        # 能量价格
        self.set_price("energy_small", 3.0, 0, "小能量价格(TRX)")
        self.set_price("energy_large", 6.0, 0, "大能量价格(TRX)")
        self.set_price("energy_package_per_tx", 3.6, 0, "笔数套餐单价(TRX)")
        
        # 系统设置
        self.set_setting("order_timeout_minutes", "30", 0, "订单超时时间(分钟)")
        self.set_setting("address_query_rate_limit", "1", 0, "地址查询限频(分钟)")
        
        logger.info("Default configs initialized")


# 全局配置管理器实例
config_manager = ConfigManager()
