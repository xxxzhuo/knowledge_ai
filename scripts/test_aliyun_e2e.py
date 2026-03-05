"""End-to-end test: create index, put vectors, search, delete, clear."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
get_settings.cache_clear()

from app.storage.aliyun_vector_store import AliyunVectorStore

def main():
    store = AliyunVectorStore(collection_name="testindex")

    # 1. Health check
    print("1. Health check...")
    assert store.is_healthy(), "Health check failed"
    print("   OK")

    # 2. Ensure index + count
    print("2. Count (auto-creates index)...")
    count = store.count()
    print(f"   count = {count}")

    # 3. Put vectors (3 test vectors, dim=768)
    print("3. Put vectors...")
    dim = 768
    import random
    random.seed(42)
    embeddings = [[random.gauss(0, 1) for _ in range(dim)] for _ in range(3)]
    texts = [
        "MT41K256M16TW-107 是镁光 DDR3 4Gb 芯片",
        "K4A8G165WC-BCWE 是三星 DDR4 8Gb 颗粒",
        "IS43TR16512BL-125KBL 是 ISSI DDR3L 8Gb 存储器",
    ]
    metadatas = [
        {"brand": "micron", "type": "DDR3"},
        {"brand": "samsung", "type": "DDR4"},
        {"brand": "issi", "type": "DDR3L"},
    ]

    ids = store.add_embeddings(embeddings, texts, metadatas)
    print(f"   inserted {len(ids)} vectors: {ids}")

    # 4. Count after insert
    print("4. Count after insert...")
    count = store.count()
    print(f"   count = {count}")

    # 5. Search
    print("5. Search (query = first embedding)...")
    results = store.search(embeddings[0], k=3)
    print(f"   got {len(results)} results:")
    for dist, text, meta in results:
        print(f"     dist={dist:.4f} text={text[:40]}... meta={meta}")

    # 5b. get_by_ids (云端精确检索)
    print(f"5b. get_by_ids({ids[:2]})...")
    records = store.get_by_ids(ids[:2], return_data=False, return_metadata=True)
    print(f"   returned {len(records)} records:")
    for rec in records:
        key = rec.get("key", "?")
        meta = rec.get("metadata", {})
        txt = meta.get("text", "")[:40]
        print(f"     key={key} text={txt}... brand={meta.get('brand','')}")
    assert len(records) == 2, f"Expected 2 records, got {len(records)}"

    # 5c. list_vectors (分页列举)
    print("5c. list_vectors(max_results=2)...")
    page_vecs, next_token = store.list_vectors(max_results=2, return_metadata=True)
    print(f"   page1: {len(page_vecs)} vectors, next_token={'Yes' if next_token else 'None'}")
    for v in page_vecs:
        k = v.get("key", "?")
        m = v.get("metadata", {})
        print(f"     key={k} brand={m.get('brand','')}")
    if next_token:
        page2, token2 = store.list_vectors(max_results=10, next_token=next_token, return_metadata=True)
        print(f"   page2: {len(page2)} vectors, next_token={'Yes' if token2 else 'None'}")

    # 5d. get_texts_by_ids (便捷方法)
    print(f"5d. get_texts_by_ids({ids[1:]})...")
    text_results = store.get_texts_by_ids(ids[1:])
    print(f"   returned {len(text_results)} records:")
    for key, text, meta in text_results:
        print(f"     key={key} text={text[:40]}... meta={meta}")
    assert len(text_results) == 2, f"Expected 2, got {len(text_results)}"

    # 6. Delete one vector
    print(f"6. Delete vector {ids[2]}...")
    ok = store.delete([ids[2]])
    print(f"   delete ok = {ok}")
    count = store.count()
    print(f"   count after delete = {count}")

    # 7. Clear
    print("7. Clear (delete + recreate index)...")
    ok = store.clear()
    print(f"   clear ok = {ok}")
    count = store.count()
    print(f"   count after clear = {count}")

    print("\nALL E2E TESTS PASSED!")

if __name__ == "__main__":
    main()
