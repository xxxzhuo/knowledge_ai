# Semiconductor Knowledge AI

半导体行业 RAG + Agent 知识库系统，支持存储芯片料号智能解析、文档检索问答和可视化分析。

## 项目特点

- **存储芯片料号解析 Agent**: 支持镁光/SpecTek/三星/海力士/长江存储/英特尔/闪迪，覆盖 NAND 颗粒、DDR 颗粒、NAND 晶圆、服务器内存模组
- **完整 RAG Chain**: Retriever + LCEL + Reranker (Simple / CrossEncoder / Hybrid)
- **前端可视化**: 单页应用，料号解析/对比/BOM 生成/智能问答四大功能
- **本地化部署**: Ollama (qwen2.5:7b) + embeddinggemma，零 API 成本
- **LangChain 1.0**: LCEL 声明式链路 + 流式输出
- **容器化**: Docker Compose 一键编排

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | HTML / CSS / JS | 单页应用，无外部依赖 |
| API | FastAPI | 异步高性能 |
| Agent | 自研 PartNumberParser + StorageChipAgent | 料号解析 / 工具编排 |
| LLM | Ollama (qwen2.5:7b) / OpenAI | 可切换 |
| Embedding | embeddinggemma / text-embedding-3-large | 768 维向量 |
| RAG | LangChain 1.0 + LCEL | 检索增强生成 |
| 向量库 | Milvus 2.3 | 高性能向量检索 |
| 数据库 | PostgreSQL | 元数据存储 |
| 部署 | Docker Compose | Milvus + PostgreSQL + App |

## 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 15+ (可选，Docker 提供)
- Docker 20.10+ (可选)

### 安装 & 启动

```bash
# 克隆
git clone git@github.com:xxxzhuo/knowledge_ai.git
cd knowledge_ai

# 虚拟环境
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env 设置数据库、Ollama 等参数

# 启动
cd knowledge_ai
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

浏览器访问 **http://localhost:8000** 即可打开前端页面。

API 文档: **http://localhost:8000/docs**

### Docker 方式

```bash
cd docker
docker-compose up -d
```

## 前端功能

访问 `http://localhost:8000` 打开可视化界面，包含四个标签页:

| 标签 | 功能 | 说明 |
|------|------|------|
| 料号解析 | 输入料号 + 数量 | 卡片式展示品牌/晶圆型号/容量/制程/位宽/球位/良率等，自动计算总容量和有效产出 |
| 料号对比 | 多料号横向对比 | 表格展示所有参数差异 |
| BOM 清单 | 料号 × 数量列表 | 生成 BOM 汇总表，统计总容量/有效产出 |
| 智能问答 | 自然语言交互 | Agent 自动路由到解析/对比/BOM/搜索工具 |

## API 端点

### Agent (料号解析)

```bash
# 解析料号 (JSON)
POST /api/v1/agent/parse_json
{"part_number": "FBMB47R128G8ABAEAWG5-AS"}

# 参数计算 (JSON)
POST /api/v1/agent/calculate_json
{"part_number": "FBMB47R128G8ABAEAWG5-AS", "quantity": 100}

# 多料号对比 (JSON)
POST /api/v1/agent/compare_json
{"part_numbers": ["FBMB47R128G8ABAEAWG5-AS", "SUM123Z32512M8-TP"]}

# BOM 生成 (JSON)
POST /api/v1/agent/bom_json
{"items": [{"part_number": "FBMB47R128G8ABAEAWG5-AS", "quantity": 100}]}

# Agent 智能问答
POST /api/v1/agent/chat
{"query": "解析 FBMB47R128G8ABAEAWG5-AS"}
```

### RAG 检索

```bash
POST /api/v1/query         # 单条问答
POST /api/v1/query/batch   # 批量查询
```

### 文档管理

```bash
GET    /api/v1/documents          # 文档列表
GET    /api/v1/documents/{id}     # 文档详情
POST   /api/v1/documents          # 上传文档
DELETE /api/v1/documents/{id}     # 删除文档
```

### 健康检查

```bash
GET /api/v1/health
GET /api/v1/status
```

## 项目结构

