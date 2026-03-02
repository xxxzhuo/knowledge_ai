"""Verify aliyun vector store integration."""
import sys

def main():
    # 1. Config
    from app.config import get_settings
    s = get_settings()
    print(f"vector_store_type = {s.vector_store_type}")
    print(f"aliyun_oss_endpoint = {repr(s.aliyun_oss_endpoint)}")
    print(f"aliyun_vector_batch_size = {s.aliyun_vector_batch_size}")
    
    # 2. Import AliyunVectorStore
    from app.storage.aliyun_vector_store import AliyunVectorStore
    print("AliyunVectorStore imported OK")
    
    # 3. Import from __init__
    from app.storage import VectorStore, MilvusStore, AliyunVectorStore as AV, get_vector_store
    print("storage __init__ imported OK")
    
    # 4. Check interface completeness
    base_methods = {m for m in dir(VectorStore) if not m.startswith('_') and callable(getattr(VectorStore, m))}
    aliyun_methods = {m for m in dir(AV) if not m.startswith('_') and callable(getattr(AV, m))}
    missing = base_methods - aliyun_methods
    if missing:
        print(f"FAIL: missing methods: {missing}")
        sys.exit(1)
    else:
        print("OK: AliyunVectorStore implements all VectorStore methods")
    
    # 5. Import retriever
    from app.retriever.vector_retriever import VectorRetriever
    print("VectorRetriever imported OK")
    
    # 6. Import document_processor
    from app.document_processor import DocumentProcessor
    print("DocumentProcessor imported OK")
    
    # 7. Import health
    from app.api.health import check_vector_store
    print("health.py imported OK")
    
    print("\nALL VERIFICATIONS PASSED")

if __name__ == "__main__":
    main()
