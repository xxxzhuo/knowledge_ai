# 第二阶段快速参考指南

## 📚 文档加载器快速使用

### PDF 加载
```python
from app.loaders import PDFLoader

# 基础使用
loader = PDFLoader("document.pdf")
doc = loader.load()

print(f"文件: {doc.file_name}")
print(f"页数: {doc.page_count}")
print(f"内容: {doc.content[:200]}...")

# 获取逐页内容
pages = loader.get_pages_content()
for page in pages:
    print(f"页 {page['page_number']}: {page['char_count']} 字符")
```

### 表格提取
```python
from app.loaders import TableExtractor

extractor = TableExtractor()

# 提取表格 (自动检测)
tables = extractor.extract_tables_from_pdf("document.pdf")

# 带回退的智能提取
tables = extractor.extract_tables_with_fallback("document.pdf")

for table in tables:
    print(f"表格 {table['table_id']}: {table['rows']}行 x {table['columns']}列")
    print(f"精度: {table['accuracy']:.1f}%")
```

### 图片加载和 OCR
```python
from app.loaders import ImageLoader, PDFImageExtractor

# 加载单个图片并识别文字
loader = ImageLoader("image.jpg", enable_ocr=True)
doc = loader.load()
print(f"识别文字: {doc.content}")

# 从 PDF 提取图片
extractor = PDFImageExtractor(enable_ocr=True)
images = extractor.extract_images_from_pdf("document.pdf", output_dir="./images")
for img in images:
    print(f"页 {img['page_number']}: {img['size']}")
```

---

## ✂️ 文本分块快速使用

### 半导体分块器
```python
from app.chunking import SemiconductorTextSplitter

# 初始化
splitter = SemiconductorTextSplitter(
    chunk_size=1024,      # 目标分块大小
    chunk_overlap=200,    # 分块间重叠
    preserve_sections=True  # 保留章节边界
)

# 分块处理
text = "... 很长的半导体文档 ..."
chunks = splitter.chunk(text, metadata={"source": "spec.pdf"})

# 使用分块
for chunk in chunks:
    print(f"分块 {chunk.chunk_index}:")
    print(f"  类型: {chunk.chunk_type.value}")
    print(f"  大小: {len(chunk.content)} 字符")
    print(f"  Tokens: {chunk.token_count}")
```

### 表格感知分块器
```python
from app.chunking import TableAwareChunker

chunker = TableAwareChunker(
    chunk_size=1024,
    chunk_overlap=200,
    preserve_tables=True  # 保持表格完整
)

# 分块处理
chunks = chunker.chunk(mixed_content_text)

# 提取识别到的表格
tables = chunker.extract_tables(mixed_content_text)
print(f"识别到 {len(tables)} 个表格")

# 合并过小的分块
chunks = chunker.merge_small_chunks(chunks, min_size=100)
```

---

## 🔄 完整处理管道

### 单文件处理
```python
from app.document_processor import DocumentProcessor

# 创建处理器
processor = DocumentProcessor(
    chunker_type="semiconductor",  # 或 "table_aware"
    chunk_size=1024,
    chunk_overlap=200,
    enable_ocr=False,
    extract_tables=True,
    extract_images=False
)

# 处理文档
result = processor.process("document.pdf")

# 使用结果
print(f"分块数: {result.total_chunks}")
print(f"Tokens: {result.total_tokens}")
print(f"表格数: {len(result.tables)}")

# 访问分块
for chunk in result.chunks[:5]:
    print(f"- 分块 {chunk['chunk_index']}: {chunk['content'][:100]}...")
```

### 批量处理
```python
# 批量处理多个文件
files = ["doc1.pdf", "doc2.pdf", "image.jpg"]
results = processor.batch_process(files, continue_on_error=True)

# 查看结果
for result in results:
    print(f"{result.file_name}: "
          f"{result.total_chunks} 分块, "
          f"{result.total_tokens} Tokens")
```

---

## 🌐 API 端点使用

### 单文件上传处理
```bash
curl -X POST "http://localhost:8000/api/v1/process" \
  -F "file=@document.pdf" \
  -F "chunker_type=semiconductor" \
  -F "chunk_size=1024" \
  -F "chunk_overlap=200" \
  -F "enable_ocr=false" \
  -F "extract_tables=true" \
  -F "extract_images=false"
```

**响应示例:**
```json
{
  "success": true,
  "file_name": "document.pdf",
  "file_type": "pdf",
  "total_chunks": 42,
  "total_tokens": 15234,
  "tables_count": 3,
  "images_count": 0,
  "message": "文档处理成功，耗时 2.34 秒",
  "processing_time": 2.34
}
```

### 批量处理
```bash
curl -X POST "http://localhost:8000/api/v1/batch-process" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@image.jpg" \
  -F "chunker_type=table_aware"
```

### 查询处理状态
```bash
curl "http://localhost:8000/api/v1/processing-status/document-id-uuid"
```

