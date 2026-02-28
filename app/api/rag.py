"""RAG 查询端点。"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import hashlib
import logging
import time

from app.database import get_db
from app.schemas import RAGQuery, RAGResponse, RetrievedChunk
from app.models import QueryCache
from app.retriever import VectorRetriever

router = APIRouter()
logger = logging.getLogger(__name__)


def get_vector_retriever() -> VectorRetriever:
    """
    获取向量检索器实例的依赖注入函数
    
    返回:
        VectorRetriever: 向量检索器实例
    """
    return VectorRetriever()


@router.post("/query", response_model=RAGResponse)
async def query(
    query: RAGQuery,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    vector_retriever: VectorRetriever = Depends(get_vector_retriever)
):
    """RAG 查询端点。返回基于检索到的文档的答案。"""
    
    start_time = time.time()
    
    # 生成查询哈希用于缓存
    query_hash = hashlib.sha256(
        query.question.encode()
    ).hexdigest()
    
    # 检查缓存
    cached = db.query(QueryCache).filter(
        QueryCache.query_hash == query_hash
    ).first()
    
    if cached:
        logger.info(f"缓存命中: {query.question[:50]}")
        # 更新缓存统计
        cached.hit_count += 1
        db.commit()
        
        # 解析缓存结果（TODO: 完成缓存功能后实现）
        # return json.loads(cached.result_json)
    
    try:
        # 实现 RAG 检索逻辑
        # 1. 使用向量检索器检索相关文档
        logger.info(f"开始检索相关文档: {query.question[:50]}")
        retrieved_results = vector_retriever.retrieve(query.question, k=5)
        
        # 2. 构建检索结果
        retrieved_chunks = []
        for similarity, text, metadata in retrieved_results:
            chunk = RetrievedChunk(
                content=text,
                score=similarity,
                source=metadata.get("file_name", "unknown"),
                page=metadata.get("page_start", 0)
            )
            retrieved_chunks.append(chunk)
        
        # 3. 生成响应（占位答案，实际应用中应使用 LLM 生成）
        processing_time = (time.time() - start_time) * 1000  # 转换为毫秒
        
        # 简单的答案生成逻辑（占位）
        if retrieved_chunks:
            answer = f"基于检索到的文档，我可以提供以下信息: {retrieved_chunks[0].content[:100]}..."
            confidence_score = retrieved_chunks[0].score
        else:
            answer = "抱歉，我没有找到与您的问题相关的信息。"
            confidence_score = 0.0
        
        response = RAGResponse(
            question=query.question,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            confidence_score=confidence_score,
            tokens_used=0,
            processing_time_ms=processing_time
        )
        
        # 在后台存储结果
        background_tasks.add_task(
            cache_query_result,
            query_hash,
            query.question,
            response,
            db
        )
        
        return response
    except Exception as e:
        logger.error(f"RAG 查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="查询失败，请稍后重试")


@router.post("/query/batch")
async def batch_query(
    queries: list[RAGQuery],
    db: Session = Depends(get_db),
    vector_retriever: VectorRetriever = Depends(get_vector_retriever)
):
    """批量查询处理端点。"""
    
    results = []
    for q in queries:
        # 为单条查询创建副本以便独立处理
        result = await query(q, BackgroundTasks(), db, vector_retriever)
        results.append(result)
    
    return {
        "total": len(queries),
        "results": results
    }


def cache_query_result(query_hash: str, query_text: str, response, db: Session):
    """将查询结果缓存供未来使用。"""
    try:
        # TODO: 实现缓存逻辑
        logger.debug(f"为查询缓存结果: {query_text[:50]}")
    except Exception as e:
        logger.error(f"缓存查询结果失败: {e}")


@router.get("/retrieval/sources")
async def get_retrieval_sources(
    category: str = None,
    vendor: str = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取可用的检索源。"""
    
    # TODO: 实现检索源列表功能
    return {
        "sources": [],
        "total": 0,
        "filters": {
            "category": category,
            "vendor": vendor
        }
    }
