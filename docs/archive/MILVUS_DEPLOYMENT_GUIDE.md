# Milvus 向量库部署和使用指南

## 概述

本指南详细说明如何部署、配置和使用 Milvus 向量库，以支持 Knowledge AI 的向量检索功能。

## 目录

1. [快速开始](#快速开始)
2. [Docker 部署](#docker-部署)
3. [服务配置](#服务配置)
4. [初始化和测试](#初始化和测试)
5. [常见问题](#常见问题)
6. [性能优化](#性能优化)
7. [故障排除](#故障排除)

## 快速开始

### 前置要求

- Docker 和 Docker Compose
- Python 3.10+
- 至少 8GB RAM 和 20GB 磁盘空间

### 一键启动和初始化

```bash
cd knowledge_ai

# 使用管理脚本进行完整初始化
chmod +x docker_manage.sh
./docker_manage.sh full-init
```

这将执行以下步骤：
1. ✓ 启动所有 Docker 服务
2. ✓ 初始化 PostgreSQL 数据库
3. ✓ 初始化 Milvus 向量库
4. ✓ 运行功能测试

### 验证部署

```bash
# 检查服务状态
./docker_manage.sh status

# 查看服务日志
./docker_manage.sh logs

# 测试向量存储功能
./docker_manage.sh test
```

## Docker 部署

### 服务架构

```
┌─────────────────────────────────────────────┐
│         Knowledge AI FastAPI App            │
│  - 文档处理                                  │
│  - 向量化处理                                │
│  - RAG 查询                                  │
└────────┬────────────────────────────────────┘
         │
    ┌────┴─────────────────────────────┐
    │                                   │
    ▼                                   ▼
┌─────────────┐                   ┌──────────────┐
│ PostgreSQL  │                   │ Milvus       │
│ (关系数据库) │                   │ (向量库)      │
│ - 元数据     │                   │ - 向量索引     │
│ - 缓存      │                   │ - 相似度搜索   │
└─────────────┘                   └──────────────┘
```

### docker-compose.yml 关键配置

#### Milvus 服务

```yaml
milvus:
  image: milvusdb/milvus:v2.3.11
  container_name: knowledge_ai_milvus
  environment:
    COMMON_STORAGETYPE: local
  ports:
    - "19530:19530"  # gRPC 端口
    - "9091:9091"    # 健康检查端口
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
    interval: 10s
    timeout: 10s
    retries: 10
```

**重要配置参数：**

| 参数 | 说明 | 默认值 |
|------|------|-------|
| `COMMON_STORAGETYPE` | 存储类型 (local/remote) | local |
| `ETCD_ENDPOINTS` | etcd 服务地址 | localhost:2379 |
| `COMMON_LOGPATH` | 日志路径 | /var/log/milvus |

#### MinIO (对象存储)

Milvus 使用 MinIO 作为默认对象存储：

```yaml
minio:
  image: minio/minio:latest
  environment:
    MINIO_ACCESS_KEY: minioadmin
    MINIO_SECRET_KEY: minioadmin
  ports:
    - "9000:9000"  # API 端口
    - "9001:9001"  # 控制台端口
```

**默认凭证：**
- 用户名：`minioadmin`
- 密码：`minioadmin`
- 控制台：http://localhost:9001

## 服务配置

### Milvus 配置文件

配置文件位置：`docker/milvus_config.yaml`

**关键配置项：**

```yaml
common:
  loglevel: info
  logpath: /var/log/milvus

etcd:
  endpoints:
    - localhost:2379
  dial_timeout: 30000000000

storage:
  type: local
  path: /var/lib/milvus
  minio:
    address: minio:9000
    bucket_name: milvus-bucket
```

### Python 配置

在 `app/config.py` 中配置连接参数：

```python
class Settings(BaseSettings):
    # Milvus 配置
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    vector_dimension: int = 1536  # text-embedding-3-large
    vector_store_type: str = "milvus"
```

**环境变量：**

```bash
export MILVUS_HOST=localhost
export MILVUS_PORT=19530
export VECTOR_DIMENSION=1536
```

## 初始化和测试

### 1. Milvus 初始化

初始化脚本位置：`scripts/init_milvus.py`

**功能：**
- ✓ 等待 Milvus 服务启动
- ✓ 创建 `knowledge_ai` 集合
- ✓ 定义集合字段结构
- ✓ 创建向量索引（IVF_FLAT）
- ✓ 验证配置

**运行方式：**

```bash
# 使用管理脚本
./docker_manage.sh init-milvus

# 或直接运行 Python 脚本
python scripts/init_milvus.py

# 使用自定义配置
python scripts/init_milvus.py \
  --host localhost \
  --port 19530 \
  --collection knowledge_ai \
  --dimension 1536

# 仅验证配置
python scripts/init_milvus.py --verify-only
```

### 2. 向量库结构

初始化创建的集合结构：

```
集合名: knowledge_ai
├── 字段:
│   ├── id (VARCHAR, 主键)
│   │   └── 唯一文档标识符
│   ├── embedding (FLOAT_VECTOR, dim=1536)
│   │   └── 文本的向量表示
│   ├── text (VARCHAR, max_length=65535)
│   │   └── 原始文本内容
│   └── metadata (JSON)
│       └── 文档元数据（来源、页面、标签等）
│
└── 索引:
    └── IVF_FLAT (嵌入字段)
        ├── 度量类型: L2
        ├── 聚类数: 128
        └── 搜索参数: nprobe=10
```

### 3. 功能测试

集成测试脚本位置：`scripts/test_vector_store_integration.py`

**测试内容：**

```bash
测试 1: 向量库连接 ✓
├── 检查连接状态
├── 验证健康检查
└── 显示集合元数据

测试 2: Embedding 服务 ✓
├── 单个文本向量化
└── 批量文本向量化

测试 3: 向量添加和存储 ✓
├── 生成示例向量
├── 添加到向量库
└── 验证数据持久化

测试 4: 向量搜索和检索 ✓
├── 执行相似度搜索
├── 验证搜索结果
└── 计算相似度得分

测试 5: 检索器集成 ✓
├── 初始化检索器
├── 执行端到端检索
└── 验证结果排序

测试 6: 向量库统计 ✓
├── 获取向量数量
├── 检查健康状态
└── 显示存储类型
```

**运行测试：**

```bash
# 使用管理脚本
./docker_manage.sh test

# 或直接运行 Python 脚本
python scripts/test_vector_store_integration.py

# 测试输出示例
✓ 向量库连接: 通过
✓ Embedding 服务: 通过
✓ 向量添加和存储: 通过
✓ 向量搜索和检索: 通过
✓ 检索器集成: 通过
✓ 向量库统计: 通过

总测试数: 6
通过: 6
失败: 0
```

### 4. 测试结果保存

测试结果自动保存到：`vector_store_test_results.json`

```json
{
  "timestamp": "2024-02-28 10:30:45",
  "tests": [
    {
      "name": "向量库连接",
      "status": "通过",
      "error": null
    }
  ],
  "summary": {
    "total": 6,
    "passed": 6,
    "failed": 0
  }
}
```

## Docker 管理脚本使用

完整的 `docker_manage.sh` 脚本提供以下命令：

### 基本操作

```bash
# 启动所有服务
./docker_manage.sh start

# 停止所有服务
./docker_manage.sh stop

# 重启所有服务
./docker_manage.sh restart

# 查看服务日志
./docker_manage.sh logs [service]
./docker_manage.sh logs api         # 查看 API 日志
./docker_manage.sh logs milvus      # 查看 Milvus 日志
```

### 服务管理

```bash
# 检查服务状态
./docker_manage.sh status

# 连接到 API 容器
./docker_manage.sh shell

# 清理所有数据
./docker_manage.sh clean
```

### 初始化

```bash
# 初始化 Milvus
./docker_manage.sh init-milvus

# 测试向量功能
./docker_manage.sh test

# 完整初始化
./docker_manage.sh full-init
```

## 依赖管理

### requirements.txt 中的关键依赖

```txt
# 向量库
pymilvus==2.3.4

# Embedding
openai==1.3.5
tenacity==8.2.3

# 数据库
sqlalchemy==2.0.23
psycopg2-binary==2.9.9

# Web 框架
fastapi==0.104.1
uvicorn==0.24.0
```

### 依赖安装

```bash
# 安装所有依赖
pip install -r requirements.txt

# 仅安装向量库相关
pip install pymilvus openai
```

## 常见问题

### Q1: Milvus 连接失败

**错误信息：**
```
Error: Failed to connect to Milvus
```

**解决方案：**
1. 检查 Milvus 容器是否运行
   ```bash
   ./docker_manage.sh status
   ```

2. 检查端口是否开放
   ```bash
   curl http://localhost:9091/healthz
   ```

3. 查看 Milvus 日志
   ```bash
   ./docker_manage.sh logs milvus
   ```

### Q2: 向量维度不匹配

**错误信息：**
```
ValueError: Embedding dimension 1536 does not match configured dimension
```

**解决方案：**
- 确保 OpenAI 模型使用 `text-embedding-3-large`（维度 1536）
- 或更新配置文件中的 `vector_dimension`
- 根据使用的模型调整维度值

### Q3: 搜索结果为空

**可能原因：**
- 向量库中没有数据
- 文档尚未向量化
- 相似度阈值设置过高

**解决方案：**
1. 检查向量库中的数据量
   ```python
   vector_store = MilvusStore()
   print(f"向量数量: {vector_store.count()}")
   ```

2. 运行测试脚本添加样本数据
   ```bash
   ./docker_manage.sh test
   ```

3. 降低相似度阈值进行搜索

### Q4: 内存不足

**解决方案：**
- 增加 Docker 内存限制
- 更新 `docker-compose.yml`
  ```yaml
  milvus:
    deploy:
      resources:
        limits:
          memory: 8G
  ```

## 性能优化

### 1. 索引优化

**IVF_FLAT vs IVF_SQ8**

```python
# IVF_FLAT (更精确)
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 128}
}

# IVF_SQ8 (更快，占用空间少)
index_params = {
    "index_type": "IVF_SQ8",
    "metric_type": "L2",
    "params": {"nlist": 128}
}
```

### 2. 搜索参数调优

```python
# 搜索参数
search_params = {
    "metric_type": "L2",
    "params": {"nprobe": 10}  # 增加 nprobe 提高精度，降低速度
}
```

**nprobe 建议值：**
- 快速搜索：3-5
- 平衡：10
- 精确搜索：20-30

### 3. 批量操作优化

```python
# 批量添加向量
batch_size = 1000
for i in range(0, len(embeddings), batch_size):
    batch = embeddings[i:i+batch_size]
    ids = vector_store.add_embeddings(batch, texts, metadatas)
    vector_store.flush()
```

### 4. 资源配置

**docker-compose.yml 中的资源限制：**

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
    reservations:
      cpus: '2'
      memory: 4G
```

## 故障排除

### 日志位置

- Milvus 日志：`docker volume inspect knowledge_ai_milvus_data`
- API 日志：`./docker_manage.sh logs api`
- PostgreSQL 日志：`./docker_manage.sh logs postgres`

### 健康检查

```bash
# 检查所有服务
./docker_manage.sh status

# 手动检查各服务
curl -s http://localhost:9091/healthz     # Milvus
curl -s http://localhost:9000/minio/health/live  # MinIO
curl -s http://localhost:5432             # PostgreSQL
curl -s http://localhost:8000/health      # API
```

### 排查步骤

1. **检查容器状态**
   ```bash
   docker-compose ps
   ```

2. **查看容器日志**
   ```bash
   docker-compose logs -f [service_name]
   ```

3. **验证网络连接**
   ```bash
   docker network ls
   docker network inspect knowledge_ai_network
   ```

4. **检查数据卷**
   ```bash
   docker volume ls
   docker volume inspect knowledge_ai_milvus_data
   ```

5. **重启服务**
   ```bash
   ./docker_manage.sh restart
   ```

## 生产部署建议

### 1. 安全性

- 修改默认凭证（MinIO）
- 启用 TLS/SSL
- 配置防火墙规则
- 定期备份数据

### 2. 监控

- 使用 Prometheus 采集指标
- 配置告警规则
- 监控 CPU、内存、磁盘使用

### 3. 备份和恢复

```bash
# 备份 Milvus 数据
docker run --rm -v knowledge_ai_milvus_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/milvus_backup.tar.gz -C /data .

# 恢复
docker run --rm -v knowledge_ai_milvus_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/milvus_backup.tar.gz -C /data
```

## 参考资源

- [Milvus 官方文档](https://milvus.io/docs)
- [Milvus Python SDK](https://github.com/milvus-io/pymilvus)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Docker Compose 文档](https://docs.docker.com/compose/)

## 支持和反馈

如遇到问题，请：
1. 查看本指南的故障排除部分
2. 检查 docker 和 Milvus 日志
3. 运行诊断脚本：`./docker_manage.sh status`
4. 提交问题报告（包含日志和复现步骤）
