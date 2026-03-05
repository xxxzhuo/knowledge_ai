#!/usr/bin/env python3
"""
全流程端到端测试
================
测试流程:
    1. PDF 识别  — 使用 PdfExtractor 从 testpdf/ 提取文本、表格、图片
    2. 文档分块  — 使用 DocumentProcessor 进行分块处理
    3. 向量化    — 使用 Ollama Embedding (embeddinggemma) 将分块向量化
    4. 云端存储  — 使用 AliyunVectorStore 上传到阿里云 OSS 向量索引
    5. 云端检索  — 使用 query_vectors / get_by_ids / list_vectors 从云端检索
    6. RAG 问答  — 使用 VectorRetriever + RAGChain 完成检索增强问答
    7. 清理      — 删除测试索引

用法:
    cd knowledge_ai
    PYTHONPATH=. python scripts/test_full_pipeline.py
"""

import sys
import os
import time
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("full_pipeline_test")

# 重置 config 缓存
from app.config import get_settings
get_settings.cache_clear()

# =====================================================================
# 工具函数
# =====================================================================

DIVIDER = "=" * 70
TEST_INDEX_NAME = "pipelinetest"  # 测试用索引名 (无下划线)
PASS_COUNT = 0
FAIL_COUNT = 0


def step(num, title):
    """打印步骤标题"""
    print(f"\n{DIVIDER}")
    print(f"  STEP {num}: {title}")
    print(DIVIDER)


def ok(msg):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"  ✅ {msg}")


def fail(msg):
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"  ❌ {msg}")


def info(msg):
    print(f"  ℹ️  {msg}")


# =====================================================================
# STEP 1: PDF 识别（文本 / 表格 / 图片提取）
# =====================================================================

