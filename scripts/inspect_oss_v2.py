"""Inspect alibabacloud_oss_v2.vectors API."""
import inspect
import alibabacloud_oss_v2.vectors as oss_vectors

# Core APIs - check signatures
for method_name in ['put_vector_index', 'put_vectors', 'query_vectors', 'delete_vectors', 'get_vector_index', 'get_vectors', 'list_vectors']:
    method = getattr(oss_vectors.Client, method_name)
    sig = inspect.signature(method)
    print(f"\n--- {method_name}{sig} ---")

# Check key model fields
models = oss_vectors.models
for cls_name in [
    'PutVectorIndexRequest', 'PutVectorsRequest', 'QueryVectorsRequest',
    'DeleteVectorsRequest', 'GetVectorsRequest',
    'GetVectorIndexResult', 'QueryVectorsResult', 'PutVectorsResult',
    'ListVectorsRequest', 'ListVectorsResult',
]:
    cls = getattr(models, cls_name)
    print(f"\n=== {cls_name} ===")
    sig = inspect.signature(cls.__init__)
    for pname, p in sig.parameters.items():
        if pname == 'self':
            continue
        annot = p.annotation if p.annotation != inspect.Parameter.empty else '?'
        default = p.default if p.default != inspect.Parameter.empty else '(required)'
        print(f"  {pname}: {annot} = {default}")
