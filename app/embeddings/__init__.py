"""Embedding 模块。"""

import threading
from app.embeddings.base import EmbeddingService
from app.embeddings.openai_embedding import OpenAIEmbeddingService
from app.embeddings.ollama_embedding import OllamaEmbeddingService

__all__ = ["EmbeddingService", "OpenAIEmbeddingService", "OllamaEmbeddingService", "get_embedding_service"]

_embedding_service_instance: EmbeddingService = None
_embedding_lock = threading.Lock()


def get_embedding_service() -> EmbeddingService:
    """
    根据配置获取 Embedding 服务单例实例
    
    返回:
        EmbeddingService: 配置的 Embedding 服务实例（全局单例）
    """
    global _embedding_service_instance
    
    if _embedding_service_instance is not None:
        return _embedding_service_instance
    
    with _embedding_lock:
        # Double-check locking
        if _embedding_service_instance is not None:
            return _embedding_service_instance
        
        from app.config import get_settings
        settings = get_settings()
        
        if settings.embedding_service == "ollama":
            _embedding_service_instance = OllamaEmbeddingService(
                model_name=settings.ollama_embedding_model,
                host=settings.ollama_host
            )
        elif settings.embedding_service == "openai":
            _embedding_service_instance = OpenAIEmbeddingService(
                model_name=settings.embedding_model,
                api_key=settings.openai_api_key
            )
        else:
            raise ValueError(f"不支持的 embedding 服务: {settings.embedding_service}")
        
        return _embedding_service_instance

