"""存储模块。"""

import logging
import threading
from app.storage.vector_store import VectorStore
from app.storage.milvus_store import MilvusStore
from app.storage.aliyun_vector_store import AliyunVectorStore

__all__ = [
    "VectorStore",
    "MilvusStore",
    "AliyunVectorStore",
    "get_milvus_store",
    "get_vector_store",
]

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Milvus 单例 (向后兼容)
# ------------------------------------------------------------------

_milvus_store_instance: MilvusStore = None
_milvus_lock = threading.Lock()


def get_milvus_store() -> MilvusStore:
    """获取 MilvusStore 单例实例，避免重复创建连接"""
    global _milvus_store_instance
    
    if _milvus_store_instance is not None:
        return _milvus_store_instance
    
    with _milvus_lock:
        if _milvus_store_instance is not None:
            return _milvus_store_instance
        _milvus_store_instance = MilvusStore()
        return _milvus_store_instance


# ------------------------------------------------------------------
# 通用向量存储工厂 (根据 config.vector_store_type 切换后端)
# ------------------------------------------------------------------

_vector_store_instance: VectorStore = None
_vector_store_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    """
    根据配置获取向量存储单例。
    
    支持的后端:
        - milvus  (默认) → MilvusStore
        - aliyun          → AliyunVectorStore (阿里云 OSS)
        - faiss / pgvector → 暂未实现，回退到 Milvus
    
    返回:
        VectorStore: 向量存储实例
    """
    global _vector_store_instance
    
    if _vector_store_instance is not None:
        return _vector_store_instance
    
    with _vector_store_lock:
        if _vector_store_instance is not None:
            return _vector_store_instance
        
        from app.config import get_settings
        settings = get_settings()
        store_type = settings.vector_store_type
        
        if store_type == "aliyun":
            logger.info("使用阿里云 OSS 向量存储后端")
            _vector_store_instance = AliyunVectorStore()
        elif store_type == "milvus":
            logger.info("使用 Milvus 向量存储后端")
            _vector_store_instance = get_milvus_store()
        else:
            logger.warning(
                f"向量存储类型 '{store_type}' 暂未实现，回退到 Milvus"
            )
            _vector_store_instance = get_milvus_store()
        
        return _vector_store_instance
