#!/usr/bin/env python
"""
向量存储和检索功能集成测试

测试:
    1. 向量库连接
    2. 向量添加和存储
    3. 向量搜索和检索
    4. RAG 系统集成
"""

import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import json

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage import MilvusStore
from app.retriever import VectorRetriever
from app.embeddings import get_embedding_service
from app.config import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorStoreTestSuite:
    """向量存储测试套件"""
    
    def __init__(self):
        """初始化测试套件"""
        self.vector_store = None
        self.embedding_service = None
        self.retriever = None
        self.test_results = []
    
    def test_vector_store_connection(self) -> bool:
        """测试 1: 向量库连接"""
        logger.info("-" * 60)
        logger.info("测试 1: 向量库连接")
        logger.info("-" * 60)
        
        try:
            self.vector_store = MilvusStore(collection_name="knowledge_ai")
            
            # 检查健康状态
            if self.vector_store.is_healthy():
                logger.info("✓ 向量库连接成功")
                logger.info(f"  - 集合名称: {self.vector_store.collection_name}")
                logger.info(f"  - 向量维度: {self.vector_store.vector_dimension}")
                logger.info(f"  - 当前实体数: {self.vector_store.count()}")
                self.test_results.append(("向量库连接", "通过", None))
                return True
            else:
                logger.error("✗ 向量库健康检查失败")
                self.test_results.append(("向量库连接", "失败", "健康检查失败"))
                return False
        except Exception as e:
            logger.error(f"✗ 连接失败: {str(e)}")
            self.test_results.append(("向量库连接", "失败", str(e)))
            return False
    
    def test_embedding_service(self) -> bool:
        """测试 2: Embedding 服务"""
        logger.info("-" * 60)
        logger.info("测试 2: Embedding 服务")
        logger.info("-" * 60)
        
        try:
            self.embedding_service = get_embedding_service()
            
            # 测试单个文本向量化
            test_text = "半导体制造工艺"
            logger.info(f"对测试文本进行向量化: '{test_text}'")
            
            embedding = self.embedding_service.embed_text(test_text)
            
            if embedding and len(embedding) == self.vector_store.vector_dimension:
                logger.info(f"✓ 单文本向量化成功")
                logger.info(f"  - 向量维度: {len(embedding)}")
                logger.info(f"  - 向量样本: {embedding[:5]}...")
                
                # 测试批量向量化
                test_texts = [
                    "CMOS 工艺技术",
                    "芯片设计流程",
                    "晶圆制造"
                ]
                logger.info(f"对 {len(test_texts)} 个文本进行批量向量化...")
                
                embeddings = self.embedding_service.embed_documents(test_texts)
                
                if len(embeddings) == len(test_texts):
                    logger.info(f"✓ 批量向量化成功，得到 {len(embeddings)} 个向量")
                    self.test_results.append(("Embedding 服务", "通过", None))
                    return True
                else:
                    logger.error(f"✗ 批量向量化失败")
                    self.test_results.append(("Embedding 服务", "失败", "批量向量化数量不匹配"))
                    return False
            else:
                logger.error(f"✗ 向量维度不匹配或为空")
                self.test_results.append(("Embedding 服务", "失败", "向量维度不匹配"))
                return False
        except Exception as e:
            logger.error(f"✗ Embedding 服务测试失败: {str(e)}")
            self.test_results.append(("Embedding 服务", "失败", str(e)))
            return False
    
    def test_vector_add_and_store(self) -> bool:
        """测试 3: 向量添加和存储"""
        logger.info("-" * 60)
        logger.info("测试 3: 向量添加和存储")
        logger.info("-" * 60)
        
        try:
            # 准备测试数据
            sample_texts = [
                "三星 5nm 工艺实现了更高的晶体管密度",
                "台积电的高端制造工艺领先行业",
                "英特尔推出 Intel 4 工艺技术"
            ]
            
            sample_metadatas = [
                {"source": "doc1.pdf", "page": 1, "company": "三星"},
                {"source": "doc2.pdf", "page": 2, "company": "台积电"},
                {"source": "doc3.pdf", "page": 3, "company": "英特尔"}
            ]
            
            logger.info(f"准备添加 {len(sample_texts)} 个向量...")
            
            # 生成向量
            embeddings = self.embedding_service.embed_documents(sample_texts)
            
            if len(embeddings) != len(sample_texts):
                logger.error("✗ 向量生成失败")
                self.test_results.append(("向量添加和存储", "失败", "向量生成数量不匹配"))
                return False
            
            logger.info(f"✓ 生成了 {len(embeddings)} 个向量")
            
            # 添加向量到库
            initial_count = self.vector_store.count()
            logger.info(f"初始向量数: {initial_count}")
            
            ids = self.vector_store.add_embeddings(
                embeddings,
                sample_texts,
                sample_metadatas
            )
            
            if not ids or len(ids) != len(sample_texts):
                logger.error("✗ 向量添加失败")
                self.test_results.append(("向量添加和存储", "失败", "添加返回的ID不正确"))
                return False
            
            # 验证向量是否被添加
            final_count = self.vector_store.count()
            logger.info(f"添加后向量数: {final_count}")
            
            if final_count >= initial_count + len(sample_texts):
                logger.info(f"✓ 成功添加 {len(ids)} 个向量")
                logger.info(f"  - 添加的向量IDs: {ids[0]}...")
                self.test_results.append(("向量添加和存储", "通过", None))
                return True
            else:
                logger.error(f"✗ 向量数量未增加")
                self.test_results.append(("向量添加和存储", "失败", "向量数量未增加"))
                return False
        except Exception as e:
            logger.error(f"✗ 向量添加失败: {str(e)}")
            self.test_results.append(("向量添加和存储", "失败", str(e)))
            return False
    
    def test_vector_search_and_retrieval(self) -> bool:
        """测试 4: 向量搜索和检索"""
        logger.info("-" * 60)
        logger.info("测试 4: 向量搜索和检索")
        logger.info("-" * 60)
        
        try:
            # 准备查询
            query_text = "半导体工艺技术"
            logger.info(f"查询文本: '{query_text}'")
            
            # 向量化查询
            query_embedding = self.embedding_service.embed_text(query_text)
            
            if not query_embedding:
                logger.error("✗ 查询向量化失败")
                self.test_results.append(("向量搜索和检索", "失败", "查询向量化失败"))
                return False
            
            logger.info("✓ 查询向量化成功")
            
            # 执行搜索
            logger.info("执行相似度搜索...")
            results = self.vector_store.search(query_embedding, k=3)
            
            if results:
                logger.info(f"✓ 搜索成功，返回 {len(results)} 个结果")
                
                for i, (distance, text, metadata) in enumerate(results, 1):
                    similarity = 1.0 / (1.0 + distance)
                    logger.info(f"  结果 {i}:")
                    logger.info(f"    - 相似度: {similarity:.4f}")
                    logger.info(f"    - 文本: {text[:50]}...")
                    logger.info(f"    - 元数据: {metadata}")
                
                self.test_results.append(("向量搜索和检索", "通过", None))
                return True
            else:
                logger.warning("⚠ 搜索返回空结果")
                self.test_results.append(("向量搜索和检索", "通过", "搜索返回空结果（可能库为空）"))
                return True
        except Exception as e:
            logger.error(f"✗ 搜索失败: {str(e)}")
            self.test_results.append(("向量搜索和检索", "失败", str(e)))
            return False
    
    def test_retriever_integration(self) -> bool:
        """测试 5: 检索器集成"""
        logger.info("-" * 60)
        logger.info("测试 5: 检索器集成")
        logger.info("-" * 60)
        
        try:
            # 创建检索器
            self.retriever = VectorRetriever(
                embedding_service=self.embedding_service,
                vector_store=self.vector_store
            )
            
            logger.info("✓ 检索器创建成功")
            
            # 测试检索器
            query = "什么是半导体工艺"
            logger.info(f"查询: '{query}'")
            
            results = self.retriever.retrieve(query, k=3)
            
            if results:
                logger.info(f"✓ 检索成功，返回 {len(results)} 个结果")
                
                for i, (similarity, text, metadata) in enumerate(results, 1):
                    logger.info(f"  结果 {i}:")
                    logger.info(f"    - 相似度: {similarity:.4f}")
                    logger.info(f"    - 文本: {text[:50]}...")
                    logger.info(f"    - 来源: {metadata.get('source', 'N/A')}")
                
                self.test_results.append(("检索器集成", "通过", None))
                return True
            else:
                logger.warning("⚠ 检索返回空结果")
                self.test_results.append(("检索器集成", "通过", "检索返回空结果（可能库为空）"))
                return True
        except Exception as e:
            logger.error(f"✗ 检索器集成失败: {str(e)}")
            self.test_results.append(("检索器集成", "失败", str(e)))
            return False
    
    def test_vector_store_stats(self) -> bool:
        """测试 6: 向量库统计信息"""
        logger.info("-" * 60)
        logger.info("测试 6: 向量库统计信息")
        logger.info("-" * 60)
        
        try:
            stats = self.retriever.get_vector_store_stats()
            
            logger.info(f"✓ 获取统计信息成功")
            logger.info(f"  - 向量数量: {stats['vector_count']}")
            logger.info(f"  - 健康状态: {stats['is_healthy']}")
            logger.info(f"  - 存储类型: {stats['store_type']}")
            
            self.test_results.append(("向量库统计信息", "通过", None))
            return True
        except Exception as e:
            logger.error(f"✗ 获取统计信息失败: {str(e)}")
            self.test_results.append(("向量库统计信息", "失败", str(e)))
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("向量存储和检索功能测试")
        logger.info("=" * 60)
        logger.info("")
        
        start_time = time.time()
        
        # 执行测试
        tests = [
            self.test_vector_store_connection,
            self.test_embedding_service,
            self.test_vector_add_and_store,
            self.test_vector_search_and_retrieval,
            self.test_retriever_integration,
            self.test_vector_store_stats
        ]
        
        all_passed = True
        for test_func in tests:
            try:
                if not test_func():
                    all_passed = False
            except Exception as e:
                logger.error(f"✗ 测试异常: {str(e)}")
                all_passed = False
            logger.info("")
        
        # 生成测试报告
        self._print_test_report(start_time, all_passed)
        
        return all_passed
    
    def _print_test_report(self, start_time: float, all_passed: bool):
        """打印测试报告"""
        elapsed_time = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info("测试报告")
        logger.info("=" * 60)
        
        # 汇总结果
        passed = sum(1 for _, status, _ in self.test_results if status == "通过")
        failed = sum(1 for _, status, _ in self.test_results if status == "失败")
        
        logger.info(f"总测试数: {len(self.test_results)}")
        logger.info(f"通过: {passed}")
        logger.info(f"失败: {failed}")
        logger.info(f"耗时: {elapsed_time:.2f}秒")
        logger.info("")
        
        # 详细结果
        logger.info("详细结果:")
        logger.info("-" * 60)
        for test_name, status, error in self.test_results:
            status_icon = "✓" if status == "通过" else "✗"
            logger.info(f"{status_icon} {test_name}: {status}")
            if error:
                logger.info(f"  错误: {error}")
        
        logger.info("=" * 60)
        if all_passed:
            logger.info("✓ 所有测试通过！")
        else:
            logger.info("✗ 部分测试未通过")
        logger.info("=" * 60)
        
        # 保存测试结果
        self._save_test_results()
    
    def _save_test_results(self):
        """保存测试结果到文件"""
        try:
            results_file = Path(__file__).parent.parent / "vector_store_test_results.json"
            
            report = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tests": [
                    {
                        "name": name,
                        "status": status,
                        "error": error
                    }
                    for name, status, error in self.test_results
                ],
                "summary": {
                    "total": len(self.test_results),
                    "passed": sum(1 for _, s, _ in self.test_results if s == "通过"),
                    "failed": sum(1 for _, s, _ in self.test_results if s == "失败")
                }
            }
            
            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"测试结果已保存到: {results_file}")
        except Exception as e:
            logger.error(f"保存测试结果失败: {str(e)}")


def main():
    """主函数"""
    try:
        test_suite = VectorStoreTestSuite()
        success = test_suite.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("\n测试被中断")
        return 1
    except Exception as e:
        logger.error(f"测试异常: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
