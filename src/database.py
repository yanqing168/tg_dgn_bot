"""
数据库配置和模型定义
使用 SQLAlchemy + SQLite
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Index, BigInteger, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import Optional
import os

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tg_bot.db")

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型
Base = declarative_base()


def get_engine():
    """获取数据库引擎（用于 Alembic 迁移）"""
    return engine


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), nullable=True)
    balance_micro_usdt = Column(Integer, default=0, nullable=False)  # 微USDT (×10^6)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    def get_balance(self) -> float:
        """获取余额（USDT）"""
        return self.balance_micro_usdt / 1_000_000
    
    def set_balance(self, amount: float):
        """设置余额（USDT）"""
        self.balance_micro_usdt = int(amount * 1_000_000)


class DepositOrder(Base):
    """充值订单表"""
    __tablename__ = "deposit_orders"
    
    order_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    base_amount = Column(Float, nullable=False)  # 基础金额
    unique_suffix = Column(Integer, nullable=False)  # 唯一后缀 (1-999)
    total_amount = Column(Float, nullable=False)  # 总金额
    amount_micro_usdt = Column(Integer, nullable=False)  # 微USDT金额
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING, PAID, EXPIRED
    tx_hash = Column(String(100), nullable=True)  # 交易哈希
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    paid_at = Column(DateTime, nullable=True)  # 支付时间
    expires_at = Column(DateTime, nullable=False)  # 过期时间
    
    # 创建索引
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_suffix', 'unique_suffix'),
    )


class DebitRecord(Base):
    """扣费记录表"""
    __tablename__ = "debit_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount_micro_usdt = Column(Integer, nullable=False)  # 扣费金额（微USDT）
    order_type = Column(String(32), nullable=False)  # 订单类型（premium/energy等）
    related_order_id = Column(String(36), nullable=True)  # 关联订单ID
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    def get_amount(self) -> float:
        """获取扣费金额（USDT）"""
        return self.amount_micro_usdt / 1_000_000


class SuffixAllocation(Base):
    """后缀分配记录表（持久化）"""
    __tablename__ = "suffix_allocations"
    
    suffix = Column(Integer, primary_key=True)  # 1-999
    order_id = Column(String(36), nullable=True, index=True)  # 当前分配的订单ID
    allocated_at = Column(DateTime, nullable=True)  # 分配时间
    expires_at = Column(DateTime, nullable=True)  # 过期时间


class AddressQueryLog(Base):
    """地址查询限频记录表"""
    __tablename__ = "address_query_logs"
    
    user_id = Column(Integer, primary_key=True, index=True)
    last_query_at = Column(DateTime, nullable=False)  # 最后查询时间
    query_count = Column(Integer, default=1, nullable=False)  # 查询次数


class EnergyOrder(Base):
    """能量订单表"""
    __tablename__ = "energy_orders"
    
    order_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    order_type = Column(String(20), nullable=False)  # hourly/package/flash
    
    # 时长能量字段
    energy_amount = Column(Integer, nullable=True)  # 能量数量(65000/131000)
    purchase_count = Column(Integer, nullable=True)  # 购买笔数(1-20)
    
    # 笔数套餐字段
    package_count = Column(Integer, nullable=True)  # 套餐笔数
    
    # 闪兑字段
    usdt_amount = Column(Float, nullable=True)  # USDT金额
    
    # 通用字段
    receive_address = Column(String(64), nullable=False)  # 接收地址
    total_price_trx = Column(Float, nullable=True)  # 总价(TRX)
    total_price_usdt = Column(Float, nullable=True)  # 总价(USDT)
    
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING/PROCESSING/COMPLETED/FAILED/EXPIRED
    api_order_id = Column(String(64), nullable=True, index=True)  # API订单ID
    error_message = Column(String(500), nullable=True)  # 错误信息
    
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    completed_at = Column(DateTime, nullable=True)  # 完成时间
    # TODO: add Alembic migration for new user confirmation columns
    user_tx_hash = Column(String(100), nullable=True)
    user_confirmed_at = Column(DateTime, nullable=True)
    
    # 创建索引
    __table_args__ = (
        Index('idx_energy_user_status', 'user_id', 'status'),
        Index('idx_energy_order_type', 'order_type'),
    )


class Order(Base):
    """通用订单表（用于管理后台）"""
    __tablename__ = "orders"
    
    order_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    order_type = Column(String(32), nullable=False)  # premium, deposit, trx_exchange, energy
    
    # 金额字段
    base_amount = Column(Integer, nullable=False)  # 基础金额（微USDT）
    unique_suffix = Column(Integer, nullable=True)  # 唯一后缀（3位小数模式）
    amount_usdt = Column(Integer, nullable=False)  # 总金额（微USDT）
    
    # 状态字段
    status = Column(String(20), default="PENDING", nullable=False)  # PENDING, PAID, DELIVERED, EXPIRED, CANCELLED
    
    # 收件人/目标地址
    recipient = Column(String(255), nullable=True)  # Premium收件人 或 TRX地址
    
    # Premium 专用字段
    premium_months = Column(Integer, nullable=True)  # Premium月数（3/6/12）
    
    # 交易信息
    tx_hash = Column(String(100), nullable=True)  # 区块链交易哈希
    # TODO: add Alembic migration for new user confirmation columns
    user_tx_hash = Column(String(100), nullable=True)
    user_confirmed_at = Column(DateTime, nullable=True)
    user_confirm_source = Column(String(32), nullable=True)
    
    # 时间字段
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    paid_at = Column(DateTime, nullable=True)  # 支付时间
    delivered_at = Column(DateTime, nullable=True)  # 交付时间
    expires_at = Column(DateTime, nullable=False)  # 过期时间
    
    # 索引
    __table_args__ = (
        Index('idx_orders_type_status', 'order_type', 'status'),
        Index('idx_orders_user_status', 'user_id', 'status'),
        Index('idx_orders_created', 'created_at'),
    )


class UserBinding(Base):
    """用户绑定表 - 存储用户名与user_id的映射"""
    __tablename__ = "user_bindings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, unique=True, index=True)
    username = Column(String(32), nullable=True, unique=True, index=True)
    nickname = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class PremiumOrder(Base):
    """Premium 专用订单表"""
    __tablename__ = "premium_orders"
    
    order_id = Column(String(36), primary_key=True)
    buyer_id = Column(BigInteger, nullable=False, index=True)  # 购买者ID
    recipient_id = Column(BigInteger, nullable=True)  # 接收者ID
    recipient_username = Column(String(32), nullable=True)  # 接收者用户名
    recipient_type = Column(String(10), nullable=False)  # 'self' or 'other'
    premium_months = Column(Integer, nullable=False)
    amount_usdt = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default='PENDING')
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    tx_hash = Column(String(100), nullable=True)
    delivery_result = Column(Text, nullable=True)
    
    # 索引
    __table_args__ = (
        Index('idx_premium_orders_buyer_status', 'buyer_id', 'status'),
        Index('idx_premium_orders_recipient', 'recipient_id'),
    )


def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # 由调用者负责关闭


def close_db(db: Session):
    """关闭数据库会话"""
    db.close()


def init_db():
    """初始化数据库（创建表）"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表初始化成功")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def init_db_safe():
    """安全初始化数据库（生产环境）"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 数据库表初始化成功")
        
        # 验证关键表
        with engine.connect() as conn:
            tables_to_check = [
                'users', 'orders', 'user_bindings', 
                'premium_orders', 'deposit_orders',
                'debit_records', 'suffix_allocations',
                'address_query_logs', 'energy_orders'
            ]
            
            for table in tables_to_check:
                try:
                    result = conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                    result.fetchone()  # 尝试获取结果
                    logger.info(f"✅ 表 {table} 验证通过")
                except Exception as e:
                    logger.warning(f"⚠️ 表 {table} 不存在或无法访问: {e}")
                    # 尝试单独创建该表
                    for model in Base.registry._class_registry.data.values():
                        if hasattr(model, '__tablename__') and model.__tablename__ == table:
                            try:
                                model.__table__.create(bind=engine, checkfirst=True)
                                logger.info(f"✅ 表 {table} 已创建")
                            except Exception as create_error:
                                logger.error(f"❌ 创建表 {table} 失败: {create_error}")
                                
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def check_database_health() -> bool:
    """检查数据库健康状态"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 尝试建立连接
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            
        # 检查关键表
        db = get_db()
        try:
            # 尝试查询用户表
            db.query(User).first()
            logger.info("✅ 数据库健康检查通过")
            return True
        finally:
            close_db(db)
            
    except Exception as e:
        logger.error(f"❌ 数据库健康检查失败: {e}")
        return False
