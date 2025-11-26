"""
能量兑换数据模型
定义订单类型、套餐、订单状态等数据结构

[Legacy] 旧版实现，仅用于兼容，后续会被 services 层封装替代
"""
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EnergyOrderType(str, Enum):
    """能量订单类型"""
    HOURLY = "hourly"  # 时长能量（1小时）
    PACKAGE = "package"  # 笔数套餐
    FLASH = "flash"  # 闪兑


class EnergyPackage(str, Enum):
    """能量套餐类型"""
    SMALL = "65000"  # 6.5万能量
    LARGE = "131000"  # 13.1万能量


class EnergyOrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"  # 待支付
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    EXPIRED = "expired"  # 已过期


class EnergyPriceConfig(BaseModel):
    """能量价格配置"""
    small_energy_price: float = Field(3.0, description="6.5万能量价格(TRX)")
    large_energy_price: float = Field(6.0, description="13.1万能量价格(TRX)")
    package_price_per_tx: float = Field(3.6, description="笔数套餐每笔价格(TRX)")
    package_min_usdt: float = Field(5.0, description="笔数套餐最低USDT购买金额")
    max_purchases: int = Field(20, description="一次最大购买笔数")
    
    class Config:
        from_attributes = True


class EnergyOrder(BaseModel):
    """能量订单模型"""
    order_id: str = Field(..., description="订单ID")
    user_id: int = Field(..., description="用户TG ID")
    order_type: EnergyOrderType = Field(..., description="订单类型")
    
    # 时长能量字段
    energy_amount: Optional[int] = Field(None, description="能量数量(65000/131000)")
    purchase_count: Optional[int] = Field(None, description="购买笔数(1-20)")
    
    # 笔数套餐字段
    package_count: Optional[int] = Field(None, description="套餐笔数")
    
    # 闪兑字段
    usdt_amount: Optional[float] = Field(None, description="USDT金额")
    
    # 通用字段
    receive_address: str = Field(..., description="接收地址")
    total_price_trx: Optional[float] = Field(None, description="总价(TRX)")
    total_price_usdt: Optional[float] = Field(None, description="总价(USDT)")
    
    status: EnergyOrderStatus = Field(EnergyOrderStatus.PENDING, description="订单状态")
    api_order_id: Optional[str] = Field(None, description="API订单ID")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    class Config:
        from_attributes = True


class APIAccountInfo(BaseModel):
    """API账号信息"""
    username: str = Field(..., description="用户名")
    balance_trx: float = Field(..., description="TRX余额")
    balance_usdt: float = Field(0.0, description="USDT余额")
    frozen_balance: float = Field(0.0, description="冻结余额")
    
    class Config:
        from_attributes = True


class APIPriceQuery(BaseModel):
    """API价格查询响应"""
    energy_65k_price: float = Field(..., description="6.5万能量价格(TRX)")
    energy_131k_price: float = Field(..., description="13.1万能量价格(TRX)")
    package_price: float = Field(..., description="笔数套餐价格(TRX)")
    
    class Config:
        from_attributes = True


class APIOrderResponse(BaseModel):
    """API订单响应"""
    code: int = Field(..., description="状态码")
    msg: str = Field(..., description="消息")
    data: Optional[dict] = Field(None, description="数据")
    order_id: Optional[str] = Field(None, description="订单ID")
    
    class Config:
        from_attributes = True
