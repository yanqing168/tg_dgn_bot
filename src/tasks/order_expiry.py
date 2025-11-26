"""
订单超时自动处理任务

定期检查数据库中的 PENDING 订单，自动将超时订单标记为 EXPIRED，
并释放占用的 Redis 后缀（如果适用）。
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import SessionLocal, Order
from ..payments.suffix_manager import SuffixManager
from src.common.settings_service import get_order_timeout_minutes

logger = logging.getLogger(__name__)


class OrderExpiryTask:
    """订单超时处理任务"""

    def __init__(self):
        """初始化任务"""
        self.suffix_manager = SuffixManager()
        logger.info("订单超时处理任务初始化完成")

    def check_and_expire_orders(self) -> dict:
        """
        检查并处理过期订单

        Returns:
            dict: 处理结果统计
                {
                    "checked": int,  # 检查的订单数
                    "expired": int,  # 已过期的订单数
                    "suffix_released": int,  # 释放的后缀数
                    "errors": int  # 处理错误数
                }
        """
        timeout_minutes = get_order_timeout_minutes()
        logger.info("订单超时检查任务：本次使用超时时间 %s 分钟", timeout_minutes)

        session = SessionLocal()
        stats = {
            "checked": 0,
            "expired": 0,
            "suffix_released": 0,
            "errors": 0
        }

        try:
            # 计算超时时间点
            timeout_time = datetime.now() - timedelta(minutes=timeout_minutes)
            
            # 查询所有超时的 PENDING 订单
            stmt = select(Order).where(
                Order.status == "PENDING",
                Order.created_at < timeout_time
            )
            expired_orders = session.execute(stmt).scalars().all()
            
            stats["checked"] = len(expired_orders)
            
            if not expired_orders:
                logger.debug("没有发现过期订单")
                return stats

            logger.info(f"发现 {len(expired_orders)} 个过期订单，开始处理...")

            # 处理每个过期订单
            for order in expired_orders:
                try:
                    self._expire_single_order(session, order, stats)
                except Exception as e:
                    logger.error(f"处理订单 {order.order_id} 失败: {e}", exc_info=True)
                    stats["errors"] += 1

            # 提交所有更改
            session.commit()
            
            logger.info(
                f"订单超时处理完成 - "
                f"检查: {stats['checked']}, "
                f"已过期: {stats['expired']}, "
                f"释放后缀: {stats['suffix_released']}, "
                f"错误: {stats['errors']}"
            )

        except Exception as e:
            logger.error(f"订单超时检查任务失败: {e}", exc_info=True)
            session.rollback()
            stats["errors"] += 1

        finally:
            session.close()

        return stats

    def _expire_single_order(self, session: Session, order: Order, stats: dict):
        """
        处理单个过期订单

        Args:
            session: 数据库会话
            order: 订单对象
            stats: 统计字典
        """
        order_id = order.order_id
        order_type = order.order_type
        
        # 更新订单状态
        order.status = "EXPIRED"
        
        logger.info(
            f"订单 {order_id} 已过期 "
            f"(类型: {order_type}, "
            f"创建时间: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')})"
        )
        
        stats["expired"] += 1

        # 释放 Redis 后缀（仅适用于使用3位小数后缀的订单类型）
        if self._should_release_suffix(order_type):
            try:
                # 从订单金额中提取后缀
                suffix = self._extract_suffix_from_amount(order.amount_usdt)
                
                if suffix:
                    released = asyncio.run(
                        self.suffix_manager.release_suffix(suffix, order_id)
                    )
                    if released:
                        logger.info(f"释放后缀 {suffix} (订单: {order_id})")
                        stats["suffix_released"] += 1
                    else:
                        logger.warning(f"无法释放后缀 {suffix} (订单: {order_id})")
                        
            except Exception as e:
                logger.error(f"释放后缀失败 (订单: {order_id}): {e}")

    def _should_release_suffix(self, order_type: str) -> bool:
        """
        判断订单类型是否需要释放后缀

        Args:
            order_type: 订单类型

        Returns:
            bool: 是否需要释放后缀
        """
        # 使用3位小数后缀的订单类型
        suffix_order_types = ["premium", "deposit", "trx_exchange"]
        return order_type in suffix_order_types

    def _extract_suffix_from_amount(self, amount_micro_usdt: int) -> Optional[int]:
        """
        从微 USDT 金额中提取后缀

        Args:
            amount_micro_usdt: 微 USDT 金额（整数，单位：微 USDT）

        Returns:
            Optional[int]: 后缀（1-999），如果无法提取则返回 None
        """
        try:
            # 将微 USDT 转为 USDT（保留3位小数）
            amount_usdt = amount_micro_usdt / 1_000_000
            
            # 提取小数部分的后三位
            # 例如：10.123 USDT -> 123
            suffix = int(round(amount_usdt * 1000)) % 1000
            
            # 验证后缀范围（1-999）
            if 1 <= suffix <= 999:
                return suffix
            else:
                logger.warning(f"提取的后缀 {suffix} 超出范围 (金额: {amount_usdt} USDT)")
                return None
                
        except Exception as e:
            logger.error(f"提取后缀失败 (金额: {amount_micro_usdt}): {e}")
            return None

    def run(self):
        """运行任务（由调度器调用）"""
        try:
            logger.debug("开始执行订单超时检查任务...")
            stats = self.check_and_expire_orders()
            return stats
        except Exception as e:
            logger.error(f"订单超时任务执行失败: {e}", exc_info=True)
            return {"error": str(e)}


# 全局任务实例
order_expiry_task = OrderExpiryTask()
