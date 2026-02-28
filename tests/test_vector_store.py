"""
向量库功能测试

测试向量库的各项功能包括：
- 连接管理
- 添加向量
- 搜索向量
- 删除向量
- 健康检查
"""

import pytest
import logging
from typing import List

from app.storage import MilvusStore, VectorStore
from app.retriever import VectorRetriever
from app.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class TestMilvusStore:
    """Milvus向量库测试"""
    
    @pytest.fixture
    def vector_store(self):
        """创建测试用的向量库实例"""
        store = MilvusStore(collection_name="test_collection")
        yield store
        # 清理：清空测试集合
        try:
            store.clear()
        except Exception as e:
            logger.warning(f"清理测试集合失败: {str(e)}")
    
    def test_connection(self, vector_store):
        """测试连接"""
        assert vector_store.is_healthy()
        logger.info("✓ 连接测试通过")
    
    def test_add_embeddings(self, vector_store):
        """测试添加向量"""
        embeddings = [
            [0.1] * 1536,  # 假设向量维度是1536
            [0.2] * 1536,
        ]
        texts = ["Sample text 1", "Sample text 2"]
        metadatas = [
            {"source": "doc1.pdf"},
            {"source": "doc2.pdf"},
        ]
        
        # 添加向量
        ids = vector_store.add_embeddings(embeddings, texts, metadatas)
        
        assert len(ids) == 2
        assert vector_store.count() >= 2
        logger.info("✓ 添加向量测试通过")
    
    def test_add_embeddings_validation(self, vector_store):
        """测试添加向量时的输入验证"""
        # 测试空向量
        with pytest.raises(ValueError):
            vector_store.add_embeddings([], [], [])
        
        # 测试长度不匹配
        embeddings = [[0.1] * 1536]
        texts = ["text1", "text2"]
        with pytest.raises(ValueError):
            vector_store.add_embeddings(embeddings, texts)
        
        # 测试维度不匹配
        embeddings = [[0.1] * 100]  # 错误的维度
        texts = ["text1"]
        with pytest.raises(ValueError):
            vector_store.add_embeddings(embeddings, texts)
        
        logger.info("✓ 输入验证测试通过")
    
    def test_search(self, vector_store):
        """测试搜索功能"""
        # 添加一些向量
        embeddings = [
            [0.1] * 1536,
            [0.2] * 1536,
            [0.15] * 1536,
        ]
        texts = ["text1", "text2", "text3"]
        metadatas = [
            {"id": "1"},
            {"id": "2"},
            {"id": "3"},
        ]
        vector_store.add_embeddings(embeddings, texts, metadatas)
        
        # 执行搜索
        query_embedding = [0.1] * 1536
        results = vector_store.search(query_embedding, k=2)
        
        assert len(results) <= 2
        assert all(len(result) == 3 for result in results)  # (distance, text, metadata)
        logger.info("✓ 搜索功能测试通过")
    
    def test_search_validation(self, vector_store):
        """测试搜索时的输入验证"""
        # 测试空向量
        with pytest.raises(ValueError):
            vector_store.search([], k=5)
        
        # 测试无效的k值
        with pytest.raises(ValueError):
            vector_store.search([0.1] * 1536, k=0)
        
        with pytest.raises(ValueError):
            vector_store.search([0.1] * 1536, k=101)
        
        # 测试维度不匹配
        with pytest.raises(ValueError):
            vector_store.search([0.1] * 100, k=5)
        
        logger.info("✓ 搜索验证测试通过")
    
    def test_delete(self, vector_store):
        """测试删除向量"""
        # 添加向量
        embeddings = [[0.1] * 1536, [0.2] * 1536]
        texts = ["text1", "text2"]
        ids = vector_store.add_embeddings(embeddings, texts)
        
        initial_count = vector_store.count()
        
        # 删除先删除第一个
        success = vector_store.delete([ids[0]])
        assert success
        
        final_count = vector_store.count()
        assert final_count < initial_count
        logger.info("✓ 删除向量测试通过")
    
    def test_clear(self, vector_store):
        """测试清空集合"""
        # 添加向量
        embeddings = [[0.1] * 1536]
        texts = ["text1"]
        vector_store.add_embeddings(embeddings, texts)
        
        # 清空
        success = vector_store.clear()
        assert success
        assert vector_store.count() == 0
        logger.info("✓ 清空集合测试通过")
    
    def test_count(self, vector_store):
        """测试计数功能"""
        initial_count = vector_store.count()
        
        # 添加向量
        embeddings = [[0.1] * 1536, [0.2] * 1536]
        texts = ["text1", "text2"]
        vector_store.add_embeddings(embeddings, texts)
        
        final_count = vector_store.count()
        assert final_count == initial_count + 2
        logger.info("✓ 计数功能测试通过")
    
    def test_health_check(self, vector_store):
        """测试健康检查"""
        is_healthy = vector_store.is_healthy()
        assert isinstance(is_healthy, bool)
        assert is_healthy
        logger.info("✓ 健康检查测试通过")


