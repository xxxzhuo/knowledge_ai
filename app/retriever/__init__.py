"""检索器模块。"""

import threading
from app.retriever.base import Retriever
from app.retriever.vector_retriever import VectorRetriever

__all__ = ["Retriever", "VectorRetriever", "get_vector_retriever"]

_vector_retriever_instance: VectorRetriever = None
_retriever_lock = threading.Lock()


def get_vector_retriever() -> VectorRetriever:
    """获取 VectorRetriever 单例实例，复用 Embedding 服务和 Milvus 连接"""
    global _vector_retriever_instance
    
    if _vector_retriever_instance is not None:
        return _vector_retriever_instance
    
    with _retriever_lock:
        if _vector_retriever_instance is not None:
            return _vector_retriever_instance
        _vector_retriever_instance = VectorRetriever()
        return _vector_retriever_instance
