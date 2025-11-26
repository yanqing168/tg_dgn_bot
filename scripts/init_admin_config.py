#!/usr/bin/env python3
"""
初始化管理员配置

在首次使用管理员面板前运行此脚本，初始化数据库中的默认配置。
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db
from src.bot_admin.config_manager import config_manager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    logger.info("🚀 开始初始化管理员配置...")
    
    # 初始化数据库
    init_db()
    logger.info("✅ 数据库初始化完成")
    
    # 初始化默认配置
    config_manager.init_defaults()
    logger.info("✅ 默认配置已写入数据库")
    
    # 显示当前配置
    logger.info("\n" + "="*50)
    logger.info("当前配置：")
    logger.info("="*50)
    
    # Premium 价格
    logger.info("\n💎 Premium 会员价格：")
    logger.info(f"  3个月：${config_manager.get_price('premium_3_months')} USDT")
    logger.info(f"  6个月：${config_manager.get_price('premium_6_months')} USDT")
    logger.info(f"  12个月：${config_manager.get_price('premium_12_months')} USDT")
    
    # TRX 汇率
    logger.info(f"\n🔄 TRX 兑换汇率：")
    logger.info(f"  1 USDT = {config_manager.get_price('trx_exchange_rate')} TRX")
    
    # 能量价格
    logger.info(f"\n⚡ 能量价格：")
    logger.info(f"  小能量：{config_manager.get_price('energy_small')} TRX")
    logger.info(f"  大能量：{config_manager.get_price('energy_large')} TRX")
    logger.info(f"  笔数套餐：{config_manager.get_price('energy_package_per_tx')} TRX/笔")
    
    # 系统设置
    logger.info(f"\n⚙️  系统设置：")
    logger.info(f"  订单超时：{config_manager.get_setting('order_timeout_minutes')} 分钟")
    logger.info(
        f"  查询限频：{config_manager.get_setting('address_query_rate_limit')} 分钟"
        "（默认 1 分钟）"
    )
    
    logger.info("\n" + "="*50)
    logger.info("✅ 初始化完成！现在可以使用 /admin 命令访问管理面板。")
    logger.info("="*50)


if __name__ == "__main__":
    main()
