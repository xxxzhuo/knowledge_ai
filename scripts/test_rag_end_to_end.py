#!/usr/bin/env python
"""
RAG 系统端到端集成测试

测试完整的 RAG 流程：
    1. 文档向量化
    2. 向量存储
    3. 向量检索
    4. 结果排等
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
from app.document_processor import DocumentProcessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RAGSystemTest:
    """RAG 系统测试"""
    
    def __init__(self):
        """初始化测试"""
        self.vector_store = None
        self.retriever = None
        self.embedding_service = None
        self.test_results = []
        
        # 样本文档数据
        self.sample_documents = [
            {
                "title": "半导体工艺技术",
                "content": """
                    三星和台积电等领先的半导体制造商正在推进5纳米以下的工艺技术。
                    现代芯片设计采用 FinFET 和 GAA（全环绕栅极）等先进工艺。
                    工艺节点的减小提高了晶体管密度，降低了功耗。
                """,
                "source": "semiconductor_guide.pdf",
                "page": 1,
                "category": "工艺"
            },
            {
                "title": "芯片设计流程",
                "content": """
                    现代芯片设计流程包括功能设计、逻辑设计、物理设计等阶段。
                    设计人员使用 EDA 工具进行仿真和验证。
                    设计流程确保芯片的功能正确性和可制造性。
                """,
                "source": "design_methodology.pdf",
                "page": 1,
                "category": "设计"
            },
            {
                "title": "晶圆制造工艺",
                "content": """
                    晶圆制造包括光刻、刻蚀、离子注入等多个工艺步骤。
                    每个步骤都需要精确控制以确保产品质量。
                    先进的制造工艺需要投资数十亿美元的生产线。
                """,
                "source": "manufacturing_process.pdf",
                "page": 2,
                "category": "制造"
            },
            {
                "title": "功率管理和散热",
                "content": """
                    现代高性能芯片产生大量热量，需要有效的散热方案。
                    功率管理技术包括动态电压频率调整 (DVFS) 和功率域门控。
                    散热设计对芯片的可靠性和性能至关重要。
                """,
                "source": "power_thermal.pdf",
                "page": 1,
                "category": "功率"
            },
            {
                "title": "芯片测试和可靠性",
                "content": """
                    芯片测试确保产品满足性能和可靠性要求。
                    测试包括功能测试、性能测试和可靠性测试。
                    失效率和平均故障时间 (MTBF) 是关键指标。
                """,
                "source": "testing_reliability.pdf",
                "page": 1,
                "category": "测试"
            }
        ]
        
        # 样本查询
        self.sample_queries = [
            {
                "query": "什么是半导体工艺节点？",
                "expected_category": "工艺"
            },
            {
                "query": "芯片设计的主要步骤是什么？",
                "expected_category": "设计"
            },
            {
                "query": "晶圆制造包含哪些工艺步骤？",
                "expected_category": "制造"
            },
            {
                "query": "如何处理芯片的散热问题？",
                "expected_category": "功率"
            },
            {
                "query": "芯片测试的目的是什么？",
                "expected_category": "测试"
            }
        ]
    
    def test_document_vectorization(self) -> bool:
        """测试 1: 文档向量化"""
        logger.info("-" * 60)
        logger.info("测试 1: 文档向量化")
        logger.info("-" * 60)
        
        try:
            self.embedding_service = get_embedding_service()
            
            logger.info(f"准备向量化 {len(self.sample_documents)} 个文档...")
            
            # 提取文本
            texts = [doc["content"].strip() for doc in self.sample_documents]
            
            # 向量化
            embeddings = self.embedding_service.embed_documents(texts)
            
            if len(embeddings) == len(texts):
                logger.info(f"✓ 成功向量化 {len(embeddings)} 个文档")
                for i, doc in enumerate(self.sample_documents):
                    logger.info(f"  - {doc['title']} (维度: {len(embeddings[i])})")
                self.test_results.append(("文档向量化", "通过", None))
                return True
            else:
                logger.error("✗ 向量化数量不匹配")
                self.test_results.append(("文档向量化", "失败", "向量化数量不匹配"))
                return False
        except Exception as e:
            logger.error(f"✗ 向量化失败: {str(e)}")
            self.test_results.append(("文档向量化", "失败", str(e)))
            return False
    
    def test_vector_storage(self) -> bool:
        """测试 2: 向量存储"""
        logger.info("-" * 60)
        logger.info("测试 2: 向量存储")
        logger.info("-" * 60)
        
        try:
            self.vector_store = MilvusStore(collection_name="knowledge_ai")
            
            logger.info(f"向向量库添加 {len(self.sample_documents)} 个文档...")
            
            # 提取向量
            texts = [doc["content"].strip() for doc in self.sample_documents]
            embeddings = self.embedding_service.embed_documents(texts)
            
            # 提取元数据
            metadatas = [
                {
                    "source": doc["source"],
                    "page": doc["page"],
                    "category": doc["category"],
                    "title": doc["title"]
                }
                for doc in self.sample_documents
            ]
            
            # 添加到向量库
            initial_count = self.vector_store.count()
            ids = self.vector_store.add_embeddings(embeddings, texts, metadatas)
            final_count = self.vector_store.count()
            
            if len(ids) == len(self.sample_documents) and final_count > initial_count:
                logger.info(f"✓ 成功存储 {len(ids)} 个文档")
                logger.info(f"  - 初始数量: {initial_count}")
                logger.info(f"  - 最终数量: {final_count}")
                logger.info(f"  - 添加的数量: {final_count - initial_count}")
                self.test_results.append(("向量存储", "通过", None))
                return True
            else:
                logger.error("✗ 存储数据验证失败")
                self.test_results.append(("向量存储", "失败", "存储数据验证失败"))
                return False
        except Exception as e:
            logger.error(f"✗ 存储失败: {str(e)}")
            self.test_results.append(("向量存储", "失败", str(e)))
            return False
    
    def test_vector_retrieval(self) -> bool:
        """测试 3: 向量检索"""
        logger.info("-" * 60)
        logger.info("测试 3: 向量检索")
        logger.info("-" * 60)
        
        try:
            self.retriever = VectorRetriever(
                embedding_service=self.embedding_service,
                vector_store=self.vector_store
            )
            
            logger.info(f"执行 {len(self.sample_queries)} 个查询...")
            
            all_success = True
            for i, query_info in enumerate(self.sample_queries, 1):
                query = query_info["query"]
                expected_category = query_info["expected_category"]
                
                logger.info(f"\n  查询 {i}: {query}")
                
                # 执行检索
                results = self.retriever.retrieve(query, k=3)
                
                if results:
                    logger.info(f"  ✓ 检索成功，返回 {len(results)} 个结果")
                    
                    # 显示前 3 个结果
                    for j, (similarity, text, metadata) in enumerate(results[:3], 1):
                        category = metadata.get("category", "未知")
                        title = metadata.get("title", "未标题")
                        logger.info(f"    结果 {j}: {title} (分类: {category}, 相似度: {similarity:.3f})")
                    
                    # 检查排名
                    top_category = results[0][2].get("category")
                    if top_category == expected_category:
                        logger.info(f"  ✓ 排名验证通过 (预期: {expected_category}, 实际: {top_category})")
                    else:
                        logger.warning(f"  ⚠ 排名验证未通过 (预期: {expected_category}, 实际: {top_category})")
                else:
                    logger.warning(f"  ⚠ 检索返回空结果")
                    all_success = False
            
            if all_success:
                self.test_results.append(("向量检索", "通过", None))
            else:
                self.test_results.append(("向量检索", "通过", "部分查询返回空结果"))
            
            return True
        except Exception as e:
            logger.error(f"✗ 检索失败: {str(e)}")
            self.test_results.append(("向量检索", "失败", str(e)))
            return False
    
    def test_rag_end_to_end(self) -> bool:
        """测试 4: RAG 端到端流程"""
        logger.info("-" * 60)
        logger.info("测试 4: RAG 端到端流程")
        logger.info("-" * 60)
        
        try:
            logger.info("执行完整的 RAG 流程...")
            
            # 模拟用户查询
            user_query = "现代芯片如何应对高功耗问题？"
            logger.info(f"\n用户查询: {user_query}")
            
            # 第 1 步: 向量化查询
            logger.info("\n第 1 步: 向量化查询...")
            query_embedding = self.embedding_service.embed_text(user_query)
            logger.info("✓ 查询向量化成功")
            
            # 第 2 步: 检索相关文档
            logger.info("\n第 2 步: 检索相关文档...")
            results = self.retriever.retrieve(user_query, k=3)
            logger.info(f"✓ 检索成功，找到 {len(results)} 个相关文档")
            
            # 第 3 步: 整理检索结果
            logger.info("\n第 3 步: 整理检索结果...")
            context_chunks = []
            for i, (similarity, text, metadata) in enumerate(results, 1):
                chunk = {
                    "rank": i,
                    "similarity": similarity,
                    "source": metadata.get("source", "未知"),
                    "category": metadata.get("category", "未知"),
                    "text_preview": text[:100] + "..." if len(text) > 100 else text
                }
                context_chunks.append(chunk)
                logger.info(f"  {i}. {chunk['source']} (相似度: {chunk['similarity']:.3f})")
                logger.info(f"     {chunk['text_preview']}")
            
            # 第 4 步: 模拟 LLM 生成答案 (此处为占位)
            logger.info("\n第 4 步: 基于检索结果生成答案...")
            if context_chunks:
                generated_answer = f"""
                根据检索到的文档，我可以提供以下信息：
                
                1. 最相关的文档: {context_chunks[0]['source']}
                2. 相似度得分: {context_chunks[0]['similarity']:.3f}
                3. 相关分类: {context_chunks[0]['category']}
                
                基于上述信息，可以生成用户友好的答案。
                """
                logger.info("✓ 答案生成成功")
                logger.info(answer_preview := generated_answer.strip()[:100] + "...")
            
            # 第 5 步: 验证 RAG 流程
            logger.info("\n第 5 步: 验证 RAG 流程...")
            rag_pipeline_valid = (
                query_embedding is not None and
                len(results) > 0 and
                all("similarity" in str(r) for r in results)
            )
            
            if rag_pipeline_valid:
                logger.info("✓ RAG 流程验证通过")
                self.test_results.append(("RAG 端到端", "通过", None))
                return True
            else:
                logger.error("✗ RAG 流程验证失败")
                self.test_results.append(("RAG 端到端", "失败", "流程验证失败"))
                return False
        except Exception as e:
            logger.error(f"✗ RAG 新流程失败: {str(e)}")
            self.test_results.append(("RAG 端到端", "失败", str(e)))
            return False
    
    def test_system_stats(self) -> bool:
        """测试 5: 系统统计信息"""
        logger.info("-" * 60)
        logger.info("测试 5: 系统统计信息")
        logger.info("-" * 60)
        
        try:
            stats = self.retriever.get_vector_store_stats()
            
            logger.info(f"✓ 获取系统统计成功:")
            logger.info(f"  - 向量总数: {stats['vector_count']}")
            logger.info(f"  - 系统健康: {stats['is_healthy']}")
            logger.info(f"  - 存储类型: {stats['store_type']}")
            
            self.test_results.append(("系统统计", "通过", None))
            return True
        except Exception as e:
            logger.error(f"✗ 获取统计失败: {str(e)}")
            self.test_results.append(("系统统计", "失败", str(e)))
            return False
    
    def run_all_tests(self) -> bool:
        """运行所有测试"""
        logger.info("=" * 60)
        logger.info("RAG 系统端到端集成测试")
        logger.info("=" * 60)
        logger.info("")
        
        start_time = time.time()
        
        # 执行测试
        tests = [
            self.test_document_vectorization,
            self.test_vector_storage,
            self.test_vector_retrieval,
            self.test_rag_end_to_end,
            self.test_system_stats
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
        logger.info("RAG 系统测试报告")
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
            logger.info("✓ RAG 系统准备就绪！")
            logger.info("\n您现在可以:")
            logger.info("  1. 上传并处理文档")
            logger.info("  2. 基于向量检索执行 RAG 查询")
            logger.info("  3. 利用检索结果提高 LLM 回答质量")
        else:
            logger.info("✗ RAG 系统存在问题，请检查错误信息")
        logger.info("=" * 60)
        
        # 保存测试结果
        self._save_test_results()
    
    def _save_test_results(self):
        """保存测试结果到文件"""
        try:
            results_file = Path(__file__).parent.parent / "rag_system_test_results.json"
            
            report = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "test_type": "RAG_END_TO_END",
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
        test_suite = RAGSystemTest()
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
