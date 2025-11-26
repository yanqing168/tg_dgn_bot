"""
Bot API接口层
提供REST API访问Bot功能
"""

from .app import create_api_app
from .routes import router

__all__ = ['create_api_app', 'router']
