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
