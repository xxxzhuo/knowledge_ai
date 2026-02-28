# Ollama Embedding 集成指南

本指南介绍如何在 Knowledge AI 项目中使用 Ollama 本地部署的 embedding 模型。

## 📋 目录

1. [概述](#概述)
2. [安装 Ollama](#安装-ollama)
3. [配置项目](#配置项目)
4. [测试集成](#测试集成)
5. [使用示例](#使用示例)
6. [性能对比](#性能对比)
7. [故障排除](#故障排除)

## 概述

### 为什么使用 Ollama？

- ✅ **本地部署**: 无需依赖外部 API，数据更安全
- ✅ **成本节省**: 无 API 调用费用
- ✅ **低延迟**: 本地推理，响应更快
- ✅ **离线使用**: 不需要互联网连接

### 支持的模型

- **embeddinggemma** (推荐): 768 维向量，L2 归一化
- 其他 Ollama embedding 模型

## 安装 Ollama

### 1. 安装 Ollama 服务

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**验证安装:**
```bash
ollama --version
```

### 2. 下载 embeddinggemma 模型

```bash
ollama pull embeddinggemma
```

### 3. 启动 Ollama 服务

```bash
ollama serve
```

默认服务地址: `http://localhost:11434`

### 4. 测试模型

```bash
# 测试模型是否可用
ollama list

# 应该看到 embeddinggemma 在列表中
```

## 配置项目

### 1. 安装 Python 依赖

```bash
cd knowledge_ai
pip3 install ollama>=0.1.0
```

或使用 requirements.txt:
```bash
pip3 install -r requirements.txt
```

### 2. 配置环境变量

创建或编辑 `.env` 文件:

```bash
# ============== Embedding Configuration ==============
# 选择 embedding 服务: openai 或 ollama
EMBEDDING_SERVICE=ollama

# Ollama 配置
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=embeddinggemma

# ============== Vector Store Configuration ==============
# embeddinggemma 使用 768 维向量
VECTOR_DIMENSION=768
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 3. 更新 Milvus 集合

如果已经存在使用 1536 维的集合，需要重新创建：

```bash
# 停止服务
./docker_manage.sh stop

# 清理旧数据
docker-compose -f docker/docker-compose.yml down -v

# 重新启动并初始化
./docker_manage.sh full-init
```

## 测试集成

### 1. 运行测试脚本

```bash
cd knowledge_ai
python3 scripts/test_ollama_embedding.py
```

**预期输出:**
```
==============================================================
Ollama Embedding 服务测试
==============================================================

==============================================================
测试 1: 直接使用 OllamaEmbeddingService
==============================================================

1. 测试单个文本向量化...
   ✓ 文本: The quick brown fox jumps over the lazy dog.
   ✓ 向量维度: 768
   ✓ 向量前5个值: [0.123, -0.456, 0.789, ...]

2. 测试批量文本向量化...
   ✓ 文本数量: 3
   ✓ 向量数量: 3
   ✓ 每个向量维度: 768

3. 测试获取服务维度...
   ✓ 服务维度: 768

4. 测试健康检查...
   ✓ 服务状态: 健康

==============================================================
✓ 所有测试通过！
==============================================================
```

### 2. 测试向量存储集成

```bash
python3 scripts/test_vector_store_integration.py
```

这将测试完整的向量存储流程。

## 使用示例

### 1. 基本使用

```python
from app.embeddings import get_embedding_service

# 获取 embedding 服务（自动根据配置选择）
service = get_embedding_service()

# 单个文本向量化
text = "半导体制造工艺中的光刻技术"
embedding = service.embed_text(text)
print(f"向量维度: {len(embedding)}")  # 768

# 批量文本向量化
texts = [
    "芯片设计流程",
    "晶圆制造技术",
    "封装测试工艺"
]
embeddings = service.embed_documents(texts)
print(f"向量数量: {len(embeddings)}")  # 3
```

### 2. 在 RAG 系统中使用

```python
from app.retriever import VectorRetriever

# 创建检索器（自动使用配置的 embedding 服务）
retriever = VectorRetriever()

# 检索相关文档
query = "什么是光刻技术？"
results = retriever.retrieve(query, k=5)

for similarity, text, metadata in results:
    print(f"相似度: {similarity:.3f}")
    print(f"内容: {text[:100]}...")
```

### 3. 文档处理

```python
from app.document_processor import DocumentProcessor

# 创建文档处理器
processor = DocumentProcessor()

# 处理文档（自动使用 Ollama embedding）
result = processor.process_document("path/to/document.pdf")
print(f"生成向量数: {len(result.chunks)}")
```

## 性能对比

### embeddinggemma vs OpenAI text-embedding-3-large

| 指标 | embeddinggemma | text-embedding-3-large |
|------|----------------|------------------------|
| 向量维度 | 768 | 1536 |
| 单文本延迟 | ~50ms | ~200ms (含网络) |
| 批量吞吐 | ~100 doc/s | ~50 doc/s |
| 成本 | 免费 | $0.00013/1K tokens |
| 部署 | 本地 | 云端 API |
| 归一化 | L2 归一化 | 未归一化 |

### 资源使用

**embeddinggemma (本地):**
- 内存: ~2GB
- CPU: 中等负载
- 磁盘: ~1.5GB (模型大小)

## 故障排除

### 1. Ollama 服务未启动

**错误信息:**
```
ConnectionError: Failed to connect to Ollama
```

**解决方案:**
```bash
# 启动 Ollama 服务
ollama serve

# 在另一个终端验证
curl http://localhost:11434/api/version
```

### 2. 模型未下载

**错误信息:**
```
Model 'embeddinggemma' not found
```

**解决方案:**
```bash
# 下载模型
ollama pull embeddinggemma

# 验证模型
ollama list
```

### 3. 向量维度不匹配

**错误信息:**
```
ValueError: Vector dimension mismatch: expected 1536, got 768
```

**解决方案:**

1. 更新配置文件 `.env`:
```bash
VECTOR_DIMENSION=768
```

2. 重新创建 Milvus 集合:
```bash
./docker_manage.sh clean
./docker_manage.sh full-init
```

### 4. 端口冲突

**错误信息:**
```
Address already in use: 11434
```

**解决方案:**
```bash
# 查找占用端口的进程
lsof -i :11434

# 杀死进程或使用不同端口
# 在 .env 中配置:
OLLAMA_HOST=http://localhost:11435
```

### 5. 内存不足

**错误信息:**
```
Out of memory error
```

**解决方案:**

1. 关闭其他程序释放内存
2. 使用更小的模型
3. 增加系统内存或使用 swap

## 切换回 OpenAI

如果需要切换回 OpenAI Embedding:

```bash
# 在 .env 中修改
EMBEDDING_SERVICE=openai
OPENAI_API_KEY=sk-your-key-here
EMBEDDING_MODEL=text-embedding-3-large
VECTOR_DIMENSION=1536

# 重新初始化向量库
./docker_manage.sh clean
./docker_manage.sh full-init
```

## 最佳实践

### 1. 批量处理

```python
# ✓ 推荐：批量处理
texts = [...]  # 100 个文本
embeddings = service.embed_documents(texts)  # 一次调用

# ✗ 不推荐：逐个处理
for text in texts:
    embedding = service.embed_text(text)  # 100 次调用
```

### 2. 错误处理

```python
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def safe_embed(text):
    try:
        return service.embed_text(text)
    except Exception as e:
        logger.error(f"Embedding 失败: {e}")
        raise
```

### 3. 缓存结果

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_embed(text: str):
    return tuple(service.embed_text(text))
```

## 参考资源

- [Ollama 官方文档](https://ollama.com/docs)
- [embeddinggemma 模型](https://ollama.com/library/embeddinggemma)
- [Ollama Python SDK](https://github.com/ollama/ollama-python)

## 支持

如遇问题，请：
1. 查看本指南的故障排除部分
2. 运行测试脚本诊断: `python3 scripts/test_ollama_embedding.py`
3. 检查 Ollama 服务日志
4. 提交 Issue（附带日志和错误信息）

---

**更新日期**: 2026-02-28
**版本**: v1.0
**状态**: ✅ 生产就绪
