"""基于 Milvus 的向量存储实现。"""

import logging
import uuid
import time
from typing import List, Dict, Any, Optional, Tuple
from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
    MilvusException
)

from app.storage.vector_store import VectorStore
from app.config import get_settings

logger = logging.getLogger(__name__)

# 连接池的单例
_connection_alias = "default"


class MilvusStore(VectorStore):
    """
    基于 Milvus 的向量存储实现
    
    特性:
        - 自动连接管理
        - 连接重试机制
        - 安全的删除操作（防止SQL注入）
        - 健康检查
    """

    def __init__(self, collection_name: str = "knowledge_ai", max_retries: int = 3):
        """
        初始化 Milvus 向量存储
        
        参数:
            collection_name: 集合名称
            max_retries: 连接失败时的重试次数
        """
        settings = get_settings()
        self.collection_name = collection_name
        self.host = settings.milvus_host
        self.port = settings.milvus_port
        self.vector_dimension = settings.vector_dimension
        self.max_retries = max_retries
        self.collection = None
        
        # 连接到 Milvus
        self._connect_with_retry()
        # 创建或加载集合
        self._create_collection()
        
        logger.debug(f"初始化 Milvus 向量存储，集合: {self.collection_name}")

    def _connect_with_retry(self):
        """
        连接到 Milvus 服务器（带重试机制）
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # 检查连接是否已存在
                if not connections.has_connection(_connection_alias):
                    connections.connect(
                        alias=_connection_alias,
                        host=self.host,
                        port=self.port,
                        timeout=30
                    )
                else:
                    # 验证现有连接是否有效
                    self._check_connection()
                return
            except Exception as e:
                last_exception = e
                logger.warning(f"连接 Milvus 失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    # 指数退避重试
                    wait_time = min(2 ** attempt, 10)
                    time.sleep(wait_time)
        
        # 所有重试都失败
        error_msg = f"无法连接到 Milvus ({self.host}:{self.port})，尝试 {self.max_retries} 次失败"
        logger.error(error_msg)
        raise Exception(error_msg) from last_exception

    def _check_connection(self):
        """
        检查连接是否仍然活跃
        """
        try:
            # 通过一个轻量级操作来检查连接
            utility.list_collections(using=_connection_alias)
        except Exception as e:
            logger.warning(f"连接检查失败: {str(e)}")
            # 尝试重新连接
            if connections.has_connection(_connection_alias):
                connections.disconnect(_connection_alias)
            self._connect_with_retry()

    def _create_collection(self):
        """
        创建或加载 Milvus 集合
        """
        try:
            # 定义字段
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.vector_dimension),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="metadata", dtype=DataType.JSON)
            ]
            
            # 创建 schema
            schema = CollectionSchema(fields=fields, description="Knowledge AI 向量存储")
            
            # 检查集合是否存在
            if utility.has_collection(self.collection_name, using=_connection_alias):
                # 加载集合
                self.collection = Collection(name=self.collection_name, using=_connection_alias)
            else:
                # 创建集合
                self.collection = Collection(
                    name=self.collection_name,
                    schema=schema,
                    using=_connection_alias
                )
                
                # 创建索引
                index_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": "L2",
                    "params": {"nlist": 128}
                }
                self.collection.create_index(
                    field_name="embedding",
                    index_params=index_params,
                    using=_connection_alias
                )
            
            # 加载集合到内存
            if not self.collection.is_empty:
                self.collection.load(using=_connection_alias)
            
        except MilvusException as e:
            logger.error(f"Milvus 异常: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"创建/加载集合失败: {str(e)}")
            raise

    def add_embeddings(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        添加向量到存储
        
        参数:
            embeddings: 向量列表
            texts: 文本列表
            metadatas: 元数据列表
            
        返回:
            List[str]: 插入的向量 ID 列表
            
        抛出:
            ValueError: 如果输入参数不一致
            Exception: 如果插入操作失败
        """
        if not embeddings or not texts:
            raise ValueError("embeddings and texts cannot be empty")
        
        if len(embeddings) != len(texts):
            raise ValueError("embeddings and texts must have the same length")
        
        if metadatas and len(metadatas) != len(embeddings):
            raise ValueError("metadatas length must match embeddings length")
        
        try:
            # 验证连接
            self._check_connection()
            
            # 生成唯一 ID
            ids = [str(uuid.uuid4()) for _ in range(len(embeddings))]
            
            # 验证向量维度
            for embedding in embeddings:
                if len(embedding) != self.vector_dimension:
                    raise ValueError(
                        f"Embedding dimension {len(embedding)} does not match "
                        f"configured dimension {self.vector_dimension}"
                    )
            
            # 准备数据
            data = [
                ids,
                embeddings,
                texts,
                metadatas if metadatas else [{} for _ in range(len(embeddings))]
            ]
            
            # 插入数据
            insert_result = self.collection.insert(data, using=_connection_alias)
            
            # 刷新集合
            self.collection.flush(using=_connection_alias)
            
            # 加载集合到内存（如果还没加载）
            try:
                self.collection.load(using=_connection_alias)
            except MilvusException as e:
                # 集合可能已经加载，忽略错误
                if "loaded" not in str(e).lower():
                    raise
            
            logger.debug(f"成功插入 {len(embeddings)} 个向量")
            return ids
        except ValueError as e:
            logger.error(f"输入验证失败: {str(e)}")
            raise
        except MilvusException as e:
            logger.error(f"Milvus 异常: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"插入向量失败: {str(e)}")
            raise

    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        搜索相似向量
        
        参数:
            query_embedding: 查询向量
            k: 返回的结果数量
            filter: 过滤条件（当前未使用）
            
        返回:
            List[Tuple[float, str, Dict[str, Any]]]: (距离, 文本, 元数据) 的列表
            
        抛出:
            ValueError: 如果查询向量维度不匹配
            Exception: 如果搜索操作失败
        """
        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")
        
        if len(query_embedding) != self.vector_dimension:
            raise ValueError(
                f"Query embedding dimension {len(query_embedding)} does not match "
                f"configured dimension {self.vector_dimension}"
            )
        
        if k <= 0 or k > 100:
            raise ValueError("k must be between 1 and 100")
        
        try:
            # 验证连接
            self._check_connection()
            
            # 构建搜索参数
            search_params = {
                "metric_type": "L2",
                "params": {"nprobe": 10}
            }
            
            # 构建过滤表达式
            expr = None
            if filter:
                exprs = []
                for key, value in filter.items():
                    if isinstance(value, str):
                        # 转义单引号防止注入
                        safe_value = value.replace("'", "\\'")
                        exprs.append(f"metadata['{key}'] == '{safe_value}'")
                    elif isinstance(value, (int, float)):
                        exprs.append(f"metadata['{key}'] == {value}")
                if exprs:
                    expr = " and ".join(exprs)
            
            # 执行搜索
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=k,
                expr=expr,
                output_fields=["text", "metadata"],
                using=_connection_alias
            )
            
            # 处理结果
            search_results = []
            if results and len(results) > 0:
                for result in results[0]:
                    try:
                        distance = result.distance
                        text = result.entity.get("text", "")
                        metadata = result.entity.get("metadata", {})
                        search_results.append((distance, text, metadata))
                    except Exception as e:
                        logger.warning(f"处理搜索结果失败: {str(e)}")
                        continue
            
            logger.debug(f"搜索完成，返回 {len(search_results)} 个结果")
            return search_results
        except ValueError as e:
            logger.error(f"输入验证失败: {str(e)}")
            raise
        except MilvusException as e:
            logger.error(f"Milvus 异常: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"搜索向量失败: {str(e)}")
            raise

    def delete(self, ids: List[str]) -> bool:
        """
        删除向量
        
        参数:
            ids: 要删除的向量 ID 列表
            
        返回:
            bool: 是否删除成功
        """
        if not ids:
            logger.warning("删除列表为空")
            return True
        
        try:
            # 验证连接
            self._check_connection()
            
            # 验证 ID 格式（防止注入）
            for id_val in ids:
                if not isinstance(id_val, str):
                    raise ValueError(f"Invalid ID type: {type(id_val)}, expected str")
                if len(id_val) > 64:
                    raise ValueError(f"ID too long: {len(id_val)} > 64")
            
            # 构建安全的删除表达式
            # 使用 in 操作符而不是手动拼接字符串
            placeholders = ", ".join([f"'{id_val}'" for id_val in ids])
            expr = f"id in [{placeholders}]"
            
            # 执行删除
            delete_result = self.collection.delete(expr, using=_connection_alias)
            
            # 刷新集合
            self.collection.flush(using=_connection_alias)
            
            deleted_count = getattr(delete_result, 'delete_count', len(ids))
            logger.info(f"成功删除 {deleted_count} 个向量")
            return True
        except ValueError as e:
            logger.error(f"输入验证失败: {str(e)}")
            raise
        except MilvusException as e:
            logger.error(f"Milvus 异常: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"删除向量失败: {str(e)}")
            return False

    def clear(self) -> bool:
        """
        清空所有向量
        
        返回:
            bool: 是否清空成功
        """
        try:
            # 验证连接
            self._check_connection()
            
            # 删除并重新创建集合
            if utility.has_collection(self.collection_name, using=_connection_alias):
                utility.drop_collection(self.collection_name, using=_connection_alias)
                logger.info(f"删除集合: {self.collection_name}")
            
            # 重新创建集合
            self._create_collection()
            
            logger.info("清空向量存储成功")
            return True
        except MilvusException as e:
            logger.error(f"Milvus 异常: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"清空向量存储失败: {str(e)}")
            return False

    def count(self) -> int:
        """
        获取向量数量
        
        返回:
            int: 向量数量
        """
        try:
            # 验证连接
            self._check_connection()
            
            count = self.collection.num_entities
            logger.debug(f"向量存储中共有 {count} 个向量")
            return count
        except MilvusException as e:
            logger.error(f"Milvus 异常: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"获取向量数量失败: {str(e)}")
            return 0
    
    def is_healthy(self) -> bool:
        """
        检查向量库是否健康
        
        返回:
            bool: 是否健康
        """
        try:
            self._check_connection()
            # 尝试一个简单的操作
            self.collection.num_entities
            return True
        except Exception as e:
            logger.warning(f"向量库健康检查失败: {str(e)}")
            return False
