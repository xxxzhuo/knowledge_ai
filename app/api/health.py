"""健康检查端点。"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.database import get_db
from app.schemas import HealthStatus
from app.storage import get_milvus_store
from app.embeddings import get_embedding_service

router = APIRouter()
logger = logging.getLogger(__name__)


def check_vector_store() -> str:
    """检查向量库健康状态"""
    try:
        vector_store = get_milvus_store()
        if vector_store.is_healthy():
            return "healthy"
        else:
            return "unhealthy"
    except Exception as e:
        logger.error(f"向量库检查失败: {str(e)}")
        return "unhealthy"


def check_embeddings_service() -> str:
    """检查 Embedding 服务健康状态"""
    try:
        embedding_service = get_embedding_service()
        # 尝试一个简单的embedding操作
        test_embedding = embedding_service.embed_text("test")
        if test_embedding and len(test_embedding) > 0:
            return "healthy"
        else:
            return "unhealthy"
    except Exception as e:
        logger.error(f"Embedding 服务检查失败: {str(e)}")
        return "unhealthy"


@router.get("/health", response_model=HealthStatus)
async def health_check(db: Session = Depends(get_db)) -> HealthStatus:
    """
    日常检查端点。
    
    返回所有服务的状态：
    - 数据库
    - 向量库
    - Embeddings服务
    """
    
    # 检查数据库
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"数据库检查失败: {str(e)}")
        db_status = "unhealthy"
    
    # 检查向量库
    vector_store_status = check_vector_store()
    
    # 检查 Embedding 服务
    embeddings_status = check_embeddings_service()
    
    # 决定整体状态
    if db_status == "unhealthy" or vector_store_status == "unhealthy" or embeddings_status == "unhealthy":
        overall_status = "unhealthy"
    elif vector_store_status == "degraded" or embeddings_status == "degraded":
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    logger.info(f"健康检查完成: {overall_status} (DB={db_status}, Vector={vector_store_status}, Embeddings={embeddings_status})")
    
    return HealthStatus(
        status=overall_status,
        database=db_status,
        vector_store=vector_store_status,
        embeddings_service=embeddings_status,
        timestamp=datetime.utcnow()
    )


@router.get("/health/vector-store")
async def vector_store_health() -> dict:
    """获取向量库详细的健康信息"""
    try:
        vector_store = get_milvus_store()
        stats = {
            "status": "healthy" if vector_store.is_healthy() else "unhealthy",
            "vector_count": vector_store.count(),
            "collection_name": vector_store.collection_name
        }
        return stats
    except Exception as e:
        logger.error(f"向量库详细信息获取失败: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/status")
async def status():
    """服务状态端点。"""
    return {
        "service": "Semiconductor Knowledge AI",
        "status": "operational",
        "version": "0.1.0"
    }
