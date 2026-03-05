"""Verify refactored aliyun vector store with V2 SDK."""
import sys

def main():
    # 1. Config
    from app.config import get_settings
    s = get_settings()
    print(f"vector_store_type = {s.vector_store_type}")
    print(f"aliyun_region = {repr(s.aliyun_region)}")
    print(f"aliyun_account_id = {repr(s.aliyun_account_id)}")
    print(f"aliyun_vector_batch_size = {s.aliyun_vector_batch_size}")
    
    # Verify old fields removed
    assert not hasattr(s, 'aliyun_oss_prefix'), "aliyun_oss_prefix should be removed"
    assert not hasattr(s, 'aliyun_search_endpoint'), "aliyun_search_endpoint should be removed"
    assert hasattr(s, 'aliyun_region'), "aliyun_region must exist"
    assert hasattr(s, 'aliyun_account_id'), "aliyun_account_id must exist"
    print("Config fields OK")
    
    # 2. Import AliyunVectorStore
    from app.storage.aliyun_vector_store import AliyunVectorStore
    print("AliyunVectorStore imported OK")
    
    # 3. Import from __init__
    from app.storage import VectorStore, AliyunVectorStore as AV, get_vector_store
    print("storage __init__ imported OK")
    
    # 4. Check no numpy dependency
    import importlib
    spec = importlib.util.find_spec("app.storage.aliyun_vector_store")
    with open(spec.origin) as f:
        src = f.read()
    assert "import numpy" not in src, "Should not import numpy anymore"
    assert "import oss2" not in src, "Should not import oss2 anymore"
    assert "alibabacloud_oss_v2" in src, "Should use alibabacloud_oss_v2"
    print("SDK dependency check OK")
    
    # 5. Verify interface completeness
    base_methods = {m for m in dir(VectorStore) if not m.startswith('_') and callable(getattr(VectorStore, m))}
    aliyun_methods = {m for m in dir(AV) if not m.startswith('_') and callable(getattr(AV, m))}
    missing = base_methods - aliyun_methods
    if missing:
        print(f"FAIL: missing methods: {missing}")
        sys.exit(1)
    print("Interface completeness OK")
    
    # 6. Verify alibabacloud_oss_v2 is importable
    import alibabacloud_oss_v2 as oss
    import alibabacloud_oss_v2.vectors as oss_vectors
    print(f"alibabacloud-oss-v2 version: {oss.__version__ if hasattr(oss, '__version__') else 'installed'}")
    
    # 7. Verify other consumers
    from app.retriever.vector_retriever import VectorRetriever
    print("VectorRetriever imported OK")
    from app.document_processor import DocumentProcessor
    print("DocumentProcessor imported OK")
    from app.api.health import check_vector_store
    print("health.py imported OK")
    
    print("\nALL VERIFICATIONS PASSED")

if __name__ == "__main__":
    main()
