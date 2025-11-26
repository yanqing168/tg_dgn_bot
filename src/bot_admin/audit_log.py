"""
操作审计日志

记录所有管理员操作，用于追踪和审计。
"""
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import os

logger = logging.getLogger(__name__)

Base = declarative_base()


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, nullable=False, comment="管理员 user_id")
    action = Column(String(100), nullable=False, comment="操作类型")
    target = Column(String(200), comment="操作对象")
    details = Column(Text, comment="操作详情")
    result = Column(String(20), comment="操作结果: success/failed")
    ip_address = Column(String(50), comment="IP地址")
    created_at = Column(DateTime, default=datetime.now)


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, db_path: str = None):
        """初始化审计日志"""
        if db_path is None:
            db_path = os.getenv("DATABASE_URL", "sqlite:///./tg_bot.db")
        
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def log(
        self,
        admin_id: int,
        action: str,
        target: str = "",
        details: str = "",
        result: str = "success",
        ip_address: str = ""
    ):
        """记录审计日志"""
        session = self.SessionLocal()
        try:
            log = AuditLog(
                admin_id=admin_id,
                action=action,
                target=target,
                details=details,
                result=result,
                ip_address=ip_address
            )
            session.add(log)
            session.commit()
            
            logger.info(
                f"Audit: admin={admin_id}, action={action}, "
                f"target={target}, result={result}"
            )
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log audit: {e}")
        finally:
            session.close()
    
    def get_recent_logs(self, limit: int = 50):
        """获取最近的审计日志"""
        session = self.SessionLocal()
        try:
            logs = (
                session.query(AuditLog)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )
            return logs
        finally:
            session.close()
    
    def get_admin_logs(self, admin_id: int, limit: int = 20):
        """获取指定管理员的操作日志"""
        session = self.SessionLocal()
        try:
            logs = (
                session.query(AuditLog)
                .filter_by(admin_id=admin_id)
                .order_by(AuditLog.created_at.desc())
                .limit(limit)
                .all()
            )
            return logs
        finally:
            session.close()


# 全局审计日志实例
audit_logger = AuditLogger()
