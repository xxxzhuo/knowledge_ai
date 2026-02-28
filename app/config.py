"""应用配置管理。"""

from typing import Literal
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """支持环境变量的应用配置类。"""

    # API 配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    api_title: str = "Semiconductor Knowledge AI"
    api_version: str = "0.1.0"

    # 数据库配置
    database_url: str = "postgresql://postgres:password@localhost:5432/knowledge_ai"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # LLM 和 Embedding 配置
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    
    # Ollama LLM 配置
    ollama_llm_model: str = "qwen2.5:7b"
    
    # Embedding 服务配置
    embedding_service: Literal["openai", "ollama"] = "ollama"  # 选择 embedding 服务
    
    # OpenAI Embedding 配置
    embedding_model: str = "text-embedding-3-large"
    embedding_batch_size: int = 32
    
    # Ollama Embedding 配置
    ollama_host: str = "http://localhost:11434"
    ollama_embedding_model: str = "embeddinggemma"
    
    # RAG 配置
    rag_llm_type: Literal["openai", "ollama"] = "ollama"
    rag_temperature: float = 0.1
    rag_top_k: int = 5
    rag_reranker_type: Literal["simple", "cross_encoder", "hybrid"] = "simple"
    rag_prompt_type: str = "default"
    rag_min_similarity: float = 0.3

    # 向量库配置
    vector_store_type: Literal["faiss", "milvus", "pgvector"] = "milvus"
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    vector_dimension: int = 768  # embeddinggemma: 768, text-embedding-3-large: 1536

    # 存储配置
    storage_type: Literal["s3", "minio", "local"] = "local"
    storage_local_path: str = "./data/documents"
    s3_bucket: str = "knowledge-ai"
    s3_endpoint: str = "https://s3.amazonaws.com"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # 监控和日志配置
    langsmith_api_key: str = ""
    langsmith_project_name: str = "semiconductor-rag"
    prometheus_port: int = 8001
    log_level: str = "INFO"
    log_format: str = "json"  # 日志格式: json, text

    # 处理配置
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_tokens_per_doc: int = 50000

    class Config:
        """Pydantic 配置类。"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例。"""
    return Settings()
