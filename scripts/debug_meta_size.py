#!/usr/bin/env python3
"""Debug metadata size"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.document_processor import DocumentProcessor

processor = DocumentProcessor(chunker_type='semiconductor', chunk_size=1024, chunk_overlap=200, enable_embedding=False)
result = processor.process('testpdf/255.PDF')

for i, chunk in enumerate(result.chunks[:5]):
    meta = {
        'file_name': '255.PDF',
        'chunk_index': str(chunk['chunk_index']),
        'chunk_type': chunk['chunk_type'],
        'page_start': str(chunk.get('page_start', 0)),
        'page_end': str(chunk.get('page_end', 0)),
        'token_count': str(chunk['token_count']),
    }
    non_text_size = len(json.dumps(meta, ensure_ascii=False).encode('utf-8'))
    text_bytes = len(chunk['content'].encode('utf-8'))
    
    # Simulate what aliyun_vector_store does
    text_budget = max(0, 2048 - non_text_size - 62)
    truncated = chunk['content'].encode('utf-8')[:text_budget].decode('utf-8', errors='ignore')
    
    meta['text'] = truncated
    final_size = len(json.dumps(meta, ensure_ascii=False).encode('utf-8'))
    
    print(f"chunk[{i}]: non_text={non_text_size}B text_orig={text_bytes}B budget={text_budget}B truncated={len(truncated)}chars final_meta={final_size}B")
