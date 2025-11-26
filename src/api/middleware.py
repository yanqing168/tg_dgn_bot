"""
API中间件配置
"""

import logging
import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware


logger = logging.getLogger(__name__)


async def log_requests(request: Request, call_next: Callable) -> Response:
    """
    请求日志中间件
    
    记录所有API请求的详细信息
    """
    start_time = time.time()
    
    # 记录请求信息
    logger.info(
        f"API Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = time.time() - start_time
    
    # 记录响应信息
    logger.info(
        f"API Response: {request.method} {request.url.path} "
        f"status={response.status_code} time={process_time:.3f}s"
    )
    
    # 添加处理时间到响应头
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    速率限制中间件
    
    限制API请求频率
    """
    # TODO: 实现基于Redis的速率限制
    # 这里仅作为示例框架
    
    # 获取客户端IP
    client_ip = request.client.host if request.client else "unknown"
    
    # 检查速率限制（简化版本）
    # 实际应该使用Redis或其他存储来跟踪请求次数
    
    response = await call_next(request)
    return response


def setup_middleware(app: FastAPI):
    """
    设置所有中间件
    
    Args:
        app: FastAPI应用实例
    """
    # 添加请求日志中间件
    @app.middleware("http")
    async def add_log_requests(request: Request, call_next):
        return await log_requests(request, call_next)
    
    # 添加速率限制中间件
    @app.middleware("http")
    async def add_rate_limit(request: Request, call_next):
        return await rate_limit_middleware(request, call_next)
    
    # 添加可信主机中间件（生产环境使用）
    # app.add_middleware(
    #     TrustedHostMiddleware,
    #     allowed_hosts=["example.com", "*.example.com"]
    # )
    
    logger.info("✅ API中间件设置完成")
