#!/usr/bin/env python3
"""Debug: check exact metadata size for the failing vector"""
import sys, os, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The failing key prefix is 7ede3948a817
# Let's find which text produces this hash

from app.config import get_settings
get_settings.cache_clear()
from app.document_processor import DocumentProcessor

processor = DocumentProcessor(chunker_type='semiconductor', chunk_size=1024, chunk_overlap=200,
                              extract_tables=False, extract_images=False, enable_embedding=False)
result = processor.process('testpdf/255.PDF')

target_hash = "7ede3948a817"
for i, chunk in enumerate(result.chunks):
    text = chunk["content"]
    h = hashlib.md5(text.encode("utf-8")).hexdigest()[:12]
    if h == target_hash:
        meta = {
            "file_name": "255.PDF",
            "chunk_index": str(chunk["chunk_index"]),
            "chunk_type": chunk["chunk_type"],
            "page_start": str(chunk.get("page_start", 0)),
            "page_end": str(chunk.get("page_end", 0)),
            "token_count": str(chunk["token_count"]),
        }
        # Add text
        meta["text"] = text
        raw_size = len(json.dumps(meta, ensure_ascii=False).encode("utf-8"))
        text_bytes = len(text.encode("utf-8"))
        
        print(f"FOUND: chunk[{i}] hash={h}")
        print(f"  text_chars={len(text)}, text_bytes={text_bytes}")
        print(f"  full_meta_json_bytes={raw_size}")
        print(f"  meta_without_text_bytes={len(json.dumps({k:v for k,v in meta.items() if k!='text'}, ensure_ascii=False).encode('utf-8'))}")
        print(f"  text[:100] = {text[:100]}")
        
        # Now simulate proper truncation
        MAX = 2000
        overhead = len(json.dumps({k:v for k,v in meta.items() if k!="text"}, ensure_ascii=False).encode("utf-8"))
        budget = max(0, MAX - overhead - 14)
        trunc = text.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
        meta["text"] = trunc
        final = len(json.dumps(meta, ensure_ascii=False).encode("utf-8"))
        print(f"  truncated: text_chars={len(trunc)}, final_meta_bytes={final}, OK={final<=2048}")
        break
else:
    print(f"Hash {target_hash} not found. First 5 hashes:")
    for i, chunk in enumerate(result.chunks[:5]):
        h = hashlib.md5(chunk["content"].encode("utf-8")).hexdigest()[:12]
        print(f"  chunk[{i}]: {h}")
