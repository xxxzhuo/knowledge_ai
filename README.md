# Semiconductor Knowledge AI  

分层、解耦、可扩展的RAG + LLM知识库系统，专为半导体行业设计。

## 🎯 项目特点

- **大厂级架构**: 分层设计 + 解耦 + 可扩展
- **LangChain 1.0**: 最新API标准 + LCEL
- **Hybrid Search**: BM25 + Vector混合检索
- **工业级指标**: 可观测性、缓存、监控
- **容器化部署**: Docker + Docker Compose

## 📦 技术栈

| 层级 | 技术 |
|------|------|
| API | FastAPI |
| LLM框架 | LangChain 1.0 |
| 向量库 | Milvus / FAISS |
| 数据库 | PostgreSQL |
| 存储 | S3 / MinIO |
| 监控 | Prometheus + Grafana |

## 🚀 快速开始

### 前提条件
- Python 3.11+
- Docker 20.10+
- PostgreSQL 15+ (可选，Docker提供)

### 1. 环境配置

```bash
# 克隆项目
cd knowledge_ai

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制环境配置
cp .env.example .env
```

### 2. 配置环境变量

编辑 `.env` 文件：

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/knowledge_ai

# LLM Config
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4

# Vector Store
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Storage
STORAGE_TYPE=local
```

### 3. 启动服务

**选项 A: 使用 Docker Compose (推荐)**

```bash
cd docker
docker-compose up -d

# 等待所有服务启动（约30秒）
docker-compose ps
```

**选项 B: 本地开发**

```bash
# 初始化数据库
python scripts/init_db.py

# 加载测试数据
python scripts/seed_data.py

# 启动应用
python main.py
```

### 4. 验证安装

```bash
# API Health Check
curl http://localhost:8000/api/v1/health

# 应该看到:
# {
#   "status": "healthy",
#   "database": "healthy",
#   "vector_store": "unknown",
#   "embeddings_service": "unknown",
#   "timestamp": "2026-02-27T..."
# }
```

## 📚 API 文档

启动后自动生成 Swagger 文档：

```
http://localhost:8000/docs
```

### 核心端点

#### 1. 文档管理

```bash
# 列出文档
GET /api/v1/documents?skip=0&limit=10

# 获取文档详情
GET /api/v1/documents/{doc_id}

# 上传新文档
POST /api/v1/documents
{
  "file_name": "example.pdf",
  "vendor": "Intel",
  "category": "CPU"
}

# 删除文档
DELETE /api/v1/documents/{doc_id}
```

#### 2. RAG查询

```bash
# 提问
POST /api/v1/query
{
  "question": "Intel i7的时钟频率是多少?",
  "top_k": 5,
  "use_rerank": true
}

# 批量查询
POST /api/v1/query/batch
[
  { "question": "..." },
  { "question": "..." }
]
```

#### 3. 健康检查

```bash
GET /api/v1/health
GET /api/v1/status
```

## 📁 项目结构

```
knowledge_ai/
├── app/                           # 应用主目录
│   ├── api/                       # FastAPI 路由
│   │   ├── health.py              # 健康检查
│   │   ├── documents.py           # 文档管理
│   │   └── rag.py                 # RAG查询
│   ├── agent/                     # LangChain Agent (待实现)
│   ├── rag/                       # RAG核心逻辑 (待实现)
│   ├── retriever/                 # 检索模块 (待实现)
│   ├── embeddings/                # Embedding服务 (待实现)
│   ├── loaders/                   # 文档加载器 (待实现)
│   ├── chunking/                  # 分块策略 (待实现)
│   ├── metadata/                  # 元数据管理 (待实现)
│   ├── storage/                   # 存储接口 (待实现)
│   ├── config.py                  # 配置管理
│   ├── database.py                # 数据库连接
│   ├── models.py                  # SQLAlchemy ORM
│   ├── schemas.py                 # Pydantic schemas
│   └── main.py                    # FastAPI应用
│
├── scripts/                       # 辅助脚本
│   ├── init_db.py                 # 初始化数据库
│   └── seed_data.py               # 加载测试数据
│
├── docker/                        # Docker配置
│   ├── Dockerfile                 # 应用容器
│   ├── docker-compose.yml         # 多服务编排
│   └── prometheus.yml             # 监控配置
│
├── tests/                         # 单元测试
├── main.py                        # 应用入口
├── requirements.txt               # 依赖列表
├── .env.example                   # 环境变量示例
└── README.md                      # 本文件
```

## 🔧 开发指南

### 添加新的API端点

在 `app/api/` 中创建新的路由文件：

```python
# app/api/new_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/new-feature")
def new_feature():
    return {"message": "New feature"}
```

在 `app/main.py` 中注册：

```python
from app.api import new_feature
app.include_router(new_feature.router, prefix="/api/v1", tags=["NewFeature"])
```

### 数据库迁移

```bash
# 创建表
python scripts/init_db.py

# 重置数据库（谨慎使用）
python scripts/init_db.py drop
```

### 运行测试

```bash
pytest tests/ -v
```

## 📊 监控和日志

### Prometheus 指标

访问 metrics 端点：
```
http://localhost:9090
```

### 应用日志

```bash
# 查看 API 服务日志
docker logs knowledge_ai_api -f

# 本地运行时
# 日志输出到控制台
```

## 🔄 工作流程概览

### 第1阶段 ✅ (当前)
- [x] 项目结构
- [x] FastAPI应用框架
- [x] PostgreSQL集成
- [x] Docker容器化

### 第2阶段 (下一步)
- [ ] 文档加载器 (PDF, OCR)
- [ ] 智能分块器
- [ ] Embedding服务
- [ ] 向量存储集成

### 第3阶段
- [ ] Hybrid Retriever
- [ ] Reranker精排
- [ ] RAG Chain
- [ ] 缓存优化

### 第4阶段
- [ ] Agent定义
- [ ] Tool集成
- [ ] 质量评估
- [ ] 性能优化

### 第5阶段
- [ ] Kubernetes部署
- [ ] 监控告警
- [ ] 文档完善
- [ ] 生产就绪

## 🐛 故障排查

### 数据库连接失败

```bash
# 检查PostgreSQL状态
docker ps

# 查看日志
docker logs knowledge_ai_postgres

# 手动连接测试
psql -h localhost -U postgres -d knowledge_ai
```

### API无法启动

```bash
# 检查端口占用
lsof -i :8000

# 查看错误日志
python main.py
```

### Milvus连接问题

```bash
# 检查Milvus状态
curl http://localhost:9091/healthz

# 重启Milvus
docker restart knowledge_ai_milvus
```

## 📝 环境变量详解

| 变量 | 说明 | 示例 |
|------|------|------|
| DATABASE_URL | PostgreSQL连接 | postgresql://user:pass@localhost/db |
| OPENAI_API_KEY | OpenAI API密钥 | sk-xxx |
| OPENAI_MODEL | 使用的模型 | gpt-4 |
| VECTOR_STORE_TYPE | 向量库类型 | milvus/faiss/pgvector |
| STORAGE_TYPE | 存储类型 | local/s3/minio |
| LOG_LEVEL | 日志级别 | INFO/DEBUG/WARNING |

## 📞 支持和反馈

遇到问题或有建议？

- 查看 [故障排查](#-故障排查) 章节
- 提交 Issue
- 联系开发团队

## 📄 许可证

MIT License

---

**版本**: 0.1.0  
**最后更新**: 2026年2月27日