class TestVectorRetriever:
    """向量检索器测试"""
    
    @pytest.fixture
    def retriever(self):
        """创建测试用的检索器实例"""
        vector_store = MilvusStore(collection_name="test_retriever_collection")
        retriever = VectorRetriever(vector_store=vector_store)
        yield retriever
        # 清理
        try:
            vector_store.clear()
        except Exception as e:
            logger.warning(f"清理测试集合失败: {str(e)}")
    
    @pytest.fixture
    def sample_data(self, retriever):
        """准备样本数据"""
        # 添加一些样本向量
        embeddings = [
            [0.1] * 1536,
            [0.2] * 1536,
            [0.11] * 1536,
        ]
        texts = [
            "Semiconductor manufacturing process",
            "CMOS technology advances",
            "Manufacturing techniques for semiconductors",
        ]
        metadatas = [
            {"file_name": "doc1.pdf", "page_start": 1},
            {"file_name": "doc2.pdf", "page_start": 2},
            {"file_name": "doc3.pdf", "page_start": 3},
        ]
        
        retriever.vector_store.add_embeddings(embeddings, texts, metadatas)
        return texts
    
    def test_retriever_initialization(self, retriever):
        """测试检索器初始化"""
        assert retriever.vector_store is not None
        assert retriever.embedding_service is not None
        logger.info("✓ 检索器初始化测试通过")
    
    def test_retrieve_with_embedding(self, retriever, sample_data):
        """测试使用向量进行检索"""
        query_embedding = [0.1] * 1536
        results = retriever.retrieve_with_embedding(query_embedding, k=2)
        
        assert len(results) <= 2
        # 每个结果应包括 (相似度, 文本, 元数据)
        for similarity, text, metadata in results:
            assert isinstance(similarity, float)
            assert isinstance(text, str)
            assert isinstance(metadata, dict)
            assert 0 <= similarity <= 1
        
        logger.info("✓ 向量检索测试通过")
    
    def test_retrieve_input_validation(self, retriever):
        """测试检索时的输入验证"""
        # 测试空查询向量
        with pytest.raises(ValueError):
            retriever.retrieve_with_embedding([], k=5)
        
        # 测试无效的k值
        with pytest.raises(ValueError):
            retriever.retrieve_with_embedding([0.1] * 1536, k=0)
        
        logger.info("✓ 检索输入验证测试通过")
    
    def test_vector_store_stats(self, retriever, sample_data):
        """测试获取向量库统计信息"""
        stats = retriever.get_vector_store_stats()
        
        assert "vector_count" in stats
        assert "is_healthy" in stats
        assert "store_type" in stats
        assert stats["vector_count"] == 3
        assert stats["is_healthy"]
        assert stats["store_type"] == "milvus"
        
        logger.info("✓ 向量库统计信息测试通过")


# 性能和集成测试
class TestVectorStorePerformance:
    """向量库性能测试"""
    
    @pytest.fixture
    def vector_store(self):
        """创建测试用的向量库实例"""
        store = MilvusStore(collection_name="test_performance_collection")
        yield store
        try:
            store.clear()
        except Exception as e:
            logger.warning(f"清理测试集合失败: {str(e)}")
    
    def test_batch_insert_performance(self, vector_store):
        """测试批量插入性能"""
        import time
        
        # 创建大量向量
        batch_size = 100
        embeddings = [[0.5] * 1536 for _ in range(batch_size)]
        texts = [f"Document {i}" for i in range(batch_size)]
        metadatas = [{"doc_id": i} for i in range(batch_size)]
        
        start_time = time.time()
        ids = vector_store.add_embeddings(embeddings, texts, metadatas)
        insert_time = time.time() - start_time
        
        assert len(ids) == batch_size
        assert vector_store.count() >= batch_size
        
        logger.info(f"✓ 批量插入性能测试通过 ({insert_time:.2f}s for {batch_size} vectors)")
    
    def test_search_performance(self, vector_store):
        """测试搜索性能"""
        import time
        
        # 准备数据
        embeddings = [[0.5] * 1536 for _ in range(50)]
        texts = [f"Document {i}" for i in range(50)]
        vector_store.add_embeddings(embeddings, texts)
        
        # 测试搜索
        query_embedding = [0.5] * 1536
        
        start_time = time.time()
        results = vector_store.search(query_embedding, k=5)
        search_time = time.time() - start_time
        
        assert len(results) <= 5
        logger.info(f"✓ 搜索性能测试通过 ({search_time*1000:.2f}ms for k=5)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
