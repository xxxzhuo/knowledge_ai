#!/usr/bin/env python
"""
Milvus 向量库初始化脚本

功能:
    - 连接到 Milvus 服务
    - 创建集合
    - 创建索引
    - 设置基本参数
    - 验证配置
"""

import logging
import sys
import time
from typing import Optional, List
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
    MilvusException
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MilvusInitializer:
    """Milvus 初始化器"""
    
    def __init__(self, host: str = "localhost", port: int = 19530, timeout: int = 30):
        """
        初始化 Milvus 初始化器
        
        参数:
            host: Milvus 服务器地址
            port: Milvus 服务器端口
            timeout: 连接超时时间（秒）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.alias = "default"
        
    def wait_for_milvus(self, max_retries: int = 30, retry_interval: int = 2):
        """
        等待 Milvus 服务启动
        
        参数:
            max_retries: 最大重试次数
            retry_interval: 重试间隔（秒）
        """
        logger.info(f"等待 Milvus 服务启动... ({self.host}:{self.port})")
        
        for attempt in range(max_retries):
            try:
                # 尝试连接
                connections.connect(
                    alias=self.alias,
                    host=self.host,
                    port=self.port,
                    timeout=self.timeout
                )
                logger.info("✓ Milvus 服务已启动并连接成功")
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"连接失败，{retry_interval}秒后重试 ({attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(retry_interval)
                else:
                    logger.error(f"✗ 无法连接到 Milvus 服务: {str(e)}")
                    return False
        
        return False
    
    def create_collection(
        self,
        collection_name: str = "knowledge_ai",
        vector_dimension: int = 1536
    ) -> bool:
        """
        创建向量集合
        
        参数:
            collection_name: 集合名称
            vector_dimension: 向量维度
        
        返回:
            bool: 是否成功
        """
        try:
            logger.info(f"检查集合 '{collection_name}'...")
            
            # 检查集合是否已存在
            if utility.has_collection(collection_name, using=self.alias):
                logger.info(f"集合 '{collection_name}' 已存在，跳过创建")
                return True
            
            # 定义集合字段
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.VARCHAR,
                    max_length=64,
                    is_primary=True,
                    description="文档唯一标识"
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=vector_dimension,
                    description="文本向量表示"
                ),
                FieldSchema(
                    name="text",
                    dtype=DataType.VARCHAR,
                    max_length=65535,
                    description="原始文本内容"
                ),
                FieldSchema(
                    name="metadata",
                    dtype=DataType.JSON,
                    description="文档元数据"
                )
            ]
            
            # 创建集合模式
            schema = CollectionSchema(
                fields=fields,
                description="Knowledge AI 向量存储集合"
            )
            
            # 创建集合
            logger.info(f"创建集合 '{collection_name}' (向量维度: {vector_dimension})...")
            collection = Collection(
                name=collection_name,
                schema=schema,
                using=self.alias
            )
            
            logger.info(f"✓ 集合 '{collection_name}' 创建成功")
            return True
            
        except MilvusException as e:
            logger.error(f"✗ Milvus 异常: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"✗ 创建集合失败: {str(e)}")
            return False
    
    def create_index(
        self,
        collection_name: str = "knowledge_ai",
        index_type: str = "IVF_FLAT",
        metric_type: str = "L2"
    ) -> bool:
        """
        为集合创建索引
        
        参数:
            collection_name: 集合名称
            index_type: 索引类型 (IVF_FLAT, IVF_SQ8, HNSW, etc.)
            metric_type: 距离度量类型 (L2, IP, COSINE, etc.)
        
        返回:
            bool: 是否成功
        """
        try:
            logger.info(f"为 '{collection_name}' 创建索引...")
            
            collection = Collection(
                name=collection_name,
                using=self.alias
            )
            
            # 检查索引是否已存在
            indexes = collection.indexes
            if indexes:
                logger.info(f"集合已有索引: {[idx.field_name for idx in indexes]}")
                return True
            
            # 定义索引参数
            index_params = {
                "index_type": index_type,
                "metric_type": metric_type,
                "params": {"nlist": 128}  # 聚类数量
            }
            
            # 创建索引
            logger.info(f"索引参数: {index_params}")
            collection.create_index(
                field_name="embedding",
                index_params=index_params,
                using=self.alias
            )
            
            logger.info(f"✓ 索引创建成功")
            return True
            
        except MilvusException as e:
            logger.error(f"✗ Milvus 异常: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"✗ 创建索引失败: {str(e)}")
            return False
    
    def load_collection(self, collection_name: str = "knowledge_ai") -> bool:
        """
        加载集合到内存
        
        参数:
            collection_name: 集合名称
        
        返回:
            bool: 是否成功
        """
        try:
            logger.info(f"加载集合 '{collection_name}' 到内存...")
            
            collection = Collection(
                name=collection_name,
                using=self.alias
            )
            
            # 检查集合是否已加载
            if collection.num_entities == 0:
                logger.info(f"集合为空，无需加载")
                return True
            
            # 加载集合
            collection.load(using=self.alias)
            
            logger.info(f"✓ 集合加载成功 (实体数: {collection.num_entities})")
            return True
            
        except MilvusException as e:
            logger.error(f"✗ Milvus 异常: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"✗ 加载集合失败: {str(e)}")
            return False
    
    def verify_configuration(self, collection_name: str = "knowledge_ai") -> bool:
        """
        验证 Milvus 配置
        
        返回:
            bool: 配置是否正确
        """
        try:
            logger.info("验证 Milvus 配置...")
            
            # 检查连接
            logger.info(f"✓ 已连接到 Milvus ({self.host}:{self.port})")
            
            # 检查集合
            if utility.has_collection(collection_name, using=self.alias):
                logger.info(f"✓ 集合 '{collection_name}' 存在")
                
                collection = Collection(
                    name=collection_name,
                    using=self.alias
                )
                
                # 显示集合信息
                logger.info(f"  - 字段数: {len(collection.schema.fields)}")
                logger.info(f"  - 实体数: {collection.num_entities}")
                logger.info(f"  - 字段列表: {[f.name for f in collection.schema.fields]}")
                
                # 检查索引
                indexes = collection.indexes
                if indexes:
                    logger.info(f"  - 索引: {[idx.field_name for idx in indexes]}")
                else:
                    logger.warning(f"  - 未创建索引")
                
                return True
            else:
                logger.error(f"✗ 集合 '{collection_name}' 不存在")
                return False
            
        except Exception as e:
            logger.error(f"✗ 验证配置失败: {str(e)}")
            return False
    
    def initialize(
        self,
        collection_name: str = "knowledge_ai",
        vector_dimension: int = 1536
    ) -> bool:
        """
        执行完整的初始化流程
        
        参数:
            collection_name: 集合名称
            vector_dimension: 向量维度
        
        返回:
            bool: 初始化是否成功
        """
        logger.info("=" * 60)
        logger.info("Milvus 向量库初始化")
        logger.info("=" * 60)
        
        # 第1步：等待 Milvus 启动
        if not self.wait_for_milvus():
            return False
        
        # 第2步：创建集合
        if not self.create_collection(collection_name, vector_dimension):
            return False
        
        # 第3步：创建索引
        if not self.create_index(collection_name):
            return False
        
        # 第4步：加载集合
        if not self.load_collection(collection_name):
            return False
        
        # 第5步：验证配置
        if not self.verify_configuration(collection_name):
            return False
        
        logger.info("=" * 60)
        logger.info("✓ Milvus 初始化完成！")
        logger.info("=" * 60)
        
        return True


def main():
    """主函数"""
    import argparse
    from app.config import get_settings
    
    parser = argparse.ArgumentParser(description="Milvus 初始化脚本")
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Milvus 服务器地址 (默认从配置文件读取)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Milvus 服务器端口 (默认从配置文件读取)"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="knowledge_ai",
        help="集合名称"
    )
    parser.add_argument(
        "--dimension",
        type=int,
        default=None,
        help="向量维度 (默认从配置文件读取)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="仅验证配置，不初始化"
    )
    
    args = parser.parse_args()
    
    # 从配置文件读取默认值
    settings = get_settings()
    host = args.host or settings.milvus_host
    port = args.port or settings.milvus_port
    dimension = args.dimension or settings.vector_dimension
    
    # 创建初始化器
    initializer = MilvusInitializer(host=host, port=port)
    
    # 执行初始化或验证
    if args.verify_only:
        success = initializer.wait_for_milvus() and initializer.verify_configuration(args.collection)
    else:
        success = initializer.initialize(args.collection, dimension)
    
    # 返回退出码
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
