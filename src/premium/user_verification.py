"""
用户身份验证服务
处理用户名验证、绑定和查询
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from telegram import User

from src.database import get_db, close_db, UserBinding
from src.common.db_manager import get_db_context

logger = logging.getLogger(__name__)


class UserVerificationService:
    """用户身份验证服务"""
    
    def __init__(self, bot_username: str = None):
        """
        初始化服务
        
        Args:
            bot_username: Bot的用户名，用于生成绑定链接
        """
        self.bot_username = bot_username or "premium_bot"
    
    async def verify_user_exists(self, username: str) -> Dict[str, Any]:
        """
        验证用户是否存在
        
        Args:
            username: Telegram用户名（不含@）
            
        Returns:
            {
                "exists": bool,
                "user_id": Optional[int],
                "nickname": Optional[str],
                "is_verified": bool,
                "binding_url": Optional[str]
            }
        """
        try:
            with get_db_context() as db:
                binding = db.query(UserBinding).filter(
                    UserBinding.username == username.lower()
                ).first()
                
                if binding and binding.is_verified:
                    # 存在且已验证
                    return {
                        "exists": True,
                        "user_id": binding.user_id,
                        "nickname": binding.nickname,
                        "is_verified": True,
                        "binding_url": None
                    }
                elif binding:
                    # 存在但未验证
                    return {
                        "exists": False,
                        "user_id": binding.user_id,
                        "nickname": binding.nickname,
                        "is_verified": False,
                        "binding_url": self._generate_binding_url(username)
                    }
                else:
                    # 不存在
                    return {
                        "exists": False,
                        "user_id": None,
                        "nickname": None,
                        "is_verified": False,
                        "binding_url": self._generate_binding_url(username)
                    }
        except Exception as e:
            logger.error(f"Error verifying user {username}: {e}")
            # 返回安全的默认值
            return {
                "exists": False,
                "user_id": None,
                "nickname": None,
                "is_verified": False,
                "binding_url": self._generate_binding_url(username)
            }
    
    async def bind_user(self, user: User, force_update: bool = False) -> bool:
        """
        绑定用户信息
        
        Args:
            user: Telegram User 对象
            force_update: 是否强制更新已存在的绑定
            
        Returns:
            是否绑定成功
        """
        if not user.username:
            logger.warning(f"User {user.id} has no username, cannot bind")
            return False
        
        try:
            with get_db_context() as db:
                # 查询现有绑定
                existing = db.query(UserBinding).filter(
                    (UserBinding.user_id == user.id) | 
                    (UserBinding.username == user.username.lower())
                ).first()
                
                if existing:
                    if not force_update:
                        logger.info(f"User {user.id} already bound")
                        return True
                    
                    # 更新绑定信息
                    existing.user_id = user.id
                    existing.username = user.username.lower()
                    existing.nickname = user.first_name
                    existing.is_verified = True
                    existing.updated_at = datetime.now()
                else:
                    # 创建新绑定
                    binding = UserBinding(
                        user_id=user.id,
                        username=user.username.lower(),
                        nickname=user.first_name,
                        is_verified=True
                    )
                    db.add(binding)
                
                # 上下文管理器会自动commit
                logger.info(f"Successfully bound user {user.id} (@{user.username})")
            return True
        except Exception as e:
            logger.error(f"Failed to bind user {user.id}: {e}", exc_info=True)
            return False
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        通过user_id获取用户信息
        
        Args:
            user_id: Telegram用户ID
            
        Returns:
            用户信息字典或None
        """
        with get_db_context() as db:
            binding = db.query(UserBinding).filter(
                UserBinding.user_id == user_id
            ).first()
            
            if binding:
                return {
                    "user_id": binding.user_id,
                    "username": binding.username,
                    "nickname": binding.nickname,
                    "is_verified": binding.is_verified
                }
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        通过用户名获取用户信息
        
        Args:
            username: Telegram用户名（不含@）
            
        Returns:
            用户信息字典或None
        """
        with get_db_context() as db:
            binding = db.query(UserBinding).filter(
                UserBinding.username == username.lower()
            ).first()
            
            if binding:
                return {
                    "user_id": binding.user_id,
                    "username": binding.username,
                    "nickname": binding.nickname,
                    "is_verified": binding.is_verified
                }
            return None
    
    def _generate_binding_url(self, username: str) -> str:
        """
        生成用户绑定链接
        
        Args:
            username: 要绑定的用户名
            
        Returns:
            深链接URL
        """
        return f"https://t.me/{self.bot_username}?start=bind_{username}"
    
    async def auto_bind_on_interaction(self, user: User) -> bool:
        """
        用户与bot交互时自动绑定（如果有用户名）
        
        Args:
            user: Telegram User 对象
            
        Returns:
            是否绑定成功
        """
        if not user or not user.username:
            return False
        
        try:
            # 使用上下文管理器确保连接正确关闭
            with get_db_context() as db:
                # 检查是否已绑定
                existing = db.query(UserBinding).filter(
                    UserBinding.user_id == user.id
                ).first()
                
                if existing:
                    if existing.is_verified:
                        # 已验证
                        return True
                    else:
                        # 存在但未验证，更新验证状态
                        existing.is_verified = True
                        existing.updated_at = datetime.now()
                        # 事务会自动提交
                        logger.info(f"Verified existing user {user.id}")
                        return True
                else:
                    # 新用户，创建绑定
                    binding = UserBinding(
                        user_id=user.id,
                        username=user.username.lower(),
                        nickname=user.first_name or user.username,
                        is_verified=True,
                        created_at=datetime.now()
                    )
                    db.add(binding)
                    # 事务会自动提交
                    logger.info(f"Created binding for user {user.id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Auto-bind failed for user {user.id}: {e}")
            # 不要抛出异常，避免影响主流程
            return False


# 全局实例（延迟初始化）
user_verification_service: Optional[UserVerificationService] = None

def get_user_verification_service(bot_username: str = None) -> UserVerificationService:
    """获取用户验证服务实例"""
    global user_verification_service
    if user_verification_service is None:
        user_verification_service = UserVerificationService(bot_username)
    return user_verification_service
