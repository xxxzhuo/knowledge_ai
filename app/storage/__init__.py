"""存储模块。"""

import threading
from app.storage.vector_store import VectorStore
from app.storage.milvus_store import MilvusStore

__all__ = ["VectorStore", "MilvusStore", "get_milvus_store"]

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
