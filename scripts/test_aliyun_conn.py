"""Quick test: connect to Aliyun OSS Vector and check health."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
s = get_settings()
print(f"VECTOR_STORE_TYPE = {s.vector_store_type}")
print(f"BUCKET = {s.aliyun_oss_bucket_name}")
print(f"REGION = {s.aliyun_region}")
print(f"AK = {s.aliyun_oss_access_key_id[:8]}***")

from app.storage.aliyun_vector_store import AliyunVectorStore
store = AliyunVectorStore()

print("\nChecking health...")
healthy = store.is_healthy()
print(f"is_healthy = {healthy}")

if healthy:
    print("\nChecking count...")
    count = store.count()
    print(f"vector count = {count}")
    print("\nConnection OK!")
else:
    print("\nConnection FAILED - check credentials/endpoint")
