"""Inspect credentials and config patterns."""
import inspect
import alibabacloud_oss_v2 as oss

# Check credentials providers
print("=== Credential providers ===")
for name in sorted(dir(oss.credentials)):
    if 'Provider' in name or 'Credentials' in name:
        print(f"  {name}")

# Check config fields
print("\n=== Config fields ===")
cfg = oss.config.load_default()
for attr in sorted(dir(cfg)):
    if not attr.startswith('_') and not callable(getattr(cfg, attr)):
        print(f"  {attr} = {getattr(cfg, attr)!r}")

# Check GetVectorBucketRequest
models = oss.vectors.models if hasattr(oss, 'vectors') else __import__('alibabacloud_oss_v2.vectors', fromlist=['models']).models
print("\n=== GetVectorBucketRequest ===")
sig = inspect.signature(models.GetVectorBucketRequest.__init__)
for pname, p in sig.parameters.items():
    if pname == 'self':
        continue
    annot = p.annotation if p.annotation != inspect.Parameter.empty else '?'
    default = p.default if p.default != inspect.Parameter.empty else '(required)'
    print(f"  {pname}: {annot} = {default}")

# Check StaticCredentialsProvider if exists
print("\n=== StaticCredentialsProvider ===")
if hasattr(oss.credentials, 'StaticCredentialsProvider'):
    sig = inspect.signature(oss.credentials.StaticCredentialsProvider.__init__)
    for pname, p in sig.parameters.items():
        if pname == 'self':
            continue
        print(f"  {pname}")
else:
    print("  Not available")
    # Check alternative
    for name in dir(oss.credentials):
        if 'static' in name.lower() or 'credential' in name.lower():
            print(f"  Found: {name}")
