"""
阿里云 OSS 向量存储实现 (基于 alibabacloud-oss-v2 SDK)

使用阿里云 OSS 原生向量索引能力，实现服务端 ANN 检索，
适用于大规模半导体文档知识库场景 (200K+ PDF, ~48M 向量)。

核心 API:
    - put_vector_index  → 创建向量索引 (指定维度/距离度量)
    - put_vectors       → 批量写入向量
    - query_vectors     → 服务端 ANN 搜索
    - delete_vectors    → 批量删除
    - list_vectors      → 分页列举
    - get_vector_index  → 获取索引信息

依赖:
    pip install alibabacloud-oss-v2
"""

import logging
import uuid
import hashlib
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from app.storage.vector_store import VectorStore
from app.config import get_settings

logger = logging.getLogger(__name__)

# 距离度量映射 (与 Milvus 的 L2 兼容)
DISTANCE_METRIC_L2 = "euclidean"
DISTANCE_METRIC_COSINE = "cosine"
DISTANCE_METRIC_DOT = "dot_product"


class AliyunVectorStore(VectorStore):
    """
    基于阿里云 OSS V2 向量索引的向量存储实现

    特性:
        - 兼容 VectorStore 抽象接口 (add_embeddings, search, delete, clear, count)
        - 服务端 ANN 搜索 (query_vectors)，无需本地加载全部向量
        - 批量写入 (put_vectors)，默认 500 条/批
        - 支持元数据过滤搜索
        - 自动创建向量索引 (首次使用时)
        - is_healthy() 健康检查
    """

    def __init__(
        self,
        collection_name: str = "semiconductordocs",
        vector_dimension: int = None,
        distance_metric: str = DISTANCE_METRIC_L2,
    ):
        """
        初始化阿里云 OSS 向量存储

        参数:
            collection_name: 索引名称 (对应 OSS Vector Index)
            vector_dimension: 向量维度，None 时从配置读取
            distance_metric: 距离度量 (euclidean / cosine / dot_product)
        """
        settings = get_settings()

        self.collection_name = collection_name
        self.vector_dimension = vector_dimension or settings.vector_dimension
        self.batch_size = settings.aliyun_vector_batch_size
        self.distance_metric = distance_metric

        # 阿里云配置
        self._access_key_id = settings.aliyun_oss_access_key_id
        self._access_key_secret = settings.aliyun_oss_access_key_secret
        self._endpoint = settings.aliyun_oss_endpoint
        self._bucket_name = settings.aliyun_oss_bucket_name
        self._region = settings.aliyun_region
        self._account_id = settings.aliyun_account_id

        # 延迟初始化客户端
        self._vector_client = None
        self._client_lock = threading.Lock()
        self._index_ensured = False

        logger.info(
            f"初始化阿里云 OSS 向量存储: index={collection_name}, "
            f"dimension={self.vector_dimension}, bucket={self._bucket_name}, "
            f"region={self._region}"
        )

    # ------------------------------------------------------------------
    # 客户端管理
    # ------------------------------------------------------------------

    def _get_vector_client(self):
        """获取 oss_vectors.Client (延迟初始化，线程安全)"""
        if self._vector_client is not None:
            return self._vector_client

        with self._client_lock:
            if self._vector_client is not None:
                return self._vector_client

            try:
                import alibabacloud_oss_v2 as oss
                import alibabacloud_oss_v2.vectors as oss_vectors
            except ImportError:
                raise ImportError(
                    "alibabacloud-oss-v2 库未安装，请运行:\n"
                    "  pip install alibabacloud-oss-v2"
                )

            # 凭证: 优先使用配置项，回退到环境变量
            if self._access_key_id and self._access_key_secret:
                credentials_provider = oss.credentials.StaticCredentialsProvider(
                    access_key_id=self._access_key_id,
                    access_key_secret=self._access_key_secret,
                )
            else:
                # 从环境变量: OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET
                credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()

            if not self._region:
                raise ValueError(
                    "阿里云 region 未配置，请设置环境变量 ALIYUN_REGION\n"
                    "  例如: cn-shenzhen"
                )

            if not self._account_id:
                raise ValueError(
                    "阿里云 account_id 未配置，请设置环境变量 ALIYUN_ACCOUNT_ID"
                )

            cfg = oss.config.load_default()
            cfg.credentials_provider = credentials_provider
            cfg.region = self._region
            cfg.account_id = self._account_id
            if self._endpoint:
                cfg.endpoint = self._endpoint

            self._vector_client = oss_vectors.Client(cfg)
            logger.info(
                f"成功初始化阿里云 OSS Vector Client: "
                f"region={self._region}, bucket={self._bucket_name}"
            )
            return self._vector_client

    # ------------------------------------------------------------------
    # 索引管理
    # ------------------------------------------------------------------

    def _ensure_index(self):
        """确保向量索引已创建 (幂等)"""
        if self._index_ensured:
            return

        import alibabacloud_oss_v2.vectors as oss_vectors

        client = self._get_vector_client()

        # 先尝试获取索引
        try:
            client.get_vector_index(oss_vectors.models.GetVectorIndexRequest(
                bucket=self._bucket_name,
                index_name=self.collection_name,
            ))
            self._index_ensured = True
            logger.debug(f"向量索引已存在: {self.collection_name}")
            return
        except Exception as e:
            if "NoSuchVectorIndex" not in str(e) and "404" not in str(e):
                # 非"不存在"错误，直接抛出
                logger.warning(f"检查向量索引时出错: {str(e)}")

        # 创建索引
        try:
            client.put_vector_index(oss_vectors.models.PutVectorIndexRequest(
                bucket=self._bucket_name,
                index_name=self.collection_name,
                dimension=self.vector_dimension,
                distance_metric=self.distance_metric,
                data_type="float32",
            ))
            self._index_ensured = True
            logger.info(
                f"创建向量索引: {self.collection_name}, "
                f"dimension={self.vector_dimension}, metric={self.distance_metric}"
            )
        except Exception as e:
            # 可能是并发创建，再试获取一次
            if "Already" in str(e) or "exist" in str(e).lower():
                self._index_ensured = True
                logger.debug(f"向量索引已被并发创建: {self.collection_name}")
            else:
                logger.error(f"创建向量索引失败: {str(e)}")
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
        批量添加向量到阿里云 OSS 向量索引

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

        import alibabacloud_oss_v2.vectors as oss_vectors

        self._ensure_index()
        client = self._get_vector_client()

        # 生成 ID 并构建向量行
        ids = []
        all_rows = []
        for i in range(len(embeddings)):
            text_hash = hashlib.md5(texts[i].encode("utf-8")).hexdigest()[:12]
            unique_id = f"{text_hash}_{uuid.uuid4().hex[:8]}"
            ids.append(unique_id)

            # 构建单条向量行: key + data({float32: [...]}) + metadata
            # 注意: metadata 值只支持 string 类型，总大小 <= 40KB
            meta_dict = {"text": texts[i][:30000]}  # 截断防止超 40KB 限制
            if metadatas[i]:
                for mk, mv in metadatas[i].items():
                    meta_dict[mk] = str(mv) if not isinstance(mv, str) else mv
            row = {
                "key": unique_id,
                "data": {"float32": embeddings[i]},
                "metadata": meta_dict,
            }
            all_rows.append(row)

        # 分批写入
        total = len(all_rows)
        uploaded = 0

        try:
            for batch_start in range(0, total, self.batch_size):
                batch = all_rows[batch_start:batch_start + self.batch_size]

                client.put_vectors(oss_vectors.models.PutVectorsRequest(
                    bucket=self._bucket_name,
                    index_name=self.collection_name,
                    vectors=batch,
                ))
                uploaded += len(batch)

                logger.debug(
                    f"批量上传进度: {min(batch_start + self.batch_size, total)}/{total}"
                )

            logger.info(f"成功写入 {uploaded}/{total} 个向量到 OSS Vector Index")
            return ids

        except Exception as e:
            logger.error(f"批量写入失败 ({uploaded}/{total} 已写入): {str(e)}")
            raise

    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        使用阿里云 OSS 原生向量搜索 (服务端 ANN)

        参数:
            query_embedding: 查询向量
            k: 返回结果数量
            filter: 元数据过滤字典，如 {"brand": "镁光"}

        返回:
            List[Tuple[float, str, Dict]]: (距离, 文本, 元数据) 列表，按距离升序
        """
        if not query_embedding:
            raise ValueError("查询向量不能为空")

        if len(query_embedding) != self.vector_dimension:
            raise ValueError(
                f"查询向量维度 {len(query_embedding)} 与配置维度 {self.vector_dimension} 不一致"
            )

        if k <= 0 or k > 100:
            raise ValueError("k 必须在 1-100 之间")

        import alibabacloud_oss_v2.vectors as oss_vectors

        try:
            self._ensure_index()
            client = self._get_vector_client()

            # 构建查询 – queryVector 直接是 {"float32": [...]}，不需要外层 data
            query_vector = {"float32": query_embedding}

            result = client.query_vectors(oss_vectors.models.QueryVectorsRequest(
                bucket=self._bucket_name,
                index_name=self.collection_name,
                top_k=k,
                query_vector=query_vector,
                filter=filter,
                return_distance=True,
                return_metadata=True,
            ))

            # 解析结果
            search_results = []
            if result.vectors:
                for vec in result.vectors:
                    distance = vec.get("distance", 0.0)
                    metadata = vec.get("metadata", {})
                    # text 存储在 metadata 中
                    text = metadata.pop("text", "")
                    search_results.append((float(distance), text, metadata))

            logger.debug(
                f"OSS 向量搜索完成: top_k={k}, 返回 {len(search_results)} 个结果"
            )
            return search_results

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            raise

    def delete(self, ids: List[str]) -> bool:
        """
        删除指定向量

        参数:
            ids: 要删除的向量 ID (key) 列表

        返回:
            bool: 是否删除成功
        """
        if not ids:
            return True

        import alibabacloud_oss_v2.vectors as oss_vectors

        try:
            self._ensure_index()
            client = self._get_vector_client()

            # 分批删除 (防止单次请求过大)
            for batch_start in range(0, len(ids), self.batch_size):
                batch = ids[batch_start:batch_start + self.batch_size]
                client.delete_vectors(oss_vectors.models.DeleteVectorsRequest(
                    bucket=self._bucket_name,
                    index_name=self.collection_name,
                    keys=batch,
                ))

            logger.info(f"成功删除 {len(ids)} 个向量")
            return True

        except Exception as e:
            logger.error(f"删除向量失败: {str(e)}")
            return False

    def clear(self) -> bool:
        """
        清空集合: 删除向量索引后重新创建

        返回:
            bool: 是否清空成功
        """
        import alibabacloud_oss_v2.vectors as oss_vectors

        try:
            client = self._get_vector_client()

            # 删除索引 (级联删除所有向量)
            try:
                client.delete_vector_index(oss_vectors.models.DeleteVectorIndexRequest(
                    bucket=self._bucket_name,
                    index_name=self.collection_name,
                ))
                logger.info(f"已删除向量索引: {self.collection_name}")
            except Exception as e:
                if "NoSuchVectorIndex" not in str(e) and "404" not in str(e):
                    raise
                logger.debug(f"向量索引不存在，跳过删除: {self.collection_name}")

            # 重新创建索引
            self._index_ensured = False
            self._ensure_index()

            logger.info(f"成功清空并重建集合: {self.collection_name}")
            return True

        except Exception as e:
            logger.error(f"清空集合失败: {str(e)}")
            return False

    def count(self) -> int:
        """
        获取向量数量 (通过分页列举统计)

        返回:
            int: 向量数量
        """
        import alibabacloud_oss_v2.vectors as oss_vectors

        try:
            self._ensure_index()
            client = self._get_vector_client()

            total = 0
            next_token = None

            while True:
                result = client.list_vectors(oss_vectors.models.ListVectorsRequest(
                    bucket=self._bucket_name,
                    index_name=self.collection_name,
                    max_results=1000,
                    next_token=next_token,
                    return_data=False,
                    return_metadata=False,
                ))

                if result.vectors:
                    total += len(result.vectors)

                next_token = result.next_token
                if not next_token:
                    break

            logger.debug(f"向量索引 {self.collection_name} 共有 {total} 个向量")
            return total

        except Exception as e:
            logger.error(f"获取向量数量失败: {str(e)}")
            return 0

    def is_healthy(self) -> bool:
        """
        检查阿里云 OSS 向量服务是否健康

        返回:
            bool: 是否健康
        """
        import alibabacloud_oss_v2.vectors as oss_vectors

        try:
            client = self._get_vector_client()
            client.get_vector_bucket(oss_vectors.models.GetVectorBucketRequest(
                bucket=self._bucket_name,
            ))
            return True
        except Exception as e:
            logger.warning(f"阿里云 OSS 向量服务健康检查失败: {str(e)}")
            return False

    # ------------------------------------------------------------------
    # 云向量 Bucket 检索 (get_by_ids / list_vectors)
    # ------------------------------------------------------------------

    def get_by_ids(
        self,
        ids: List[str],
        return_data: bool = False,
        return_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        根据向量 key 从阿里云 OSS 向量索引精确检索

        调用 SDK get_vectors，可一次获取最多 100 个向量的 data + metadata。
        适用于: 知道文档 ID 后反查原文、批量导出、数据校验等场景。

        参数:
            ids: 向量 key 列表 (对应 add_embeddings 返回的 ID)
            return_data: 是否返回 float32 向量数据 (默认 False，节省带宽)
            return_metadata: 是否返回元数据 (默认 True)

        返回:
            List[Dict]: 每条记录包含:
                - key (str): 向量唯一标识
                - data (dict|None): {"float32": [...]} 或 None
                - metadata (dict|None): 包含 text 和自定义字段
        """
        if not ids:
            return []

        import alibabacloud_oss_v2.vectors as oss_vectors

        try:
            self._ensure_index()
            client = self._get_vector_client()

            all_results: List[Dict[str, Any]] = []

            # SDK 单次最多 100 条，分批处理
            batch_size = min(self.batch_size, 100)
            for batch_start in range(0, len(ids), batch_size):
                batch_keys = ids[batch_start:batch_start + batch_size]

                result = client.get_vectors(oss_vectors.models.GetVectorsRequest(
                    bucket=self._bucket_name,
                    index_name=self.collection_name,
                    keys=batch_keys,
                    return_data=return_data,
                    return_metadata=return_metadata,
                ))

                if result.vectors:
                    all_results.extend(result.vectors)

            logger.info(
                f"按 ID 检索完成: 请求 {len(ids)} 个, 返回 {len(all_results)} 个"
            )
            return all_results

        except Exception as e:
            logger.error(f"按 ID 检索失败: {str(e)}")
            raise

    def list_vectors(
        self,
        max_results: int = 100,
        next_token: Optional[str] = None,
        return_data: bool = False,
        return_metadata: bool = True
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        分页列举阿里云 OSS 向量索引中的向量数据

        调用 SDK list_vectors，支持游标分页，单页最多 1000 条。
        适用于: 数据导出、增量同步、管理面板展示等场景。

        参数:
            max_results: 单页返回数量上限 (1-1000, 默认 100)
            next_token: 上一页返回的分页令牌，首页传 None
            return_data: 是否返回 float32 向量数据 (默认 False)
            return_metadata: 是否返回元数据 (默认 True)

        返回:
            Tuple[List[Dict], Optional[str]]:
                - vectors: 向量记录列表 (key / data / metadata)
                - next_token: 下一页令牌，None 表示已到末页
        """
        max_results = max(1, min(max_results, 1000))

        import alibabacloud_oss_v2.vectors as oss_vectors

        try:
            self._ensure_index()
            client = self._get_vector_client()

            result = client.list_vectors(oss_vectors.models.ListVectorsRequest(
                bucket=self._bucket_name,
                index_name=self.collection_name,
                max_results=max_results,
                next_token=next_token,
                return_data=return_data,
                return_metadata=return_metadata,
            ))

            vectors = result.vectors or []
            token = result.next_token

            logger.debug(
                f"列举向量: 本页 {len(vectors)} 条, "
                f"{'有下一页' if token else '已到末页'}"
            )
            return vectors, token

        except Exception as e:
            logger.error(f"列举向量失败: {str(e)}")
            raise

    def get_texts_by_ids(self, ids: List[str]) -> List[Tuple[str, str, Dict[str, Any]]]:
        """
        便捷方法: 根据向量 ID 获取对应文本和元数据

        参数:
            ids: 向量 key 列表

        返回:
            List[Tuple[str, str, Dict]]: (key, text, metadata) 列表
        """
        records = self.get_by_ids(ids, return_data=False, return_metadata=True)
        results = []
        for rec in records:
            key = rec.get("key", "")
            metadata = rec.get("metadata", {})
            text = metadata.pop("text", "")
            results.append((key, text, metadata))
        return results

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            return {
                "collection": self.collection_name,
                "dimension": self.vector_dimension,
                "distance_metric": self.distance_metric,
                "vector_count": self.count(),
                "bucket": self._bucket_name,
                "region": self._region,
                "backend": "aliyun_oss_vector",
            }
        except Exception as e:
            return {
                "collection": self.collection_name,
                "error": str(e),
                "backend": "aliyun_oss_vector",
            }
