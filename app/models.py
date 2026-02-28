"""数据库模型定义。"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Text, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
import uuid

from app.database import Base


class Document(Base):
    """文档元数据模型。"""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String(255), nullable=False, unique=True, index=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # 字节
    
    # 元数据
    vendor = Column(String(100), index=True)  # 厂商 e.g. "Intel", "TSMC"
    category = Column(String(100), index=True)  # 芯片类型 e.g. "CPU", "GPU", "MCU"
    package = Column(String(100))  # 封装 e.g. "BGA", "QFP"
    product_name = Column(String(255))  # 产品名称
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 处理状态
    processed = Column(String(20), default="pending")  # 处理状态: pending, processing, completed, failed
    page_count = Column(Integer)  # 总页码
    chunk_count = Column(Integer, default=0)  # 分块数量
    error_message = Column(Text)  # 处理出错信息

    # 关联关系
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    processing_logs = relationship("ProcessingLog", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_vendor_category", "vendor", "category"),
        Index("idx_created_processed", "created_at", "processed"),
    )


class Chunk(Base):
    """文档分块模型，用于RAG。"""

    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    
    # 内容
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer)  # 分块序列号
    page_start = Column(Integer)  # 起始页数
    page_end = Column(Integer)  # 结束页数
    
    # Embedding元数据
    embedding_id = Column(String(100))  # 向量库ID
    embedding_model = Column(String(100))  # 使用的模型
    embedding_dims = Column(Integer)  # Embedding 维数
    
    # 内容分类
    content_type = Column(String(50))  # 内容类型: text, table, image, formula
    is_table = Column(Integer, default=0)  # 是否是表格（整数作为Boolean)
    is_image = Column(Integer, default=0)  # 是否是图片
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联关系
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_doc_chunk", "doc_id", "chunk_index"),
        Index("idx_content_type", "content_type"),
    )


class QueryCache(Base):
    """查询结果缓存模型，用于性能优化。"""

    __tablename__ = "query_cache"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_hash = Column(String(64), unique=True, nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    result_json = Column(Text)  # 缓存的结果
    
    # 元数据
    hit_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    accessed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ttl_seconds = Column(Integer, default=86400)  # 默认24小时

    __table_args__ = (
        Index("idx_accessed_ttl", "accessed_at", "ttl_seconds"),
    )


class ProcessingLog(Base):
    """处理日志和审计跟踪。"""

    __tablename__ = "processing_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_id = Column(String(36), ForeignKey("documents.id"), index=True)
    
    # 日志信息
    operation = Column(String(50), index=True)  # 操作类型: upload, process, embed, index
    status = Column(String(20))  # 状态: success, warning, error
    message = Column(Text)
    duration_seconds = Column(Float)  # 处理时间
    
    # Token与成本
    tokens_used = Column(Integer)
    cost_usd = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # 关联关系
    document = relationship("Document", back_populates="processing_logs")

    __table_args__ = (
        Index("idx_operation_status", "operation", "status"),
        Index("idx_created_operation", "created_at", "operation"),
    )