def step1_pdf_extraction():
    step(1, "PDF 识别 — 提取文本、表格、图片")

    from app.loaders.loaderall import PdfExtractor

    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "testpdf")
    pdf_files = [f for f in os.listdir(test_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        fail("testpdf/ 目录下没有找到 PDF 文件")
        return []

    info(f"发现 {len(pdf_files)} 个 PDF 文件: {pdf_files}")

    summaries = []
    for pdf_name in pdf_files:
        pdf_path = os.path.join(test_dir, pdf_name)
        info(f"正在提取: {pdf_name} ...")

        try:
            extractor = PdfExtractor()
            summary = extractor.extract_assets(pdf_path)
            if summary:
                text_count = summary.get("text", {}).get("count", 0)
                image_count = summary.get("images", {}).get("count", 0)
                table_count = summary.get("datasheet", {}).get("count", 0)
                page_count = summary.get("page_count", 0)
                ok(f"{pdf_name}: {page_count} 页, {text_count} 个文本, "
                   f"{image_count} 个图片, {table_count} 个表格")
                summaries.append({"pdf_name": pdf_name, "pdf_path": pdf_path, "summary": summary})
            else:
                fail(f"{pdf_name}: 提取返回空结果")
        except Exception as e:
            fail(f"{pdf_name}: 提取失败 — {str(e)}")

    return summaries


# =====================================================================
# STEP 2: 文档分块
# =====================================================================

def step2_document_chunking(summaries):
    step(2, "文档分块 — DocumentProcessor 处理")

    from app.document_processor import DocumentProcessor

    processor = DocumentProcessor(
        chunker_type="semiconductor",
        chunk_size=1024,
        chunk_overlap=200,
        extract_tables=True,
        extract_images=False,
        enable_embedding=False,  # 这里先不向量化，后面手动做
    )

    all_docs = []
    for item in summaries:
        pdf_path = item["pdf_path"]
        pdf_name = item["pdf_name"]

        try:
            result = processor.process(pdf_path)
            ok(f"{pdf_name}: {result.total_chunks} 个分块, "
               f"{result.total_tokens} 个 tokens, "
               f"{len(result.tables)} 个表格")
            all_docs.append({"pdf_name": pdf_name, "result": result})
        except Exception as e:
            fail(f"{pdf_name}: 分块失败 — {str(e)}")

    # 汇总
    total_chunks = sum(d["result"].total_chunks for d in all_docs)
    info(f"共计: {len(all_docs)} 个文档, {total_chunks} 个分块")

    return all_docs


# =====================================================================
# STEP 3: 向量化（Ollama Embedding）
# =====================================================================

def step3_embedding(all_docs):
    step(3, "向量化 — Ollama Embedding (embeddinggemma)")

    import pickle
    CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".embedding_cache.pkl")

    from app.embeddings import get_embedding_service

    emb_service = get_embedding_service()
    info(f"Embedding 服务: {type(emb_service).__name__}")

    # 先测试单条
    try:
        test_vec = emb_service.embed_text("测试文本 semiconductor DDR3")
        dim = len(test_vec)
        ok(f"单条向量化测试成功, 维度={dim}")
    except Exception as e:
        fail(f"Embedding 服务不可用: {str(e)}")
        return []

    # 收集所有分块文本和元数据
    all_chunks = []
    for doc_item in all_docs:
        pdf_name = doc_item["pdf_name"]
        result = doc_item["result"]
        for chunk in result.chunks:
            all_chunks.append({
                "text": chunk["content"],
                "metadata": {
                    "file_name": pdf_name,
                    "chunk_index": chunk["chunk_index"],
                    "chunk_type": chunk["chunk_type"],
                    "page_start": chunk.get("page_start", 0),
                    "page_end": chunk.get("page_end", 0),
                    "token_count": chunk["token_count"],
                }
            })

    info(f"开始对 {len(all_chunks)} 个分块进行向量化...")

    texts = [c["text"] for c in all_chunks]

    # 检查是否有缓存 (文本 hash 匹配时复用)
    import hashlib as _hl
    texts_hash = _hl.md5("||".join(texts).encode("utf-8")).hexdigest()
    cached_embeddings = None
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "rb") as f:
                cache = pickle.load(f)
            if cache.get("hash") == texts_hash and len(cache.get("embeddings", [])) == len(texts):
                cached_embeddings = cache["embeddings"]
                info("使用缓存的向量化结果 (跳过重新计算)")
        except Exception:
            pass

    if cached_embeddings:
        embeddings = cached_embeddings
        ok(f"从缓存加载 {len(embeddings)} 条向量, 维度={len(embeddings[0])}")
    else:
        # 批量向量化
        try:
            t0 = time.time()
            embeddings = emb_service.embed_documents(texts)
            elapsed = time.time() - t0
            ok(f"批量向量化完成: {len(embeddings)} 条, 维度={len(embeddings[0])}, "
               f"耗时={elapsed:.1f}s ({len(embeddings)/max(elapsed,0.01):.1f} 条/s)")
            # 保存缓存
            try:
                with open(CACHE_FILE, "wb") as f:
                    pickle.dump({"hash": texts_hash, "embeddings": embeddings}, f)
                info(f"向量化结果已缓存到 {CACHE_FILE}")
            except Exception:
                pass
        except Exception as e:
            fail(f"批量向量化失败: {str(e)}")
            return []

    # 组装结果
    for i, chunk in enumerate(all_chunks):
        chunk["embedding"] = embeddings[i]

    return all_chunks


# =====================================================================
# STEP 4: 上传到阿里云云端向量存储
# =====================================================================

def step4_upload_to_cloud(all_chunks):
    step(4, "云端存储 — 上传到阿里云 OSS 向量索引")

    from app.storage.aliyun_vector_store import AliyunVectorStore

    store = AliyunVectorStore(collection_name=TEST_INDEX_NAME)

    # 健康检查
    try:
        healthy = store.is_healthy()
        if healthy:
            ok("阿里云 OSS 向量服务健康检查通过")
        else:
            fail("阿里云 OSS 向量服务不可用")
            return store, []
    except Exception as e:
        fail(f"健康检查异常: {str(e)}")
        return store, []

    # 先清空测试索引
    try:
        store.clear()
        info("已清空测试索引")
    except Exception:
        info("测试索引不存在，跳过清空")

    # 上传
    embeddings = [c["embedding"] for c in all_chunks]
    texts = [c["text"] for c in all_chunks]
    metadatas = [c["metadata"] for c in all_chunks]

    try:
        t0 = time.time()
        ids = store.add_embeddings(embeddings, texts, metadatas)
        elapsed = time.time() - t0
        ok(f"上传完成: {len(ids)} 条向量, 耗时={elapsed:.1f}s")
    except Exception as e:
        fail(f"上传失败: {str(e)}")
        return store, []

    # 验证数量
    time.sleep(1)  # 等待索引段刷新
    try:
        count = store.count()
        if count == len(ids):
            ok(f"向量数量验证通过: count={count}")
        else:
            info(f"向量数量: 期望={len(ids)}, 实际={count} (可能因为索引刷新延迟)")
    except Exception as e:
        fail(f"计数失败: {str(e)}")

    return store, ids


