"""模型文档的Pydantic schemas。"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== 文档 Schemas ====================
class DocumentBase(BaseModel):
    """别文档schema基类。"""

    file_name: str
    vendor: Optional[str] = None
    category: Optional[str] = None
    package: Optional[str] = None
    product_name: Optional[str] = None


class DocumentCreate(DocumentBase):
    """文档上传的schema。"""

    pass


class DocumentUpdate(BaseModel):
    """文档更新的schema。"""

    vendor: Optional[str] = None
    category: Optional[str] = None
    package: Optional[str] = None
    product_name: Optional[str] = None


class DocumentResponse(DocumentBase):
    """文档响应的schema。"""

    id: str
    file_path: str
    file_size: Optional[int] = None
    processed: str
    page_count: Optional[int] = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应。"""

    total: int
    items: List[DocumentResponse]


# ==================== 分块 Schemas ====================
class ChunkResponse(BaseModel):
    """分块响应的schema。"""

    id: str
    doc_id: str
    chunk_text: str
    chunk_index: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    content_type: Optional[str] = None
    is_table: int = 0
    is_image: int = 0

    class Config:
        from_attributes = True


# ==================== RAG 查询 Schemas ====================
class RAGQuery(BaseModel):
    """RAG查询请求。"""

    question: str
    top_k: int = Field(default=5, ge=1, le=20)
    use_rerank: bool = True
    return_chunks: bool = True
    filters: Optional[dict] = None


class RetrievedChunk(BaseModel):
    """来自向量库的分块。"""

    chunk_id: str
    chunk_text: str
    similarity_score: float
    doc_name: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None


class RAGResponse(BaseModel):
    """RAG查询响应。"""

    question: str
    answer: str
    retrieved_chunks: List[RetrievedChunk]
    confidence_score: float = Field(ge=0, le=1)
    tokens_used: int
    processing_time_ms: float


# ==================== 健康检查 Schemas ====================
class HealthStatus(BaseModel):
    """服务健康状态。"""

    status: str  # 服务状态: healthy, degraded, unhealthy
    database: str
    vector_store: str
    embeddings_service: str
    timestamp: datetime


# ==================== 错误 Schemas ====================
class ErrorResponse(BaseModel):
    """标准错误响应。"""

    error: str
    detail: str
    code: int
