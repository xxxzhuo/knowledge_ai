"""
文档处理API端点

提供文档上传、处理和管理的接口。
集成了文档加载器、分块器和向量化处理。
"""

import logging
import os
import shutil
from typing import Optional, List
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, Chunk, ProcessingLog
from app.document_processor import DocumentProcessor, ProcessedDocument
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["document-processing"])


# 响应模型
class ChunkInfo(BaseModel):
    """分块信息"""
    chunk_index: int
    content: str
    chunk_type: str
    page_start: int
    page_end: int
    token_count: int
    char_count: int


class TableInfo(BaseModel):
    """表格信息"""
    table_id: int
    page_number: int
    rows: int
    columns: int
    accuracy: Optional[float] = None


class ProcessingResponse(BaseModel):
    """文档处理响应"""
    success: bool
    file_name: str
    file_type: str
    total_chunks: int
    total_tokens: int
    tables_count: int
    images_count: int
    message: str
    processing_time: float


class ProcessingStatusResponse(BaseModel):
    """处理状态响应"""
    document_id: str
    file_name: str
    status: str
    total_chunks: int
    total_tokens: int
    created_at: str
    updated_at: str


# 配置常量
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


@router.post("/process", response_model=ProcessingResponse)
async def process_document(
    file: UploadFile = File(...),
    chunker_type: str = Query("semiconductor", description="分块器类型: semiconductor 或 table_aware"),
    chunk_size: int = Query(1024, ge=100, le=4096),
    chunk_overlap: int = Query(200, ge=0, le=1024),
    enable_ocr: bool = Query(False, description="是否启用OCR"),
    extract_tables: bool = Query(True, description="是否提取表格"),
    extract_images: bool = Query(False, description="是否提取图片"),
    enable_embedding: bool = Query(False, description="是否启用向量化"),
    db: Session = Depends(get_db),
) -> ProcessingResponse:
    """
    处理上传的文档
    
    流程:
        1. 验证文件格式和大小
        2. 保存临时文件
        3. 加载和解析文档
        4. 提取表格和图片
        5. 对内容进行分块
        6. 保存到数据库
        7. 返回处理结果
    
    参数:
        - file: 上传的文件
        - chunker_type: 分块器类型
        - chunk_size: 分块大小
        - chunk_overlap: 分块重叠
        - enable_ocr: 是否启用OCR
        - extract_tables: 是否提取表格
        - extract_images: 是否提取图片
    
    返回:
        处理结果，包括分块数量、token数等
    """
    import time
    start_time = time.time()

    try:
        # 第1步：验证文件
        _validate_file(file)

        # 第2步：保存临时文件
        with TemporaryDirectory() as temp_dir:
            temp_file_path = await _save_temp_file(file, temp_dir)

            # 第3步：初始化处理器并处理文档
            processor = DocumentProcessor(
                chunker_type=chunker_type,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                enable_ocr=enable_ocr,
                extract_tables=extract_tables,
                extract_images=extract_images,
                enable_embedding=enable_embedding,
            )

            processed_doc = processor.process(str(temp_file_path))

            # 第4步：保存到数据库
            doc_id = _save_to_database(processed_doc, db)

            processing_time = time.time() - start_time

            logger.debug(
                f"文档处理成功: {file.filename}, "
                f"耗时: {processing_time:.2f}s, "
                f"分块: {processed_doc.total_chunks}, "
                f"Tokens: {processed_doc.total_tokens}"
            )

            return ProcessingResponse(
                success=True,
                file_name=processed_doc.file_name,
                file_type=processed_doc.file_type,
                total_chunks=processed_doc.total_chunks,
                total_tokens=processed_doc.total_tokens,
                tables_count=len(processed_doc.tables),
                images_count=len(processed_doc.images),
                message=f"文档处理成功，耗时 {processing_time:.2f} 秒",
                processing_time=processing_time,
            )

    except ValueError as e:
        logger.error(f"文件验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文档处理失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"文档处理失败: {str(e)}"
        )


