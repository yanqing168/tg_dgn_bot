#!/usr/bin/env python3
"""
数据库清理脚本
清理测试数据和多余的记录
"""

from src.database import SessionLocal, EnergyOrder, AddressQueryLog, Order, PremiumOrder
from datetime import datetime, timedelta

def cleanup_database():
    """清理数据库中的测试数据"""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("数据库清理脚本")
        print("=" * 60)
        
        # 1. 查看能量订单
        energy_orders = db.query(EnergyOrder).all()
        print(f"\n📊 能量订单总数: {len(energy_orders)}")
        
        if energy_orders:
            print("\n能量订单列表:")
            for order in energy_orders[:10]:  # 只显示前10个
                print(f"  - ID: {order.order_id[:8]}... | 类型: {order.order_type} | 状态: {order.status} | 创建时间: {order.created_at}")
            
            # 删除测试订单（可选）
            delete_energy = input("\n是否删除所有能量订单? (y/N): ").strip().lower()
            if delete_energy == 'y':
                deleted = db.query(EnergyOrder).delete()
                db.commit()
                print(f"✅ 已删除 {deleted} 个能量订单")
        
        # 2. 查看地址查询记录
        query_logs = db.query(AddressQueryLog).all()
        print(f"\n📊 地址查询记录总数: {len(query_logs)}")
        
        if query_logs:
            print("\n地址查询记录列表:")
            for log in query_logs[:10]:
                print(f"  - 用户ID: {log.user_id} | 最后查询: {log.last_query_at} | 查询次数: {log.query_count}")
            
            # 删除查询记录（可选）
            delete_logs = input("\n是否删除所有地址查询记录? (y/N): ").strip().lower()
            if delete_logs == 'y':
                deleted = db.query(AddressQueryLog).delete()
                db.commit()
                print(f"✅ 已删除 {deleted} 个查询记录")
        
        # 3. 查看普通订单
        orders = db.query(Order).all()
        print(f"\n📊 普通订单总数: {len(orders)}")
        
        if orders:
            print("\n普通订单列表 (前10个):")
            for order in orders[:10]:
                print(f"  - ID: {order.order_id[:8]}... | 类型: {order.order_type} | 状态: {order.status} | 创建时间: {order.created_at}")
        
        # 4. 查看Premium订单
        premium_orders = db.query(PremiumOrder).all()
        print(f"\n📊 Premium订单总数: {len(premium_orders)}")
        
        if premium_orders:
            print("\n Premium订单列表 (前10个):")
            for order in premium_orders[:10]:
                print(f"  - ID: {order.order_id[:8]}... | 状态: {order.status} | 创建时间: {order.created_at}")
        
        # 5. 清理过期订单（超过7天的pending订单）
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        expired_energy = db.query(EnergyOrder).filter(
            EnergyOrder.status == 'pending',
            EnergyOrder.created_at < seven_days_ago
        ).count()
        
        expired_orders = db.query(Order).filter(
            Order.status == 'pending',
            Order.created_at < seven_days_ago
        ).count()
        
        expired_premium = db.query(PremiumOrder).filter(
            PremiumOrder.status == 'pending',
            PremiumOrder.created_at < seven_days_ago
        ).count()
        
        print(f"\n⏰ 过期订单统计 (超过7天的pending订单):")
        print(f"  - 能量订单: {expired_energy}")
        print(f"  - 普通订单: {expired_orders}")
        print(f"  - Premium订单: {expired_premium}")
        
        if expired_energy + expired_orders + expired_premium > 0:
            delete_expired = input("\n是否删除所有过期订单? (y/N): ").strip().lower()
            if delete_expired == 'y':
                deleted_energy = db.query(EnergyOrder).filter(
                    EnergyOrder.status == 'pending',
                    EnergyOrder.created_at < seven_days_ago
                ).delete()
                
                deleted_orders = db.query(Order).filter(
                    Order.status == 'pending',
                    Order.created_at < seven_days_ago
                ).delete()
                
                deleted_premium = db.query(PremiumOrder).filter(
                    PremiumOrder.status == 'pending',
                    PremiumOrder.created_at < seven_days_ago
                ).delete()
                
                db.commit()
                print(f"✅ 已删除过期订单:")
                print(f"  - 能量订单: {deleted_energy}")
                print(f"  - 普通订单: {deleted_orders}")
                print(f"  - Premium订单: {deleted_premium}")
        
        print("\n" + "=" * 60)
        print("✅ 数据库清理完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_database()
