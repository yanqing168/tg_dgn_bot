#!/usr/bin/env python3
"""
创建测试订单数据

生成各种类型和状态的测试订单，用于验证管理界面功能。
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database import Base, Order as DBOrder
from src.models import OrderStatus, OrderType


def create_test_orders(database_url: str = "sqlite:///./data/bot.db"):
    """
    创建测试订单
    
    Args:
        database_url: 数据库连接 URL
    """
    print("=" * 60)
    print("  创建测试订单数据")
    print("=" * 60)
    print()
    
    # 创建数据库连接
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)  # 确保表存在
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 清除现有测试数据（可选）
        print("🗑️  清除现有订单...")
        db.query(DBOrder).delete()
        db.commit()
        print("✅ 现有订单已清除")
        print()
        
        # 测试订单数据
        test_orders = [
            # ===== Premium 订单 =====
            {
                "order_id": "PREM001",
                "order_type": OrderType.PREMIUM.value,
                "user_id": 1001,
                "base_amount": 10000,  # 10.000 USDT
                "unique_suffix": 123,
                "amount_usdt": 10123,  # 整数微 USDT (10.123)
                "status": OrderStatus.DELIVERED.value,
                "recipient": "@testuser1",
                "premium_months": 3,
                "created_at": datetime.now() - timedelta(days=5),
                "paid_at": datetime.now() - timedelta(days=5, hours=1),
                "delivered_at": datetime.now() - timedelta(days=5, hours=2),
                "expires_at": datetime.now() + timedelta(hours=23),
            },
            {
                "order_id": "PREM002",
                "order_type": OrderType.PREMIUM.value,
                "user_id": 1002,
                "base_amount": 18000,  # 18.000 USDT
                "unique_suffix": 456,
                "amount_usdt": 18456,  # 18.456 USDT
                "status": OrderStatus.PAID.value,
                "recipient": "@testuser2",
                "premium_months": 6,
                "created_at": datetime.now() - timedelta(hours=2),
                "paid_at": datetime.now() - timedelta(hours=1),
                "delivered_at": None,
                "expires_at": datetime.now() + timedelta(hours=28),
            },
            {
                "order_id": "PREM003",
                "order_type": OrderType.PREMIUM.value,
                "user_id": 1003,
                "base_amount": 30000,  # 30.000 USDT
                "unique_suffix": 789,
                "amount_usdt": 30789,  # 30.789 USDT
                "status": OrderStatus.PENDING.value,
                "recipient": "@testuser3",
                "premium_months": 12,
                "created_at": datetime.now() - timedelta(minutes=30),
                "paid_at": None,
                "delivered_at": None,
                "expires_at": datetime.now() + timedelta(minutes=30),
            },
            {
                "order_id": "PREM004",
                "order_type": OrderType.PREMIUM.value,
                "user_id": 1004,
                "base_amount": 10000,
                "unique_suffix": 111,
                "amount_usdt": 10111,
                "status": OrderStatus.EXPIRED.value,
                "recipient": "@expireduser",
                "premium_months": 3,
                "created_at": datetime.now() - timedelta(days=2),
                "paid_at": None,
                "delivered_at": None,
                "expires_at": datetime.now() - timedelta(hours=2),
            },
            {
                "order_id": "PREM005",
                "order_type": OrderType.PREMIUM.value,
                "user_id": 1005,
                "base_amount": 18000,
                "unique_suffix": 222,
                "amount_usdt": 18222,
                "status": OrderStatus.CANCELLED.value,
                "recipient": "@cancelleduser",
                "premium_months": 6,
                "created_at": datetime.now() - timedelta(days=1),
                "paid_at": None,
                "delivered_at": None,
                "expires_at": datetime.now() + timedelta(hours=29),
            },
            
            # ===== Deposit 订单 =====
            {
                "order_id": "DEP001",
                "order_type": OrderType.DEPOSIT.value,
                "user_id": 2001,
                "base_amount": 50000,  # 50.000 USDT
                "unique_suffix": 333,
                "amount_usdt": 50333,  # 50.333 USDT
                "status": OrderStatus.DELIVERED.value,
                "recipient": None,
                "premium_months": None,
                "created_at": datetime.now() - timedelta(days=3),
                "paid_at": datetime.now() - timedelta(days=3, minutes=30),
                "delivered_at": datetime.now() - timedelta(days=3, minutes=35),
                "expires_at": datetime.now() + timedelta(hours=27),
            },
            {
                "order_id": "DEP002",
                "order_type": OrderType.DEPOSIT.value,
                "user_id": 2002,
                "base_amount": 100000,  # 100.000 USDT
                "unique_suffix": 444,
                "amount_usdt": 100444,  # 100.444 USDT
                "status": OrderStatus.PAID.value,
                "recipient": None,
                "premium_months": None,
                "created_at": datetime.now() - timedelta(hours=3),
                "paid_at": datetime.now() - timedelta(hours=2, minutes=30),
                "delivered_at": None,
                "expires_at": datetime.now() + timedelta(hours=27),
            },
            {
                "order_id": "DEP003",
                "order_type": OrderType.DEPOSIT.value,
                "user_id": 2003,
                "base_amount": 25000,  # 25.000 USDT
                "unique_suffix": 555,
                "amount_usdt": 25555,  # 25.555 USDT
                "status": OrderStatus.PENDING.value,
                "recipient": None,
                "premium_months": None,
                "created_at": datetime.now() - timedelta(minutes=15),
                "paid_at": None,
                "delivered_at": None,
                "expires_at": datetime.now() + timedelta(minutes=45),
            },
            
            # ===== TRX Exchange 订单 =====
            {
                "order_id": "TRX001",
                "order_type": OrderType.TRX_EXCHANGE.value,
                "user_id": 3001,
                "base_amount": 20000,  # 20.000 USDT
                "unique_suffix": 666,
                "amount_usdt": 20666,  # 20.666 USDT
                "status": OrderStatus.DELIVERED.value,
                "recipient": "TYourTRXReceiveAddress123",
                "premium_months": None,
                "created_at": datetime.now() - timedelta(days=1),
                "paid_at": datetime.now() - timedelta(days=1, minutes=15),
                "delivered_at": datetime.now() - timedelta(days=1, minutes=20),
                "expires_at": datetime.now() + timedelta(hours=29),
            },
            {
                "order_id": "TRX002",
                "order_type": OrderType.TRX_EXCHANGE.value,
                "user_id": 3002,
                "base_amount": 50000,  # 50.000 USDT
                "unique_suffix": 777,
                "amount_usdt": 50777,  # 50.777 USDT
                "status": OrderStatus.PAID.value,
                "recipient": "TYourTRXReceiveAddress456",
                "premium_months": None,
                "created_at": datetime.now() - timedelta(hours=4),
                "paid_at": datetime.now() - timedelta(hours=3, minutes=45),
                "delivered_at": None,
                "expires_at": datetime.now() + timedelta(hours=26),
            },
            {
                "order_id": "TRX003",
                "order_type": OrderType.TRX_EXCHANGE.value,
                "user_id": 3003,
                "base_amount": 15000,  # 15.000 USDT
                "unique_suffix": 888,
                "amount_usdt": 15888,  # 15.888 USDT
                "status": OrderStatus.PENDING.value,
                "recipient": "TYourTRXReceiveAddress789",
                "premium_months": None,
                "created_at": datetime.now() - timedelta(minutes=45),
                "paid_at": None,
                "delivered_at": None,
                "expires_at": datetime.now() + timedelta(minutes=15),
            },
            
            # ===== 更多历史订单（用于统计） =====
            {
                "order_id": "PREM006",
                "order_type": OrderType.PREMIUM.value,
                "user_id": 1006,
                "base_amount": 10000,
                "unique_suffix": 999,
                "amount_usdt": 10999,
                "status": OrderStatus.DELIVERED.value,
                "recipient": "@historyuser1",
                "premium_months": 3,
                "created_at": datetime.now() - timedelta(days=10),
                "paid_at": datetime.now() - timedelta(days=10, hours=1),
                "delivered_at": datetime.now() - timedelta(days=10, hours=2),
                "expires_at": datetime.now() + timedelta(hours=20),
            },
            {
                "order_id": "DEP004",
                "order_type": OrderType.DEPOSIT.value,
                "user_id": 2004,
                "base_amount": 75000,
                "unique_suffix": 101,
                "amount_usdt": 75101,
                "status": OrderStatus.DELIVERED.value,
                "recipient": None,
                "premium_months": None,
                "created_at": datetime.now() - timedelta(days=7),
                "paid_at": datetime.now() - timedelta(days=7, minutes=20),
                "delivered_at": datetime.now() - timedelta(days=7, minutes=25),
                "expires_at": datetime.now() + timedelta(hours=23),
            },
            {
                "order_id": "TRX004",
                "order_type": OrderType.TRX_EXCHANGE.value,
                "user_id": 3004,
                "base_amount": 30000,
                "unique_suffix": 202,
                "amount_usdt": 30202,
                "status": OrderStatus.DELIVERED.value,
                "recipient": "THistoryAddress",
                "premium_months": None,
                "created_at": datetime.now() - timedelta(days=5),
                "paid_at": datetime.now() - timedelta(days=5, minutes=10),
                "delivered_at": datetime.now() - timedelta(days=5, minutes=15),
                "expires_at": datetime.now() + timedelta(hours=25),
            },
        ]
        
        # 插入订单
        print("📝 插入测试订单...")
        created_count = 0
        for order_data in test_orders:
            order = DBOrder(**order_data)
            db.add(order)
            created_count += 1
            
            # 显示进度
            status_emoji = {
                OrderStatus.PENDING.value: "🟡",
                OrderStatus.PAID.value: "🟢",
                OrderStatus.DELIVERED.value: "✅",
                OrderStatus.EXPIRED.value: "⚫",
                OrderStatus.CANCELLED.value: "🔴",
            }
            emoji = status_emoji.get(order_data["status"], "❓")
            amount = order_data["amount_usdt"] / 1000  # 转换为 USDT
            print(f"   {emoji} {order_data['order_id']} - {order_data['order_type']} - "
                  f"{amount:.3f} USDT - {order_data['status']}")
        
        db.commit()
        print()
        print(f"✅ 成功创建 {created_count} 个测试订单")
        print()
        
        # 统计信息
        print("📊 订单统计:")
        total = db.query(DBOrder).count()
        pending = db.query(DBOrder).filter_by(status=OrderStatus.PENDING.value).count()
        paid = db.query(DBOrder).filter_by(status=OrderStatus.PAID.value).count()
        delivered = db.query(DBOrder).filter_by(status=OrderStatus.DELIVERED.value).count()
        expired = db.query(DBOrder).filter_by(status=OrderStatus.EXPIRED.value).count()
        cancelled = db.query(DBOrder).filter_by(status=OrderStatus.CANCELLED.value).count()
        
        print(f"   总订单数: {total}")
        print(f"   🟡 待支付: {pending}")
        print(f"   🟢 已支付: {paid}")
        print(f"   ✅已交付: {delivered}")
        print(f"   ⚫ 已过期: {expired}")
        print(f"   🔴 已取消: {cancelled}")
        print()
        
        # 按类型统计
        premium_count = db.query(DBOrder).filter_by(order_type=OrderType.PREMIUM.value).count()
        deposit_count = db.query(DBOrder).filter_by(order_type=OrderType.DEPOSIT.value).count()
        trx_count = db.query(DBOrder).filter_by(order_type=OrderType.TRX_EXCHANGE.value).count()
        
        print("📈 按类型统计:")
        print(f"   💎 Premium: {premium_count}")
        print(f"   💰 Deposit: {deposit_count}")
        print(f"   🔄 TRX Exchange: {trx_count}")
        print()
        
        # 成功率
        success_rate = (delivered / total * 100) if total > 0 else 0
        payment_rate = ((paid + delivered) / total * 100) if total > 0 else 0
        
        print("📈 关键指标:")
        print(f"   成功率: {success_rate:.1f}%")
        print(f"   支付率: {payment_rate:.1f}%")
        print()
        
        print("=" * 60)
        print("  ✅ 测试数据创建完成！")
        print("=" * 60)
        print()
        print("🌐 访问管理界面查看数据:")
        print("   http://localhost:8501")
        print()
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="创建测试订单数据")
    parser.add_argument(
        "--database-url",
        default="sqlite:///./data/bot.db",
        help="数据库连接 URL（默认: sqlite:///./data/bot.db）"
    )
    
    args = parser.parse_args()
    create_test_orders(args.database_url)
