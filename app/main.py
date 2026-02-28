"""应用工厂。"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.api import health, documents, rag, processing, agent

settings = get_settings()

# 配置日志
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""
    
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        debug=settings.api_debug,
    )
    
    # 创建数据库
    init_db()
    logger.info("数据库已初始化")
    
    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
    app.include_router(rag.router, prefix="/api/v1", tags=["RAG"])
    app.include_router(processing.router, tags=["Document Processing"])
    app.include_router(agent.router, prefix="/api/v1", tags=["Agent"])
    
    # 异常处理器
    @app.exception_handler(Exception)
    async def exception_handler(request, exc):
        logger.error(f"未处理的异常: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "内部服务器错误", "detail": str(exc)}
        )
    
    logger.info("FastAPI应用已成功创建")
    return app


# 创建应用实例
app = create_app()