**响应:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "document.pdf",
  "status": "completed",
  "total_chunks": 42,
  "total_tokens": 15234,
  "created_at": "2026-02-28T10:30:00",
  "updated_at": "2026-02-28T10:32:34"
}
```

### 获取分块列表
```bash
curl "http://localhost:8000/api/v1/document-chunks/document-id-uuid?skip=0&limit=10"
```

**响应:**
```json
{
  "total": 42,
  "chunks": [
    {
      "chunk_id": "uuid",
      "chunk_index": 0,
      "content": "预览文本...",
      "content_full": "完整内容",
      "type": "paragraph"
    },
    ...
  ]
}
```

---

## 🔧 常见配置场景

### 场景 1: 处理芯片规格书 (PDF)
```python
processor = DocumentProcessor(
    chunker_type="semiconductor",  # 芯片优化
    chunk_size=1024,               # 适中大小
    chunk_overlap=300,             # 较大重叠保留上下文
    enable_ocr=False,              # PDF通常不需要
    extract_tables=True,           # 规格表很重要
    extract_images=True            # 电路图等
)
```

### 场景 2: 处理混合内容文档
```python
processor = DocumentProcessor(
    chunker_type="table_aware",    # 表格感知
    chunk_size=1024,
    chunk_overlap=200,
    enable_ocr=False,
    extract_tables=True,
    extract_images=False
)
```

### 场景 3: 处理扫描的技术文档 (图片)
```python
processor = DocumentProcessor(
    chunker_type="semiconductor",
    chunk_size=512,                # 较小分块
    chunk_overlap=100,
    enable_ocr=True,               # 需要OCR识别
    extract_tables=True,           # 扫描文档可能出现表格
    extract_images=False
)
```

---

## 📊 常见分块类型

| 类型 | 特征 | 常见场景 |
|------|------|---------|
| `paragraph` | 多段落文本 | 技术说明、描述 |
| `sentence` | 单句 | 不常见，通常合并 |
| `section` | 技术规范段 | 芯片参数、规格数据 |
| `table` | 表格格式 | 数据对比、规格表 |
| `code` | 代码块 | 配置、示例 |
| `list` | 列表项 | 功能列表、说明 |
| `mixed` | 混合格式 | 多格式段落 |

---

## ⚡ 性能建议

### 分块大小选择
```
- 512 字符: 短内容、提高精度 (检索友好)
- 1024 字符: 平衡选择 (推荐) ⭐
- 2048 字符: 长内容、保留更多上下文
```

### 重叠大小建议
```
- 100 字符: 最小重叠，节省存储
- 200 字符: 标准选择，保留基本上下文 ⭐
- 300+ 字符: 最大重叠，确保信息连贯
```

### OCR 性能注意
```
⚠️  OCR 处理较慢，仅在需要时启用
- PDF 文本可提取: enable_ocr=False (快速)
- 扫描/图片文档: enable_ocr=True (慢但必需)

处理时间估计:
- PDF: 通常 < 1 秒/页
- 图片 + OCR: 1-3 秒/页
```

---

## 🐛 调试技巧

### 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 现在会看到详细的处理日志
processor.process("document.pdf")
```

### 检查分块内容
```python
result = processor.process("document.pdf")

for chunk in result.chunks:
    print(f"\n━━ 分块 {chunk['chunk_index']} ━━")
    print(f"类型: {chunk['chunk_type']}")
    print(f"字符数: {chunk['char_count']}")
    print(f"Token数: {chunk['token_count']}")
    print(f"内容:\n{chunk['content']}")
```

### 表格检查
```python
result = processor.process("document.pdf")

print(f"提取到 {len(result.tables)} 个表格:")
for table in result.tables:
    print(f"  - 表格 {table['table_id']}: "
          f"{table['rows']}行 x {table['columns']}列, "
          f"精度 {table['accuracy']:.1f}%")
```

---

## 💾 数据库查询

### 查看已处理的文档
```sql
SELECT id, file_name, chunk_count, created_at 
FROM documents 
WHERE processed = 'completed' 
ORDER BY created_at DESC;
```

### 查看某文档的所有分块
```sql
SELECT chunk_index, content_type, char_count 
FROM chunks 
WHERE doc_id = 'document-uuid' 
ORDER BY chunk_index;
```

### 统计处理信息
```sql
SELECT 
  COUNT(*) as total_documents,
  SUM(chunk_count) as total_chunks,
  AVG(chunk_count) as avg_chunks_per_doc
FROM documents 
WHERE processed = 'completed';
```

---

## 📖 更多资源

- **详细文档**: [PHASE2_SUMMARY.md](./PHASE2_SUMMARY.md)
- **项目状态**: [PROJECT_STATUS.md](./PROJECT_STATUS.md)
- **API 文档**: http://localhost:8000/docs (运行服务后)
- **第一阶段**: [PHASE1_SUMMARY.md](./PHASE1_SUMMARY.md)

---

**最后更新:** 2026年2月28日  
**版本:** 0.2.0
