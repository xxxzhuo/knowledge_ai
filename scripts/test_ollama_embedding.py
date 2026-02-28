#!/usr/bin/env python3
"""
测试 Ollama Embedding 服务
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.embeddings import OllamaEmbeddingService, get_embedding_service
from app.config import get_settings


def test_ollama_direct():
    """直接测试 Ollama Embedding 服务"""
    print("=" * 60)
    print("测试 1: 直接使用 OllamaEmbeddingService")
    print("=" * 60)
    
    try:
        service = OllamaEmbeddingService(
            model_name='embeddinggemma',
            host='http://localhost:11434'
        )
        
        # 测试单个文本
        print("\n1. 测试单个文本向量化...")
        text = "The quick brown fox jumps over the lazy dog."
        embedding = service.embed_text(text)
        print(f"   ✓ 文本: {text}")
        print(f"   ✓ 向量维度: {len(embedding)}")
        print(f"   ✓ 向量前5个值: {embedding[:5]}")
        
        # 测试批量文本
        print("\n2. 测试批量文本向量化...")
        texts = [
            'The quick brown fox jumps over the lazy dog.',
            'The five boxing wizards jump quickly.',
            'Jackdaws love my big sphinx of quartz.',
        ]
        embeddings = service.embed_documents(texts)
        print(f"   ✓ 文本数量: {len(texts)}")
        print(f"   ✓ 向量数量: {len(embeddings)}")
        print(f"   ✓ 每个向量维度: {len(embeddings[0])}")
        
        # 测试服务维度
        print("\n3. 测试获取服务维度...")
        dimension = service.get_dimension()
        print(f"   ✓ 服务维度: {dimension}")
        
        # 测试健康检查
        print("\n4. 测试健康检查...")
        is_healthy = service.health_check()
        print(f"   ✓ 服务状态: {'健康' if is_healthy else '不健康'}")
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_ollama_from_config():
    """从配置文件测试 Ollama Embedding 服务"""
    print("\n" + "=" * 60)
    print("测试 2: 使用配置获取 Embedding 服务")
    print("=" * 60)
    
    try:
        settings = get_settings()
        print(f"\n配置信息:")
        print(f"   - Embedding 服务: {settings.embedding_service}")
        print(f"   - Ollama 地址: {settings.ollama_host}")
        print(f"   - Ollama 模型: {settings.ollama_embedding_model}")
        print(f"   - 向量维度: {settings.vector_dimension}")
        
        # 使用工厂函数获取服务
        print("\n使用工厂函数获取服务...")
        service = get_embedding_service()
        print(f"   ✓ 服务类型: {type(service).__name__}")
        
        # 测试向量化
        print("\n测试向量化...")
        text = "半导体制造工艺中的光刻技术是关键环节。"
        embedding = service.embed_text(text)
        print(f"   ✓ 文本: {text}")
        print(f"   ✓ 向量维度: {len(embedding)}")
        
        print("\n" + "=" * 60)
        print("✓ 配置测试通过！")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 配置测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Ollama Embedding 服务测试")
    print("=" * 60)
    
    # 测试 1: 直接测试
    success_1 = test_ollama_direct()
    
    # 测试 2: 从配置测试
    success_2 = test_ollama_from_config()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"直接测试: {'✓ 通过' if success_1 else '✗ 失败'}")
    print(f"配置测试: {'✓ 通过' if success_2 else '✗ 失败'}")
    
    if success_1 and success_2:
        print("\n🎉 所有测试通过！Ollama Embedding 服务运行正常。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查 Ollama 服务是否正常运行。")
        print("\n提示:")
        print("  1. 确保 Ollama 服务正在运行: ollama serve")
        print("  2. 确保已下载 embeddinggemma 模型: ollama pull embeddinggemma")
        print("  3. 检查端口是否正确: http://localhost:11434")
        return 1


if __name__ == "__main__":
    sys.exit(main())
