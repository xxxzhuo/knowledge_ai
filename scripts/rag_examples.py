#!/usr/bin/env python
"""
RAG Chain 快速示例

展示如何使用 RAG Chain 进行半导体知识问答。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag import create_rag_chain


def example_1_basic_query():
    """示例1: 基础查询"""
    print("=" * 60)
    print("示例 1: 基础 RAG 查询")
    print("=" * 60)
    
    # 创建 RAG Chain
    chain = create_rag_chain(
        llm_type="ollama",
        reranker_type="simple",
        prompt_type="default"
    )
    
    # 查询
    question = "什么是半导体工艺技术？"
    print(f"\n问题: {question}\n")
    
    answer = chain.invoke(question)
    print(f"回答:\n{answer}\n")


def example_2_streaming():
    """示例2: 流式输出"""
    print("=" * 60)
    print("示例 2: 流式输出")
    print("=" * 60)
    
    chain = create_rag_chain(
        llm_type="ollama",
        prompt_type="semiconductor"
    )
    
    question = "解释一下台积电的制造工艺有什么特点"
    print(f"\n问题: {question}\n")
    print("回答:")
    
    # 流式输出
    for chunk in chain.stream(question):
        print(chunk, end="", flush=True)
    
    print("\n")


def example_3_datasheet_query():
    """示例3: 数据手册查询"""
    print("=" * 60)
    print("示例 3: 数据手册查询")
    print("=" * 60)
    
    chain = create_rag_chain(
        llm_type="ollama",
        prompt_type="datasheet"
    )
    
    question = "Intel 4 工艺有哪些技术参数？"
    print(f"\n问题: {question}\n")
    
    answer = chain.invoke(question)
    print(f"回答:\n{answer}\n")


def example_4_conversational():
    """示例4: 多轮对话"""
    print("=" * 60)
    print("示例 4: 多轮对话")
    print("=" * 60)
    
    chain = create_rag_chain(
        llm_type="ollama",
        prompt_type="conversational"
    )
    
    # 模拟对话历史
    chat_history = [
        ("user", "什么是半导体制造工艺？"),
        ("assistant", "半导体制造工艺是指生产集成电路的技术过程，包括设计、制造和测试等环节。")
    ]
    
    print("\n对话历史:")
    for role, content in chat_history:
        print(f"  {role}: {content}")
    
    # 后续问题
    question = "那台积电在这方面有什么优势？"
    print(f"\n当前问题: {question}\n")
    
    answer = chain.invoke(question, chat_history=chat_history)
    print(f"回答:\n{answer}\n")


def example_5_retrieve_only():
    """示例5: 仅检索文档"""
    print("=" * 60)
    print("示例 5: 仅检索相关文档")
    print("=" * 60)
    
    chain = create_rag_chain(
        llm_type="ollama",
        reranker_type="simple"
    )
    
    question = "5nm 工艺的特点"
    print(f"\n问题: {question}\n")
    print("检索到的相关文档:\n")
    
    # 仅检索，不生成答案
    docs = chain.retrieve_context(question)
    
    for i, (score, text, metadata) in enumerate(docs, 1):
        print(f"文档 {i}:")
        print(f"  相似度: {score:.3f}")
        print(f"  来源: {metadata.get('source', '未知')}")
        print(f"  内容: {text[:150]}...")
        print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("RAG Chain 使用示例")
    print("=" * 60 + "\n")
    
    try:
        # 运行各个示例
        example_1_basic_query()
        example_2_streaming()
        example_3_datasheet_query()
        example_4_conversational()
        example_5_retrieve_only()
        
        print("=" * 60)
        print("✓ 所有示例运行完成！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
