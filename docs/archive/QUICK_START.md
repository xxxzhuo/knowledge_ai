# Milvus 向量库集成指南

## 快速启动 (5 分钟)

### 1. 启动所有服务

```bash
cd knowledge_ai
chmod +x docker_manage.sh
./docker_manage.sh full-init
```

这将自动执行：
- ✓ 启动 Milvus、PostgreSQL、MinIO 容器
- ✓ 初始化 Milvus 向量库
- ✓ 创建数据库表
- ✓ 运行功能测试

### 2. 查看测试结果

```bash
# 测试成功后，您将看到：
✓ 向量库连接: 通过
✓ Embedding 服务: 通过
✓ 向量添加和存储: 通过
✓ 向量搜索和检索: 通过
✓ 检索器集成: 通过
✓ 向量库统计信息: 通过
```

### 3. 验证服务地址

```bash
./docker_manage.sh status

# 输出示例：
✓ PostgreSQL: 运行中 (localhost:5432)
✓ Milvus: 运行中 (localhost:19530)
✓ MinIO: 运行中 (http://localhost:9000)
✓ API: 运行中 (http://localhost:8000)
```

## 完整步骤说明

### 步骤 1: 环境准备

**前置要求：**
- Docker 和 Docker Compose
- Python 3.10+
- 8GB+ RAM

**依赖安装：**
```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 关键依赖：
# - pymilvus==2.3.4      (Milvus Python 客户端)
# - openai==1.3.5        (OpenAI API)
# - fastapi==0.104.1     (Web 框架)
```

### 步骤 2: Docker 服务启动

```bash
# 方式 A: 使用管理脚本（推荐）
./docker_manage.sh start

# 方式 B: 使用 docker-compose
cd docker
docker-compose up -d

# 方式 C: 完整初始化
./docker_manage.sh full-init
```

**启动的服务：**
| 服务 | 地址 | 用途 |
|------|------|------|
| PostgreSQL | localhost:5432 | 元数据和缓存 |
| Milvus | localhost:19530 | 向量库 |
| MinIO | localhost:9000 | 对象存储 |
| API | localhost:8000 | FastAPI 应用 |
| Prometheus | localhost:9090 | 监控 |

### 步骤 3: Milvus 初始化

```bash
# 自动初始化（推荐）
#./docker_manage.sh init-milvus

# 或直接运行脚本
python3 scripts/init_milvus.py

# 或验证配置
python3 scripts/init_milvus.py --verify-only
```

**初始化创建：**
- ✓ 集合名: `knowledge_ai`
- ✓ 字段: id, embedding, text, metadata
- ✓ 索引: IVF_FLAT (向量搜索)
- ✓ 向量维度: 768

### 步骤 4: 功能测试

```bash
# 向量库测试
./docker_manage.sh test

# 或运行脚本
python3 scripts/test_vector_store_integration.py

# RAG 系统测试
python3 scripts/test_rag_end_to_end.py
```

**测试覆盖：**
- ✓ 连接和健康检查
- ✓ 文档向量化
- ✓ 向量存储和检索
- ✓ RAG 端到端流程
- ✓ 系统统计信息

## 使用示例

### 示例 1: 基本向量存储和检索

```python
from knowledge_ai.app.storage import MilvusStore
from knowledge_ai.app.embeddings import OpenAIEmbeddingService

# 初始化
embedding_service = OpenAIEmbeddingService()
vector_store = MilvusStore()

# 添加文档
texts = [
    "Milvus 是一个开源向量数据库",
    "向量检索用于相似度搜索",
    "RAG 系统结合检索和生成"
]

embeddings = embedding_service.embed_documents(texts)
metadatas = [
    {"source": "doc1.pdf"},
    {"source": "doc2.pdf"},
    {"source": "doc3.pdf"}
]

ids = vector_store.add_embeddings(embeddings, texts, metadatas)
print(f"已添加 {len(ids)} 个文档")

# 搜索
query = "什么是向量数据库"
query_embedding = embedding_service.embed_text(query)
results = vector_store.search(query_embedding, k=3)

for distance, text, metadata in results:
    similarity = 1.0 / (1.0 + distance)
    print(f"相似度: {similarity:.3f}, 来源: {metadata['source']}")
```

### 示例 2: 使用检索器

```python
from knowledge_ai.app.retriever import VectorRetriever

# 创建检索器
retriever = VectorRetriever()

# 执行检索
query = "向量检索如何工作"
results = retriever.retrieve(query, k=3)

for similarity, text, metadata in results:
    print(f"{metadata['source']}: {similarity:.3f}")
    print(f"内容: {text[:100]}...")
```

### 示例 3: RAG 查询

```python
from knowledge_ai.app.api.rag import query as rag_query
from knowledge_ai.app.schemas import RAGQuery

# 创建查询
rag_query_obj = RAGQuery(question="什么是 RAG 系统？")

# 执行查询（在 API 路由中）
# response = await rag_query(rag_query_obj, ...)

# 获取结果
# - question: 原始问题
# - answer: 生成的答案
# - retrieved_chunks: 检索到的相关文档
# - confidence_score: 信心得分
```

## 文件结构

