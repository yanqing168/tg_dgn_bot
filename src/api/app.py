"""
API应用主文件
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from .routes import router as api_router
from .middleware import setup_middleware


logger = logging.getLogger(__name__)


def create_api_app() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title="TG Bot API",
        description="Telegram Bot REST API接口",
        version="2.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 设置其他中间件
    setup_middleware(app)
    
    # 注册路由
    app.include_router(api_router, prefix="/api")
    
    # 全局异常处理
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "status_code": 500}
        )
    
    return app