@router.post("/batch-process")
async def batch_process(
    files: List[UploadFile] = File(...),
    chunker_type: str = Query("semiconductor"),
    chunk_size: int = Query(1024, ge=100, le=4096),
    chunk_overlap: int = Query(200, ge=0, le=1024),
    db: Session = Depends(get_db),
):
    """
    批量处理多个文档
    
    参数:
        - files: 上传的文件列表
        - chunker_type: 分块器类型
        - chunk_size: 分块大小
        - chunk_overlap: 分块重叠
    
    返回:
        批量处理结果
    """
    results = []
    errors = []

    processor = DocumentProcessor(
        chunker_type=chunker_type,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    for file in files:
        try:
            _validate_file(file)

            with TemporaryDirectory() as temp_dir:
                temp_file_path = await _save_temp_file(file, temp_dir)
                processed_doc = processor.process(str(temp_file_path))
                doc_id = _save_to_database(processed_doc, db)

                results.append({
                    "file_name": processed_doc.file_name,
                    "status": "success",
                    "chunks": processed_doc.total_chunks,
                    "tokens": processed_doc.total_tokens,
                    "document_id": doc_id,
                })

        except Exception as e:
            logger.error(f"处理文件失败: {file.filename}, 错误: {str(e)}")
            errors.append({
                "file_name": file.filename,
                "status": "failed",
                "error": str(e),
            })

    return {
        "total": len(files),
        "success": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@router.get("/processing-status/{document_id}")
async def get_processing_status(
    document_id: str,
    db: Session = Depends(get_db),
) -> ProcessingStatusResponse:
    """
    获取文档处理状态
    
    参数:
        - document_id: 文档ID
    
    返回:
        处理状态信息
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    chunk_count = db.query(Chunk).filter(Chunk.doc_id == document_id).count()

    return ProcessingStatusResponse(
        document_id=str(document.id),
        file_name=document.file_name,
        status=document.processed,
        total_chunks=document.chunk_count,
        total_tokens=0,  # 可从 Chunk 表统计
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
    )


@router.get("/document-chunks/{document_id}")
async def get_document_chunks(
    document_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    获取文档的分块列表
    
    参数:
        - document_id: 文档ID
        - skip: 跳过记录数
        - limit: 返回记录数
    
    返回:
        分块列表
    """
    chunks = db.query(Chunk).filter(
        Chunk.doc_id == document_id
    ).offset(skip).limit(limit).all()

    total = db.query(Chunk).filter(Chunk.doc_id == document_id).count()

    return {
        "total": total,
        "chunks": [
            {
                "chunk_id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
                "content": chunk.chunk_text[:200] + "...",  # 预览
                "content_full": chunk.chunk_text,
                "type": chunk.content_type,
            }
            for chunk in chunks
        ],
    }


# 辅助函数

def _validate_file(file: UploadFile) -> None:
    """
    验证上传的文件
    
    参数:
        - file: 上传的文件对象
    
    抛出:
        ValueError: 如果文件验证失败
    """
    # 检查文件扩展名
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"不支持的文件格式: {file_ext}. "
            f"支持的格式: {', '.join(ALLOWED_EXTENSIONS)}"
        )




async def _save_temp_file(file: UploadFile, temp_dir: str) -> Path:
    """
    保存上传的文件到临时目录
    
    参数:
        - file: 上传的文件对象
        - temp_dir: 临时目录路径
    
    返回:
        Path: 保存的文件路径
    """
    temp_path = Path(temp_dir) / file.filename

    try:
        # 读取上传的文件内容
        contents = await file.read()

        # 检查文件大小
        if len(contents) > MAX_FILE_SIZE:
            raise ValueError(f"文件过大，最大允许 {MAX_FILE_SIZE / 1024 / 1024:.0f}MB")

        # 保存到临时文件
        with open(temp_path, 'wb') as f:
            f.write(contents)

        return temp_path

    except Exception as e:
        logger.error(f"保存临时文件失败: {str(e)}")
        raise


def _save_to_database(
    processed_doc: ProcessedDocument,
    db: Session,
) -> str:
    """
    将处理结果保存到数据库
    
    参数:
        - processed_doc: 处理后的文档对象
        - db: 数据库会话
    
    返回:
        str: 保存的文档ID
    """
    import uuid
    from datetime import datetime

    try:
        # 创建文档记录
        doc_id = str(uuid.uuid4())
        document = Document(
            id=doc_id,
            file_name=processed_doc.file_name,
            file_path=processed_doc.metadata.get("file_path", ""),
            file_size=processed_doc.metadata.get("file_size", 0),
            vendor=processed_doc.metadata.get("vendor", ""),
            category=processed_doc.metadata.get("category", ""),
            package=processed_doc.metadata.get("package", ""),
            product_name=processed_doc.metadata.get("product_name", ""),
            processed="completed",
            page_count=processed_doc.metadata.get("page_count", 1),
            chunk_count=processed_doc.total_chunks,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(document)

        # 创建分块记录
        for chunk_data in processed_doc.chunks:
            chunk = Chunk(
                id=str(uuid.uuid4()),
                doc_id=doc_id,
                chunk_text=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
                page_start=chunk_data.get("page_start", 1),
                page_end=chunk_data.get("page_end", 1),
                content_type=chunk_data["chunk_type"],
                is_table=chunk_data["chunk_type"] == "table",
                is_image=chunk_data["chunk_type"] == "image",
                created_at=datetime.utcnow(),
            )
            db.add(chunk)

        # 记录处理日志
        log = ProcessingLog(
            id=str(uuid.uuid4()),
            operation="document_process",
            status="completed",
            message=f"成功处理文档: {processed_doc.file_name}",
            tokens_used=processed_doc.total_tokens,
            created_at=datetime.utcnow(),
        )
        db.add(log)

        # 提交事务
        db.commit()

        return doc_id

    except Exception as e:
        db.rollback()
        logger.error(f"保存到数据库失败: {str(e)}")
        raise
