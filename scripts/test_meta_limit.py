#!/usr/bin/env python3
"""Quick test: verify metadata 2048B fix works with large text"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
get_settings.cache_clear()

from app.storage.aliyun_vector_store import AliyunVectorStore
import random

store = AliyunVectorStore(collection_name="metatest")
random.seed(99)

dim = 768
embs = [[random.gauss(0, 1) for _ in range(dim)] for _ in range(3)]
texts = [
    "A" * 2000,  # pure ASCII 2000 chars
    "半导体芯片数据手册" * 200,  # Chinese ~600 chars × 3 bytes = 1800B
    "MT41K256M16TW-107 DDR3 datasheet page content " * 50,  # ~2350 chars
]
metadatas = [
    {"file_name": "test.pdf", "chunk_index": "0", "page_start": "1"},
    {"file_name": "中文.pdf", "chunk_index": "1", "page_start": "5"},
    {"file_name": "datasheet.pdf", "chunk_index": "2", "page_start": "10", "extra_field": "very long metadata field"},
]

print("Uploading 3 vectors with large text...")
try:
    ids = store.add_embeddings(embs, texts, metadatas)
    print(f"OK: inserted {len(ids)} vectors")
    
    # Verify retrievable
    records = store.get_by_ids(ids, return_metadata=True)
    for r in records:
        meta = r.get("metadata", {})
        text = meta.get("text", "")
        print(f"  key={r['key'][:20]}... text_len={len(text)} chars")
    
    # Cleanup
    store.delete(ids)
    print("Cleanup done")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