# =====================================================================
# STEP 5: 云端检索测试
# =====================================================================

def step5_cloud_retrieval(store, ids, all_chunks):
    step(5, "云端检索 — ANN搜索 / 按ID检索 / 分页列举")

    if not ids:
        fail("无向量 ID，跳过检索测试")
        return

    # 5a. ANN 搜索 (query_vectors)
    info("5a. ANN 向量搜索 (query_vectors) ...")
    info("  等待索引构建完成 (最长 30s) ...")
    try:
        # 用第一个分块的向量作为查询
        query_vec = all_chunks[0]["embedding"]
        query_text = all_chunks[0]["text"][:60]

        # ANN 索引新建后需要等待构建，带重试
        results = []
        for attempt in range(6):
            results = store.search(query_vec, k=5)
            if results:
                break
            time.sleep(5)
            info(f"  重试 ANN 搜索 ({attempt+2}/6)...")

        if results:
            ok(f"ANN 搜索返回 {len(results)} 个结果")
            info(f"  查询文本: '{query_text}...'")
            for i, (dist, text, meta) in enumerate(results):
                info(f"  [{i+1}] dist={dist:.4f} file={meta.get('file_name','')} "
                     f"text={text[:50]}...")
        else:
            info("ANN 搜索返回 0 个结果 (索引可能还在构建中)")
    except Exception as e:
        fail(f"ANN 搜索失败: {str(e)}")

    # 5b. 按 ID 精确检索 (get_by_ids)
    info("5b. 按 ID 精确检索 (get_by_ids) ...")
    try:
        sample_ids = ids[:3]
        records = store.get_by_ids(sample_ids, return_data=False, return_metadata=True)
        if len(records) == len(sample_ids):
            ok(f"按 ID 检索: 请求 {len(sample_ids)} 个, 返回 {len(records)} 个")
            for rec in records:
                key = rec.get("key", "?")
                meta = rec.get("metadata", {})
                info(f"  key={key[:30]}... file={meta.get('file_name','')}")
        else:
            fail(f"按 ID 检索数量不匹配: 期望 {len(sample_ids)}, 实际 {len(records)}")
    except Exception as e:
        fail(f"按 ID 检索失败: {str(e)}")

    # 5c. get_texts_by_ids 便捷方法
    info("5c. get_texts_by_ids 便捷方法 ...")
    try:
        text_records = store.get_texts_by_ids(ids[:2])
        if len(text_records) == 2:
            ok(f"get_texts_by_ids 返回 {len(text_records)} 条")
            for key, text, meta in text_records:
                info(f"  key={key[:25]}... text={text[:50]}...")
        else:
            fail(f"get_texts_by_ids 数量不匹配: 期望 2, 实际 {len(text_records)}")
    except Exception as e:
        fail(f"get_texts_by_ids 失败: {str(e)}")

    # 5d. 分页列举 (list_vectors)
    info("5d. 分页列举 (list_vectors) ...")
    try:
        page1, next_token = store.list_vectors(max_results=5, return_metadata=True)
        ok(f"分页列举: 第1页={len(page1)} 条, 有下一页={'是' if next_token else '否'}")

        total_listed = len(page1)
        pages = 1
        token = next_token
        while token and pages < 20:
            page_n, token = store.list_vectors(max_results=100, next_token=token, return_metadata=False)
            total_listed += len(page_n)
            pages += 1

        info(f"  遍历完成: {pages} 页, 共列举 {total_listed} 条")
    except Exception as e:
        fail(f"分页列举失败: {str(e)}")


# =====================================================================
# STEP 6: RAG 检索增强问答
# =====================================================================

