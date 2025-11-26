"""
API认证模块
"""

import logging
from typing import Optional
from fastapi import HTTPException, Header
from src.config import settings


logger = logging.getLogger(__name__)


async def api_key_auth(
    x_api_key: Optional[str] = Header(None, description="API密钥")
) -> str:
    """
    API密钥认证
    
    Args:
        x_api_key: 请求头中的API密钥
        
    Returns:
        认证成功返回API密钥
        
    Raises:
        HTTPException: 认证失败
    """
    if not x_api_key:
        logger.warning("API request without key")
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # 从配置中获取有效的API密钥
    valid_api_keys = getattr(settings, 'api_keys', [])
    if not valid_api_keys:
        # 如果没有配置，使用默认密钥（仅用于开发）
        valid_api_keys = [settings.webhook_secret] if hasattr(settings, 'webhook_secret') else []
    
    if x_api_key not in valid_api_keys:
        logger.warning(f"Invalid API key attempt: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )
    
    return x_api_key


async def optional_api_key_auth(
    x_api_key: Optional[str] = Header(None, description="API密钥")
) -> Optional[str]:
    """
    可选的API密钥认证（某些接口可以不需要认证）
    
    Args:
        x_api_key: 请求头中的API密钥
        
    Returns:
        API密钥或None
    """
    if x_api_key:
        try:
            return await api_key_auth(x_api_key)
        except HTTPException:
            return None
    return None