```
knowledge_ai/
├── app/
│   ├── api/                       # FastAPI 路由
│   │   ├── agent.py               # Agent 料号解析 API
│   │   ├── documents.py           # 文档管理
│   │   ├── health.py              # 健康检查
│   │   ├── processing.py          # 文档处理
│   │   └── rag.py                 # RAG 查询
│   ├── agent/                     # 料号解析 Agent
│   │   ├── agent.py               # StorageChipAgent 工具编排
│   │   ├── part_number_parser.py  # 料号解析器 (8 大规则)
│   │   └── tools.py               # Agent 工具函数
│   ├── rag/                       # RAG 核心
│   │   ├── chain.py               # LCEL 链路
│   │   ├── prompts.py             # Prompt 模板
│   │   └── reranker.py            # 重排序 (Simple/CE/Hybrid)
│   ├── retriever/                 # 检索模块
│   │   ├── base.py                # 检索器基类
│   │   └── vector_retriever.py    # 向量检索
│   ├── embeddings/                # Embedding 服务
│   │   ├── ollama_embedding.py    # Ollama 本地向量化
│   │   └── openai_embedding.py    # OpenAI 向量化
│   ├── loaders/                   # 文档加载器
│   │   ├── pdf_loader.py          # PDF 解析
│   │   ├── image_loader.py        # 图片 OCR
│   │   └── table_extractor.py     # 表格提取
│   ├── chunking/                  # 分块策略
│   │   ├── semiconductor_splitter.py  # 半导体领域分块
│   │   └── table_aware_chunker.py     # 表格感知分块
│   ├── storage/                   # 向量存储
│   │   ├── milvus_store.py        # Milvus 存储
│   │   └── vector_store.py        # 通用接口
│   ├── static/                    # 前端页面
│   │   └── index.html             # 单页应用
│   ├── config.py                  # 配置管理
│   ├── database.py                # PostgreSQL 连接
│   ├── models.py                  # SQLAlchemy ORM
│   ├── schemas.py                 # Pydantic Schemas
│   └── main.py                    # FastAPI 应用工厂
├── docker/
│   ├── docker-compose.yml         # 服务编排
│   ├── Dockerfile                 # 应用容器
│   └── prometheus.yml             # 监控配置
├── scripts/                       # 辅助脚本
├── tests/                         # 测试
├── main.py                        # 入口
├── requirements.txt               # 依赖
└── .env.example                   # 环境变量模板
```

## 料号解析规则

解析器支持 8 大规则，覆盖存储芯片料号的完整参数提取:

| 规则 | 说明 | 示例 |
|------|------|------|
| 品牌识别 | 前缀 → 品牌 + 产品类型 | FBM → 镁光 NAND 颗粒 |
| 晶圆型号 | NAND: 第 4-8 位; DDR: 第 7-14 位 | B47R, Z32x |
| 晶圆容量 | 型号第 3 位数字映射 | 7 → 64GB |
| 颗粒容量 | NAND: left/8; DDR: left×right/8 | 128G8 → 16G |
| 位宽 | NAND: H/K/L; DDR: 4/8/16/32/64 | K → X8 |
| 制程 | 型号首字母 M/L/B/N | B → TLC |
| 球位 | NAND: '-' 左 2 位; DDR: 代数×位宽 | G5 → 272 |
| 良率 | 晶圆: E+数字; 颗粒: 后缀字母 | E9 → 90%, AS → 96% |

支持品牌: 镁光 (FBM/SUM/MT29)、SpecTek (FBN/FBC/SUN/SUU/XCB/PRM/PRN/W)、三星 (K9/M321/M393)、海力士 (H25)、长江存储 (YMN)、英特尔 (X29)、闪迪 (SD)

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DATABASE_URL | PostgreSQL 连接 | postgresql://postgres:password@localhost:5432/knowledge_ai |
| OLLAMA_HOST | Ollama 服务地址 | http://localhost:11434 |
| OLLAMA_LLM_MODEL | LLM 模型 | qwen2.5:7b |
| OLLAMA_EMBEDDING_MODEL | Embedding 模型 | embeddinggemma |
| EMBEDDING_SERVICE | Embedding 服务类型 | ollama |
| RAG_LLM_TYPE | RAG LLM 类型 | ollama |
| RAG_RERANKER_TYPE | 重排序策略 | simple |
| MILVUS_HOST | Milvus 地址 | localhost |
| OPENAI_API_KEY | OpenAI 密钥 (可选) | - |

## 故障排查

```bash
# 端口占用
lsof -i :8000

# 数据库连接 (数据库不可用时 Agent 功能仍正常)
psql -h localhost -U postgres -d knowledge_ai

# Milvus 状态
curl http://localhost:9091/healthz

# 查看日志
docker logs knowledge_ai_api -f
```

## 许可证

MIT License

---

**版本**: 0.2.0  
**最后更新**: 2026-03-02
