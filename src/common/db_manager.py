"""
数据库上下文管理器
确保数据库连接正确关闭
"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    数据库上下文管理器
    
    使用方法:
        with get_db_context() as db:
            # 执行数据库操作
            user = db.query(User).first()
    
    Returns:
        数据库会话
    """
    from src.database import get_db, close_db
    
    db = get_db()
    try:
        yield db
        # 如果没有异常，提交事务
        if db.is_active:
            try:
                db.commit()
            except Exception as e:
                logger.error(f"Failed to commit transaction: {e}")
                db.rollback()
                raise
    except Exception as e:
        # 发生异常时回滚
        logger.error(f"Database operation failed: {e}")
        if db.is_active:
            db.rollback()
        raise
    finally:
        # 确保连接关闭
        close_db(db)


@contextmanager
def get_db_context_readonly() -> Generator[Session, None, None]:
    """
    只读数据库上下文管理器
    不会自动提交事务
    
    使用方法:
        with get_db_context_readonly() as db:
            # 只读查询
            users = db.query(User).all()
    
    Returns:
        数据库会话（只读）
    """
    from src.database import get_db, close_db
    
    db = get_db()
    try:
        yield db
    finally:
        # 只读操作不需要提交
        if db.is_active:
            db.rollback()  # 回滚任何意外的修改
        close_db(db)


def execute_in_transaction(func):
    """
    装饰器：自动管理数据库事务
    
    使用方法:
        @execute_in_transaction
        def update_user(user_id: int, name: str):
            db = get_current_db()  # 从上下文获取db
            user = db.query(User).filter(User.id == user_id).first()
            user.name = name
    """
    def wrapper(*args, **kwargs):
        with get_db_context() as db:
            # 将db注入到函数参数中
            kwargs['db'] = db
            return func(*args, **kwargs)
    return wrapper