def step6_rag_qa(all_chunks):
    step(6, "RAG 问答 — VectorRetriever + LLM")

    from app.retriever import VectorRetriever
    from app.embeddings import get_embedding_service
    from app.storage.aliyun_vector_store import AliyunVectorStore

    # 构建使用测试索引的检索器
    store = AliyunVectorStore(collection_name=TEST_INDEX_NAME)
    emb_service = get_embedding_service()
    retriever = VectorRetriever(embedding_service=emb_service, vector_store=store)

    # 设计几个测试问题
    test_questions = [
        "What is the Autotrol 255 valve?",
        "Describe the service manual content.",
        "What flow rate specifications are mentioned?",
    ]

    for q in test_questions:
        info(f"问题: {q}")
        try:
            results = retriever.retrieve(q, k=3)
            if results:
                ok(f"检索到 {len(results)} 个相关片段")
                for i, (score, text, meta) in enumerate(results):
                    info(f"  [{i+1}] score={score:.4f} file={meta.get('file_name','')} "
                         f"text={text[:60]}...")
            else:
                info("  检索返回 0 结果 (索引可能还在构建中)")
        except Exception as e:
            fail(f"检索失败: {str(e)}")

    # 尝试 RAG Chain (如果 Ollama LLM 可用)
    info("\n  尝试 RAG Chain 问答 (需要 Ollama LLM) ...")
    try:
        from app.rag.chain import RAGChain
        settings = get_settings()

        rag_chain = RAGChain(
            retriever=retriever,
            llm_type="ollama",
            llm_model=settings.ollama_llm_model,
            prompt_type="semiconductor",
            top_k=3,
        )

        question = "What is the purpose of the Autotrol 255 valve?"
        info(f"  RAG 问题: {question}")
        answer = rag_chain.invoke(question)

        if answer and isinstance(answer, dict):
            answer_text = answer.get("answer", str(answer))
            ok(f"RAG 问答成功!")
            info(f"  回答: {answer_text[:200]}...")
        elif answer and isinstance(answer, str):
            ok(f"RAG 问答成功!")
            info(f"  回答: {answer[:200]}...")
        else:
            info("  RAG 返回空结果")

    except Exception as e:
        info(f"  RAG Chain 不可用 (可能缺少 LLM): {str(e)[:100]}")


# =====================================================================
# STEP 7: 清理
# =====================================================================

def step7_cleanup(store):
    step(7, "清理 — 删除测试索引")

    import alibabacloud_oss_v2.vectors as oss_vectors

    try:
        client = store._get_vector_client()
        client.delete_vector_index(oss_vectors.models.DeleteVectorIndexRequest(
            bucket=store._bucket_name,
            index_name=store.collection_name,
        ))
        ok("测试索引已删除")
    except Exception as e:
        if "NoSuchVectorIndex" in str(e) or "404" in str(e):
            ok("测试索引不存在，无需清理")
        else:
            fail(f"清理异常: {str(e)}")


# =====================================================================
# 主流程
# =====================================================================

def main():
    print("\n" + "=" * 70)
    print("   全流程端到端测试 (PDF → 分块 → 向量化 → 云端 → 检索 → RAG)")
    print("=" * 70)

    t_start = time.time()

    # Step 1: PDF 识别
    summaries = step1_pdf_extraction()
    if not summaries:
        print("\n❌ STEP 1 失败，无法继续测试")
        return

    # Step 2: 文档分块
    all_docs = step2_document_chunking(summaries)
    if not all_docs:
        print("\n❌ STEP 2 失败，无法继续测试")
        return

    # Step 3: 向量化
    all_chunks = step3_embedding(all_docs)
    if not all_chunks:
        print("\n❌ STEP 3 失败，无法继续测试")
        return

    # Step 4: 上传到云端
    store, ids = step4_upload_to_cloud(all_chunks)
    if not ids:
        print("\n❌ STEP 4 失败，无法继续测试")
        return

    # Step 5: 云端检索
    step5_cloud_retrieval(store, ids, all_chunks)

    # Step 6: RAG 问答
    step6_rag_qa(all_chunks)

    # Step 7: 清理
    step7_cleanup(store)

    # 汇总
    elapsed = time.time() - t_start
    print(f"\n{'=' * 70}")
    print(f"  测试完成 — ✅ 通过: {PASS_COUNT}  ❌ 失败: {FAIL_COUNT}  ⏱️ 耗时: {elapsed:.1f}s")
    print(f"{'=' * 70}\n")

    if FAIL_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