```
knowledge_ai/
├── docker/
│   ├── docker-compose.yml      # Docker 服务配置
│   ├── milvus_config.yaml      # Milvus 配置文件
│   └── prometheus.yml          # Prometheus 配置
│
├── scripts/
│   ├── init_milvus.py          # Milvus 初始化脚本
│   ├── init_db.py              # 数据库初始化脚本
│   ├── test_vector_store_integration.py  # 向量库测试
│   └── test_rag_end_to_end.py  # RAG 系统测试
│
├── app/
│   ├── storage/
│   │   ├── vector_store.py     # 向量库基类
│   │   └── milvus_store.py     # Milvus 实现
│   │
│   ├── retriever/
│   │   ├── base.py             # 检索器基类
│   │   └── vector_retriever.py # 向量检索器
│   │
│   ├── embeddings/
│   │   ├── base.py             # 向量化基类
│   │   └── openai_embedding.py # OpenAI Embedding 实现
│   │
│   └── api/
│       ├── rag.py              # RAG 查询端点
│       └── health.py           # 健康检查端点
│
├── docker_manage.sh            # Docker 管理脚本
├── MILVUS_DEPLOYMENT_GUIDE.md  # 部署指南
├── VECTOR_STORE_IMPROVEMENTS.md # 改进说明
└── requirements.txt            # Python 依赖
```

## 关键 API 端点

### 健康检查

```bash
# 整体健康检查
GET http://localhost:8000/health

# 向量库健康检查
GET http://localhost:8000/health/vector-store
```

### RAG 查询

```bash
# 单个查询
POST http://localhost:8000/api/v1/query
{
  "question": "什么是半导体？",
  "k": 5
}

# 批量查询
POST http://localhost:8000/api/v1/query/batch
[
  {"question": "问题 1"},
  {"question": "问题 2"}
]
```

## 常见命令

```bash
# Docker 管理命令
./docker_manage.sh start         # 启动所有服务
./docker_manage.sh stop          # 停止所有服务
./docker_manage.sh restart       # 重启所有服务
./docker_manage.sh logs          # 查看日志
./docker_manage.sh status        # 检查状态
./docker_manage.sh init-milvus   # 初始化 Milvus
./docker_manage.sh test          # 运行测试
./docker_manage.sh full-init     # 完整初始化
./docker_manage.sh clean         # 清理数据
./docker_manage.sh shell         # 连接容器

# Python 脚本
python scripts/init_milvus.py              # 初始化 Milvus
python scripts/test_vector_store_integration.py  # 测试向量库
python scripts/test_rag_end_to_end.py      # 测试 RAG
```

## 性能指标

| 操作 | 耗时 | 备注 |
|------|------|------|
| 文档向量化 (1000 docs) | ~30s | OpenAI API |
| 向量存储 (1000 vectors) | ~2s | 批量操作 |
| 向量搜索 (k=5) | <50ms | IVF_FLAT 索引 |
| RAG 查询 (完整流程) | ~5-10s | 包括 API 调用 |

## 故障排除

### 问题 1: Milvus 连接超时

```bash
# 检查 Milvus 服务
curl http://localhost:9091/healthz

# 查看日志
./docker_manage.sh logs milvus

# 重启服务
./docker_manage.sh restart
```

### 问题 2: 向量维度不匹配

```python
# 确保使用正确的模型
from knowledge_ai.app.config import get_settings

settings = get_settings()
print(f"配置的向量维度: {settings.vector_dimension}")
print(f"模型: {settings.embedding_model}")
```

### 问题 3: 搜索返回空结果

```python
# 检查向量库中的数据
vector_store = MilvusStore()
print(f"向量总数: {vector_store.count()}")

# 运行测试添加数据
./docker_manage.sh test

# 尝试搜索
retriever = VectorRetriever()
results = retriever.retrieve("test query", k=5)
print(f"搜索结果: {len(results)}")
```

## 下一步

1. **上传文档**
   ```bash
   curl -X POST http://localhost:8000/api/v1/process \
     -F "file=@document.pdf" \
     -F "enable_embedding=true"
   ```

2. **执行 RAG 查询**
   ```bash
   curl -X POST http://localhost:8000/api/v1/query \
     -H "Content-Type: application/json" \
     -d '{"question": "什么是 RAG？"}'
   ```

3. **监控系统**
   访问 http://localhost:9090 查看 Prometheus 指标

4. **查看日志**
   ```bash
   ./docker_manage.sh logs api
   ./docker_manage.sh logs milvus
   ```

## 支持和文档

- [Milvus 官方文档](https://milvus.io/docs)
- [完整部署指南](MILVUS_DEPLOYMENT_GUIDE.md)
- [向量库改进说明](VECTOR_STORE_IMPROVEMENTS.md)
- [API 文档](http://localhost:8000/docs)

## 总结

| 项目 | 状态 | 说明 |
|------|------|------|
| Milvus 向量库 | ✓ 部署完成 | 高性能向量检索 |
| 向量存储 | ✓ 实现完整 | 支持批量操作 |
| 向量检索 | ✓ 测试通过 | 支持相似度搜索 |
| RAG 系统 | ✓ 集成完成 | 端到端流程测试通过 |
| 监控告警 | ✓ Prometheus | 可观测性完善 |

现在您已经拥有一个完整的向量检索系统，可以开始构建智能应用了！🎉
