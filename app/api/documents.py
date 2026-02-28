"""文档管理端点。"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Document, Chunk
from app.schemas import (
    DocumentResponse,
    DocumentCreate,
    DocumentListResponse,
    DocumentUpdate,
    ChunkResponse
)

router = APIRouter()


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    vendor: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """按分页和筛选条件列出文档。

    查询参数：
    - skip: 跳过记录数（分页）
    - limit: 返回记录数
    - vendor: 厂商筛选（可选）
    - category: 类别筛选（可选）
    - status: 处理状态筛选（pending, processing, completed, failed）
    """
    
    query = db.query(Document)
    
    if vendor:
        query = query.filter(Document.vendor == vendor)
    if category:
        query = query.filter(Document.category == category)
    if status:
        query = query.filter(Document.processed == status)
    
    total = query.count()
    documents = query.offset(skip).limit(limit).all()
    
    return DocumentListResponse(
        total=total,
        items=[DocumentResponse.from_orm(doc) for doc in documents]
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: Session = Depends(get_db)
):
    """按文档 ID 获取详情。"""
    
    document = db.query(Document).filter(Document.id == doc_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse.from_orm(document)


@router.get("/documents/{doc_id}/chunks", response_model=list[ChunkResponse])
async def get_document_chunks(
    doc_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取指定文档的分块列表。"""
    
    # 确认文档存在
    document = db.query(Document).filter(Document.id == doc_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunks = db.query(Chunk).filter(
        Chunk.doc_id == doc_id
    ).offset(skip).limit(limit).all()
    
    return [ChunkResponse.from_orm(chunk) for chunk in chunks]


@router.post("/documents", response_model=DocumentResponse)
async def create_document(
    document: DocumentCreate,
    db: Session = Depends(get_db)
):
    """上传并登记新文档。"""
    
    # 检查文档是否已存在
    existing = db.query(Document).filter(
        Document.file_name == document.file_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Document with name '{document.file_name}' already exists"
        )
    
    # 创建新文档
    db_document = Document(
        file_name=document.file_name,
        file_path=f"documents/{document.file_name}",  # TODO: 使用实际的文件路径
        vendor=document.vendor,
        category=document.category,
        package=document.package,
        product_name=document.product_name,
        processed="pending"
    )
    
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    return DocumentResponse.from_orm(db_document)


@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """更新文档元数据。"""
    
    db_document = db.query(Document).filter(Document.id == doc_id).first()
    
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    update_data = document_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_document, field, value)
    
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    return DocumentResponse.from_orm(db_document)


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db)
):
    """删除文档及其关联分块。"""
    
    db_document = db.query(Document).filter(Document.id == doc_id).first()
    
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(db_document)
    db.commit()
    
    return {"message": f"Document {doc_id} deleted successfully"}


@router.get("/documents/stats/summary")
async def documents_statistics(db: Session = Depends(get_db)):
    """获取文档集合统计信息。"""
    
    stats = {
        "total_documents": db.query(func.count(Document.id)).scalar(),
        "processed": db.query(func.count(Document.id)).filter(
            Document.processed == "completed"
        ).scalar(),
        "pending": db.query(func.count(Document.id)).filter(
            Document.processed == "pending"
        ).scalar(),
        "failed": db.query(func.count(Document.id)).filter(
            Document.processed == "failed"
        ).scalar(),
        "total_chunks": db.query(func.count(Chunk.id)).scalar(),
        "vendors": db.query(Document.vendor).distinct().count(),
        "categories": db.query(Document.category).distinct().count(),
    }
    
    return stats
