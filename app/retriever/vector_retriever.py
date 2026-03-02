"""基于向量相似度的检索器实现。"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from app.retriever.base import Retriever
from app.embeddings import get_embedding_service, EmbeddingService
from app.storage import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


class VectorRetriever(Retriever):
    """
    基于向量相似度的检索器实现
    
    特性:
        - 自动连接管理
        - 健康检查
        - 详细的错误处理和日志记录
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStore] = None
    ):
        """
        初始化向量检索器
        
        参数:
            embedding_service: Embedding 服务实例
            vector_store: 向量存储实例 (支持 Milvus / Aliyun 等后端)
        """
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_store = vector_store or get_vector_store()
        
        logger.info("初始化向量检索器")

    def retrieve(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        根据查询文本检索相关文档
        
        参数:
            query: 查询文本
            k: 返回的结果数量 (1-100)
            filter: 过滤条件
            
        返回:
            List[Tuple[float, str, Dict[str, Any]]]: (相似度, 文本, 元数据) 的列表
            
        抛出:
            ValueError: 如果输入参数不合法
            Exception: 如果检索失败
        """
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        
        if k <= 0 or k > 100:
            raise ValueError("k must be between 1 and 100")
        
        try:
            # 验证向量库健康状态
            if not self.vector_store.is_healthy():
                raise RuntimeError("向量库无法连接或不可用")
            
            # 将查询文本转换为向量
            logger.debug(f"开始对查询文本进行向量化: '{query[:50]}...'")
            query_embedding = self.embedding_service.embed_text(query)
            
            if not query_embedding:
                raise RuntimeError("Embedding 服务返回空向量")
            
            # 使用向量进行检索
            results = self.retrieve_with_embedding(query_embedding, k, filter)
            
            logger.info(f"检索完成，查询: '{query[:50]}...'，返回 {len(results)} 个结果")
            return results
        except ValueError as e:
            logger.error(f"输入验证失败: {str(e)}")
            raise
        except RuntimeError as e:
            logger.error(f"运行时错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"检索失败: {str(e)}", exc_info=True)
            raise

    def retrieve_with_embedding(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        根据查询向量检索相关文档
        
        参数:
            query_embedding: 查询向量
            k: 返回的结果数量 (1-100)
            filter: 过滤条件
            
        返回:
            List[Tuple[float, str, Dict[str, Any]]]: (相似度, 文本, 元数据) 的列表
            
        抛出:
            ValueError: 如果输入参数不合法
            Exception: 如果检索失败
        """
        if not query_embedding or not isinstance(query_embedding, list):
            raise ValueError("Query embedding must be a non-empty list")
        
        if k <= 0 or k > 100:
            raise ValueError("k must be between 1 and 100")
        
        try:
            # 验证向量库健康状态
            if not self.vector_store.is_healthy():
                raise RuntimeError("向量库无法连接或不可用")
            
            logger.debug(f"开始向量搜索，k={k}")
            # 使用向量存储进行搜索
            results = self.vector_store.search(query_embedding, k, filter)
            
            if not results:
                logger.warning("搜索未返回任何结果")
                return []
            
            # 处理相似度得分
            processed_results = []
            for distance, text, metadata in results:
                if text is None or text == "":
                    logger.warning(f"忽略空文本结果，元数据: {metadata}")
                    continue
                
                # 转换 L2 距离为相似度得分（范围 0-1）
                # L2 距离越小，相似度越高
                similarity = 1.0 / (1.0 + distance) if distance >= 0 else 0.0
                processed_results.append((similarity, text, metadata if metadata else {}))
            
            # 按相似度降序排序
            processed_results.sort(key=lambda x: x[0], reverse=True)
            
            logger.debug(f"向量检索完成，返回 {len(processed_results)} 个有效结果")
            return processed_results
        except ValueError as e:
            logger.error(f"输入验证失败: {str(e)}")
            raise
        except RuntimeError as e:
            logger.error(f"运行时错误: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}", exc_info=True)
            raise

    def get_vector_store_stats(self) -> Dict[str, Any]:
        """
        获取向量存储统计信息
        
        返回:
            Dict: 包含向量数量和健康状态的统计信息
        """
        try:
            count = self.vector_store.count()
            is_healthy = self.vector_store.is_healthy()
            store_type = type(self.vector_store).__name__
            return {
                "vector_count": count,
                "is_healthy": is_healthy,
                "store_type": store_type
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return {
                "vector_count": 0,
                "is_healthy": False,
                "error": str(e)
            }
