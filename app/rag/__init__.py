"""RAG 模块 - 检索增强生成。"""

from app.rag.reranker import (
    Reranker,
    SimpleReranker,
    CrossEncoderReranker,
    HybridReranker,
    get_reranker
)
from app.rag.chain import (
    RAGChain,
    MultiChainRAG,
    create_rag_chain
)
from app.rag.prompts import (
    QA_PROMPT,
    SEMICONDUCTOR_QA_PROMPT,
    DATASHEET_QUERY_PROMPT,
    CONVERSATIONAL_PROMPT,
    format_docs,
    format_chat_history,
    get_prompt_by_type
)

__all__ = [
    # Rerankers
    "Reranker",
    "SimpleReranker",
    "CrossEncoderReranker",
    "HybridReranker",
    "get_reranker",
    
    # Chains
    "RAGChain", 
    "MultiChainRAG",
    "create_rag_chain",
    
    # Prompts
    "QA_PROMPT",
    "SEMICONDUCTOR_QA_PROMPT",
    "DATASHEET_QUERY_PROMPT",
    "CONVERSATIONAL_PROMPT",
    "format_docs",
    "format_chat_history",
    "get_prompt_by_type",
]

