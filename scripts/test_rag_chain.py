#!/usr/bin/env python
"""
RAG Chain 端到端测试

测试:
    1. 基础 RAG 查询
    2. 重排序器功能
    3. 流式输出
    4. 多轮对话
    5. 不同 prompt 类型
"""

import logging
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag import RAGChain, create_rag_chain, get_reranker
from app.config import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_rag():
    """测试基础 RAG 查询"""
    logger.info("=" * 60)
    logger.info("测试 1: 基础 RAG 查询")
    logger.info("=" * 60)
    
    try:
        # 创建 RAG Chain
        chain = create_rag_chain(
            llm_type="ollama",
            reranker_type="simple",
            prompt_type="default"
        )
        
        # 测试查询
        query = "什么是半导体工艺技术？"
        logger.info(f"\n问题: {query}")
        
        answer = chain.invoke(query)
        
        logger.info(f"\n回答:\n{answer}\n")
        logger.info("✓ 基础 RAG 查询测试通过")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 基础 RAG 查询测试失败: {str(e)}", exc_info=True)
        return False


def test_reranker():
    """测试重排序器"""
    logger.info("=" * 60)
    logger.info("测试 2: 重排序器功能")
    logger.info("=" * 60)
    
    try:
        # 创建带重排序的 RAG Chain
        chain = RAGChain(
            reranker=get_reranker("simple", min_similarity=0.4),
            llm_type="ollama",
            prompt_type="default"
        )
        
        # 测试查询
        query = "台积电的制造工艺有什么特点？"
        logger.info(f"\n问题: {query}")
        
        # 先获取检索结果
        docs = chain.retrieve_context(query)
        logger.info(f"\n检索到 {len(docs)} 个文档:")
        for i, (score, text, metadata) in enumerate(docs, 1):
            source = metadata.get("source", "未知")
            logger.info(f"  {i}. 相似度: {score:.3f}, 来源: {source}")
            logger.info(f"     内容: {text[:100]}...")
        
        # 生成答案
        answer = chain.invoke(query)
        logger.info(f"\n回答:\n{answer}\n")
        logger.info("✓ 重排序器测试通过")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 重排序器测试失败: {str(e)}", exc_info=True)
        return False


def test_streaming():
    """测试流式输出"""
    logger.info("=" * 60)
    logger.info("测试 3: 流式输出")
    logger.info("=" * 60)
    
    try:
        # 创建 RAG Chain
        chain = create_rag_chain(
            llm_type="ollama",
            prompt_type="semiconductor"
        )
        
        # 测试流式查询
        query = "解释一下 5nm 工艺和 7nm 工艺的区别"
        logger.info(f"\n问题: {query}")
        logger.info("\n流式回答:")
        
        # 收集完整答案以验证
        full_answer = ""
        for chunk in chain.stream(query):
            print(chunk, end="", flush=True)
            full_answer += chunk
        
        print("\n")
        logger.info("✓ 流式输出测试通过")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 流式输出测试失败: {str(e)}", exc_info=True)
        return False


def test_conversational():
    """测试多轮对话"""
    logger.info("=" * 60)
    logger.info("测试 4: 多轮对话")
    logger.info("=" * 60)
    
    try:
        # 创建对话式 RAG Chain
        chain = create_rag_chain(
            llm_type="ollama",
            prompt_type="conversational"
        )
        
        # 模拟对话历史
        chat_history = [
            ("user", "什么是半导体制造工艺？"),
            ("assistant", "半导体制造工艺是指生产集成电路和其他半导体器件的技术过程...")
        ]
        
        # 后续问题
        query = "那台积电在这方面有什么优势？"
        logger.info(f"\n对话历史:")
        for role, content in chat_history:
            logger.info(f"  {role}: {content[:50]}...")
        
        logger.info(f"\n当前问题: {query}")
        
        answer = chain.invoke(query, chat_history=chat_history)
        
        logger.info(f"\n回答:\n{answer}\n")
        logger.info("✓ 多轮对话测试通过")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 多轮对话测试失败: {str(e)}", exc_info=True)
        return False


def test_different_prompts():
    """测试不同的 prompt 类型"""
    logger.info("=" * 60)
    logger.info("测试 5: 不同 Prompt 类型")
    logger.info("=" * 60)
    
    try:
        prompt_types = ["default", "semiconductor", "datasheet"]
        query = "Intel 4 工艺的主要特点是什么？"
        
        for prompt_type in prompt_types:
            logger.info(f"\n--- 使用 {prompt_type} prompt ---")
            
            chain = create_rag_chain(
                llm_type="ollama",
                prompt_type=prompt_type
            )
            
            answer = chain.invoke(query)
            logger.info(f"回答: {answer[:200]}...\n")
        
        logger.info("✓ 不同 Prompt 类型测试通过")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 不同 Prompt 类型测试失败: {str(e)}", exc_info=True)
        return False


async def test_async_rag():
    """测试异步 RAG"""
    logger.info("=" * 60)
    logger.info("测试 6: 异步 RAG 查询")
    logger.info("=" * 60)
    
    try:
        # 创建 RAG Chain
        chain = create_rag_chain(llm_type="ollama")
        
        # 测试异步查询
        query = "什么是光刻技术？"
        logger.info(f"\n问题: {query}")
        
        answer = await chain.ainvoke(query)
        
        logger.info(f"\n回答:\n{answer}\n")
        logger.info("✓ 异步 RAG 查询测试通过")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 异步 RAG 查询测试失败: {str(e)}", exc_info=True)
        return False


def main():
    """运行所有测试"""
    logger.info("=" * 60)
    logger.info("RAG Chain 端到端测试")
    logger.info("=" * 60)
    
    # 检查配置
    settings = get_settings()
    logger.info(f"\n配置信息:")
    logger.info(f"  - Ollama Host: {settings.ollama_host}")
    logger.info(f"  - Ollama LLM Model: {settings.ollama_llm_model}")
    logger.info(f"  - Vector Dimension: {settings.vector_dimension}")
    logger.info(f"  - RAG Top-K: {settings.rag_top_k}")
    logger.info(f"  - Reranker Type: {settings.rag_reranker_type}")
    
    # 运行测试
    results = {
        "基础 RAG 查询": False,
        "重排序器功能": False,
        "流式输出": False,
        "多轮对话": False,
        "不同 Prompt 类型": False,
        "异步 RAG 查询": False
    }
    
    # 同步测试
    results["基础 RAG 查询"] = test_basic_rag()
    results["重排序器功能"] = test_reranker()
    results["流式输出"] = test_streaming()
    results["多轮对话"] = test_conversational()
    results["不同 Prompt 类型"] = test_different_prompts()
    
    # 异步测试
    results["异步 RAG 查询"] = asyncio.run(test_async_rag())
    
    # 打印测试报告
    logger.info("=" * 60)
    logger.info("测试报告")
    logger.info("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 60)
    logger.info(f"总计: {passed}/{total} 测试通过")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("🎉 所有测试通过！RAG Chain 运行正常。")
        return 0
    else:
        logger.warning(f"⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
