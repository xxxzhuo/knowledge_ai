"""
阿里云 OSS 向量存储实现

基于阿里云 OSS 对象存储实现的向量存储后端，适用于大规模半导体文档知识库场景
（200K+ PDF, ~48M 向量）。

架构设计:
    - 向量数据: JSON 格式存储在 OSS，路径结构为 {prefix}/{collection}/{doc_id}/{chunk_id}.json
    - 索引文件: 每个 collection 一个索引文件 {prefix}/{collection}/_index.json
    - 搜索: 本地暴力搜索(小规模) 或 阿里云向量检索服务(大规模可选)
    - 批量写入: 支持 500-1000 条/批次并发上传

依赖:
    pip install oss2 numpy
"""

import json
import logging
import uuid
import time
import hashlib
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from app.storage.vector_store import VectorStore
from app.config import get_settings

logger = logging.getLogger(__name__)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算余弦相似度"""
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    dot = np.dot(a_arr, b_arr)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


def _l2_distance(a: List[float], b: List[float]) -> float:
    """计算 L2 距离"""
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    return float(np.linalg.norm(a_arr - b_arr))


class AliyunVectorStore(VectorStore):
    """
    基于阿里云 OSS 的向量存储实现
    
    特性:
        - 兼容 VectorStore 抽象接口 (add_embeddings, search, delete, clear, count)
        - 分层目录结构: {prefix}/{collection}/{doc_id}/{chunk_id}.json
        - 批量并发写入 (默认 500 条/批)
        - 支持元数据过滤搜索
        - 线程安全的索引缓存
        - is_healthy() 健康检查
    
    注意:
        搜索默认使用本地暴力检索 (加载所有向量到内存)，
        适合 10 万级以下向量。超过此规模建议对接阿里云向量检索服务。
    """

    def __init__(
        self,
        collection_name: str = "semiconductor_docs",
        vector_dimension: int = None,
        max_workers: int = 8,
    ):
        """
        初始化阿里云 OSS 向量存储
        
        参数:
            collection_name: 集合名称 (对应 OSS 路径前缀下的子目录)
            vector_dimension: 向量维度，None 时从配置读取
            max_workers: 并发上传线程数
        """
        settings = get_settings()
        
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension or settings.vector_dimension
        self.batch_size = settings.aliyun_vector_batch_size
        self.max_workers = max_workers
        
        # OSS 配置
        self._access_key_id = settings.aliyun_oss_access_key_id
        self._access_key_secret = settings.aliyun_oss_access_key_secret
        self._endpoint = settings.aliyun_oss_endpoint
        self._bucket_name = settings.aliyun_oss_bucket_name
        self._prefix = settings.aliyun_oss_prefix
        
        # 延迟初始化 OSS 客户端
        self._bucket = None
        self._bucket_lock = threading.Lock()
        
        # 索引缓存 (内存)
        self._index_cache: Optional[Dict[str, Any]] = None
        self._index_lock = threading.Lock()
        self._index_dirty = False
        
        logger.info(
            f"初始化阿里云 OSS 向量存储: collection={collection_name}, "
            f"dimension={self.vector_dimension}, bucket={self._bucket_name}"
        )

    # ------------------------------------------------------------------
    # OSS 连接管理
    # ------------------------------------------------------------------
    
    def _get_bucket(self):
        """获取 OSS Bucket 对象 (延迟初始化，线程安全)"""
        if self._bucket is not None:
            return self._bucket
        
        with self._bucket_lock:
            if self._bucket is not None:
                return self._bucket
            
            try:
                import oss2
            except ImportError:
                raise ImportError(
                    "oss2 库未安装，请运行: pip install oss2\n"
                    "或在 requirements.txt 中添加 oss2>=2.18.0"
                )
            
            if not self._access_key_id or not self._access_key_secret:
                raise ValueError(
                    "阿里云 OSS 凭证未配置，请设置环境变量:\n"
                    "  ALIYUN_OSS_ACCESS_KEY_ID\n"
                    "  ALIYUN_OSS_ACCESS_KEY_SECRET"
                )
            
            if not self._endpoint or not self._bucket_name:
                raise ValueError(
                    "阿里云 OSS 端点或桶名未配置，请设置环境变量:\n"
                    "  ALIYUN_OSS_ENDPOINT\n"
                    "  ALIYUN_OSS_BUCKET_NAME"
                )
            
            auth = oss2.Auth(self._access_key_id, self._access_key_secret)
            self._bucket = oss2.Bucket(auth, self._endpoint, self._bucket_name)
            
            # 验证连接
            try:
                self._bucket.get_bucket_info()
                logger.info(f"成功连接阿里云 OSS: bucket={self._bucket_name}")
            except Exception as e:
                self._bucket = None
                raise ConnectionError(f"无法连接阿里云 OSS: {str(e)}")
            
            return self._bucket

    # ------------------------------------------------------------------
    # OSS 路径工具
    # ------------------------------------------------------------------
    
    def _vector_key(self, vector_id: str) -> str:
        """生成向量对象的 OSS key"""
        # 使用 ID 前两位做分桶，避免单目录对象过多
        bucket_prefix = vector_id[:2] if len(vector_id) >= 2 else "00"
        return f"{self._prefix}/{self.collection_name}/{bucket_prefix}/{vector_id}.json"

    def _index_key(self) -> str:
        """索引文件的 OSS key"""
        return f"{self._prefix}/{self.collection_name}/_index.json"
    
    def _collection_prefix(self) -> str:
        """集合目录前缀"""
        return f"{self._prefix}/{self.collection_name}/"

    # ------------------------------------------------------------------
    # 索引管理
    # ------------------------------------------------------------------
    
    def _load_index(self) -> Dict[str, Any]:
        """从 OSS 加载索引文件"""
        if self._index_cache is not None:
            return self._index_cache
        
        with self._index_lock:
            if self._index_cache is not None:
                return self._index_cache
            
            try:
                bucket = self._get_bucket()
                result = bucket.get_object(self._index_key())
                data = json.loads(result.read().decode('utf-8'))
                self._index_cache = data
                logger.debug(f"加载索引: {len(data.get('vectors', {}))} 条记录")
                return self._index_cache
            except Exception as e:
                if 'NoSuchKey' in str(e) or '404' in str(e):
                    # 索引不存在，创建空索引
                    self._index_cache = {
                        "collection": self.collection_name,
                        "dimension": self.vector_dimension,
                        "created_at": datetime.utcnow().isoformat(),
                        "vectors": {},  # {id: {text_hash, metadata_keys}}
                        "count": 0,
                    }
                    return self._index_cache
                else:
                    logger.error(f"加载索引失败: {str(e)}")
                    raise

    def _save_index(self):
        """将索引写回 OSS"""
        with self._index_lock:
            if self._index_cache is None:
                return
            
            try:
                bucket = self._get_bucket()
                self._index_cache["updated_at"] = datetime.utcnow().isoformat()
                self._index_cache["count"] = len(self._index_cache.get("vectors", {}))
                data = json.dumps(self._index_cache, ensure_ascii=False)
                bucket.put_object(self._index_key(), data.encode('utf-8'))
                self._index_dirty = False
                logger.debug(f"索引已保存: {self._index_cache['count']} 条记录")
            except Exception as e:
                logger.error(f"保存索引失败: {str(e)}")
                raise

    # ------------------------------------------------------------------
    # VectorStore 接口实现
    # ------------------------------------------------------------------
    
    def add_embeddings(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        批量添加向量到 OSS 存储
        
        参数:
            embeddings: 向量列表
            texts: 对应文本列表
            metadatas: 对应元数据列表
            
        返回:
            List[str]: 插入的向量 ID 列表
        """
        if not embeddings:
            return []
        
        if len(embeddings) != len(texts):
            raise ValueError(
                f"向量数量 ({len(embeddings)}) 和文本数量 ({len(texts)}) 不一致"
            )
        
        # 验证维度
        for i, emb in enumerate(embeddings):
            if len(emb) != self.vector_dimension:
                raise ValueError(
                    f"向量 {i} 维度 {len(emb)} 与配置维度 {self.vector_dimension} 不一致"
                )
        
        if metadatas and len(metadatas) != len(embeddings):
            raise ValueError(
                f"元数据数量 ({len(metadatas)}) 和向量数量 ({len(embeddings)}) 不一致"
            )
        
        if not metadatas:
            metadatas = [{} for _ in range(len(embeddings))]
        
        # 生成 ID
        ids = []
        for i in range(len(embeddings)):
            # 基于内容生成确定性 ID (文本hash + 时间戳后缀)
            text_hash = hashlib.md5(texts[i].encode('utf-8')).hexdigest()[:12]
            unique_id = f"{text_hash}_{uuid.uuid4().hex[:8]}"
            ids.append(unique_id)
        
        # 准备 JSON 对象
        objects_to_upload = []
        for i in range(len(embeddings)):
            obj = {
                "id": ids[i],
                "embedding": embeddings[i],
                "text": texts[i],
                "metadata": metadatas[i],
                "created_at": datetime.utcnow().isoformat(),
            }
            objects_to_upload.append((ids[i], obj))
        
        # 分批并发上传
        total = len(objects_to_upload)
        uploaded = 0
        
        try:
            bucket = self._get_bucket()
            
            for batch_start in range(0, total, self.batch_size):
                batch = objects_to_upload[batch_start:batch_start + self.batch_size]
                
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {}
                    for vec_id, obj in batch:
                        key = self._vector_key(vec_id)
                        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
                        future = executor.submit(bucket.put_object, key, data)
                        futures[future] = vec_id
                    
                    for future in as_completed(futures):
                        try:
                            future.result()
                            uploaded += 1
                        except Exception as e:
                            vec_id = futures[future]
                            logger.error(f"上传向量 {vec_id} 失败: {str(e)}")
                
                logger.debug(
                    f"批量上传进度: {min(batch_start + self.batch_size, total)}/{total}"
                )
            
            # 更新索引
            index = self._load_index()
            for vec_id, obj in objects_to_upload:
                index["vectors"][vec_id] = {
                    "text_len": len(obj["text"]),
                    "metadata_keys": list(obj["metadata"].keys()) if obj["metadata"] else [],
                    "created_at": obj["created_at"],
                }
            self._index_dirty = True
            self._save_index()
            
            logger.info(f"成功上传 {uploaded}/{total} 个向量到 OSS")
            return ids
            
        except Exception as e:
            logger.error(f"批量写入失败: {str(e)}")
            raise

    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        搜索相似向量
        
        当前实现: 从 OSS 加载所有向量数据进行暴力搜索。
        适合 10 万级以下向量。超过此规模应对接阿里云向量检索服务。
        
        参数:
            query_embedding: 查询向量
            k: 返回结果数量
            filter: 元数据过滤字典，如 {"brand": "镁光"}
            
        返回:
            List[Tuple[float, str, Dict]]: (L2距离, 文本, 元数据) 列表，按距离升序
        """
        if not query_embedding:
            raise ValueError("查询向量不能为空")
        
        if len(query_embedding) != self.vector_dimension:
            raise ValueError(
                f"查询向量维度 {len(query_embedding)} 与配置维度 {self.vector_dimension} 不一致"
            )
        
        if k <= 0 or k > 100:
            raise ValueError("k 必须在 1-100 之间")
        
        try:
            # 从索引加载所有向量 ID
            index = self._load_index()
            vector_ids = list(index.get("vectors", {}).keys())
            
            if not vector_ids:
                logger.warning("向量库为空，无搜索结果")
                return []
            
            # 并发加载向量数据
            bucket = self._get_bucket()
            all_vectors = []
            
            def _load_vector(vid: str):
                key = self._vector_key(vid)
                try:
                    result = bucket.get_object(key)
                    return json.loads(result.read().decode('utf-8'))
                except Exception as e:
                    logger.warning(f"加载向量 {vid} 失败: {str(e)}")
                    return None
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(_load_vector, vid): vid for vid in vector_ids}
                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        all_vectors.append(result)
            
            # 元数据过滤
            if filter:
                filtered = []
                for vec in all_vectors:
                    meta = vec.get("metadata", {})
                    match = True
                    for fk, fv in filter.items():
                        if meta.get(fk) != fv:
                            match = False
                            break
                    if match:
                        filtered.append(vec)
                all_vectors = filtered
            
            if not all_vectors:
                return []
            
            # 计算 L2 距离
            q = np.array(query_embedding, dtype=np.float32)
            distances = []
            for vec in all_vectors:
                emb = np.array(vec["embedding"], dtype=np.float32)
                dist = float(np.linalg.norm(q - emb))
                distances.append((dist, vec["text"], vec.get("metadata", {})))
            
            # 按距离升序排序，取 top k
            distances.sort(key=lambda x: x[0])
            results = distances[:k]
            
            logger.debug(f"OSS 搜索完成: 检索 {len(all_vectors)} 个向量，返回 {len(results)} 个结果")
            return results
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise

    def delete(self, ids: List[str]) -> bool:
        """
        删除指定向量
        
        参数:
            ids: 要删除的向量 ID 列表
            
        返回:
            bool: 是否全部删除成功
        """
        if not ids:
            return True
        
        try:
            bucket = self._get_bucket()
            
            # 并发删除 OSS 对象
            deleted = 0
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {}
                for vid in ids:
                    key = self._vector_key(vid)
                    future = executor.submit(bucket.delete_object, key)
                    futures[future] = vid
                
                for future in as_completed(futures):
                    try:
                        future.result()
                        deleted += 1
                    except Exception as e:
                        vid = futures[future]
                        logger.warning(f"删除向量 {vid} 失败: {str(e)}")
            
            # 更新索引
            index = self._load_index()
            for vid in ids:
                index["vectors"].pop(vid, None)
            self._index_dirty = True
            self._save_index()
            
            logger.info(f"成功删除 {deleted}/{len(ids)} 个向量")
            return deleted == len(ids)
            
        except Exception as e:
            logger.error(f"删除向量失败: {str(e)}")
            return False

    def clear(self) -> bool:
        """
        清空集合中的所有向量
        
        返回:
            bool: 是否清空成功
        """
        try:
            bucket = self._get_bucket()
            prefix = self._collection_prefix()
            
            # 列举并删除所有对象 (OSS 批量删除每次最多 1000 个)
            deleted_total = 0
            
            import oss2
            
            while True:
                objects = list(oss2.ObjectIterator(bucket, prefix=prefix, max_keys=1000))
                if not objects:
                    break
                
                keys = [obj.key for obj in objects]
                bucket.batch_delete_objects(keys)
                deleted_total += len(keys)
                logger.debug(f"清空进度: 已删除 {deleted_total} 个对象")
            
            # 重置索引缓存
            with self._index_lock:
                self._index_cache = {
                    "collection": self.collection_name,
                    "dimension": self.vector_dimension,
                    "created_at": datetime.utcnow().isoformat(),
                    "vectors": {},
                    "count": 0,
                }
                self._index_dirty = False
            
            logger.info(f"成功清空集合 {self.collection_name}，共删除 {deleted_total} 个对象")
            return True
            
        except Exception as e:
            logger.error(f"清空集合失败: {str(e)}")
            return False

    def count(self) -> int:
        """
        获取向量数量
        
        返回:
            int: 向量数量
        """
        try:
            index = self._load_index()
            return len(index.get("vectors", {}))
        except Exception as e:
            logger.error(f"获取向量数量失败: {str(e)}")
            return 0

    def is_healthy(self) -> bool:
        """
        检查阿里云 OSS 连接是否健康
        
        返回:
            bool: 是否健康
        """
        try:
            bucket = self._get_bucket()
            bucket.get_bucket_info()
            return True
        except Exception as e:
            logger.warning(f"阿里云 OSS 健康检查失败: {str(e)}")
            return False

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------
    
    def invalidate_cache(self):
        """手动清除索引缓存，下次操作会重新加载"""
        with self._index_lock:
            self._index_cache = None
            logger.debug("索引缓存已清除")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            index = self._load_index()
            return {
                "collection": self.collection_name,
                "dimension": self.vector_dimension,
                "vector_count": len(index.get("vectors", {})),
                "bucket": self._bucket_name,
                "prefix": self._prefix,
                "backend": "aliyun_oss",
            }
        except Exception as e:
            return {
                "collection": self.collection_name,
                "error": str(e),
                "backend": "aliyun_oss",
            }
