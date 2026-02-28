"""RAG Chain 实现 - 使用 LangChain Expression Language (LCEL)。"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from operator import itemgetter

from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableParallel,
    RunnableLambda
)
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from app.retriever import VectorRetriever
from app.rag.reranker import get_reranker, Reranker
from app.rag.prompts import (
    QA_PROMPT,
    SEMICONDUCTOR_QA_PROMPT,
    CONVERSATIONAL_PROMPT,
    format_docs,
    format_chat_history,
    get_prompt_by_type
)
from app.config import get_settings

logger = logging.getLogger(__name__)


class RAGChain:
    """
    RAG Chain - 使用 LCEL 构建的检索增强生成链
    
    特性:
        - 基于 LCEL 的声明式链构建
        - 支持多种 LLM (OpenAI/Ollama)
        - 集成重排序器
        - 可配置的 prompt 模板
        - 流式输出支持
    """
    
    def __init__(
        self,
        retriever: Optional[VectorRetriever] = None,
        reranker: Optional[Reranker] = None,
        llm_type: str = "ollama",
        llm_model: Optional[str] = None,
        prompt_type: str = "default",
        temperature: float = 0.1,
        top_k: int = 5
    ):
        """
        初始化 RAG Chain
        
        参数:
            retriever: 向量检索器
            reranker: 重排序器
            llm_type: LLM 类型 (openai/ollama)
            llm_model: LLM 模型名称
            prompt_type: prompt 类型
            temperature: 生成温度
            top_k: 检索文档数量
        """
        settings = get_settings()
        
        # 初始化检索器
        self.retriever = retriever or VectorRetriever()
        
        # 初始化重排序器
        self.reranker = reranker or get_reranker("simple", min_similarity=0.3)
        
        # 初始化 LLM
        self.llm_type = llm_type
        if llm_type == "openai":
            self.llm = ChatOpenAI(
                model=llm_model or settings.openai_model,
                temperature=temperature,
                openai_api_key=settings.openai_api_key
            )
        elif llm_type == "ollama":
            self.llm = ChatOllama(
                model=llm_model or "qwen2.5:7b",
                temperature=temperature,
                base_url=settings.ollama_host
            )
        else:
            raise ValueError(f"不支持的 LLM 类型: {llm_type}")
        
        # 获取 prompt 模板
        self.prompt = get_prompt_by_type(prompt_type)
        self.prompt_type = prompt_type
        
        # 配置参数
        self.top_k = top_k
        self.temperature = temperature
        
        # 构建 LCEL chain
        self._build_chain()
        
        logger.debug(
            f"初始化 RAG Chain - "
            f"LLM: {llm_type}, "
            f"Prompt: {prompt_type}, "
            f"Top-K: {top_k}"
        )
    
    def _build_chain(self):
        """构建 LCEL chain"""
        
        # 定义检索函数
        def retrieve_and_rerank(query: str) -> List[Tuple[float, str, Dict[str, Any]]]:
            """检索并重排序"""
            # 1. 向量检索
            docs = self.retriever.retrieve(query, k=self.top_k * 2)
            
            # 2. 重排序
            reranked = self.reranker.rerank(query, docs, self.top_k)
            
            return reranked
        
        # 构建 LCEL chain
        # 方式1: 基础 QA Chain
        if self.prompt_type in ["default", "semiconductor", "datasheet", "process"]:
            self.chain = (
                {
                    "context": RunnableLambda(retrieve_and_rerank) | RunnableLambda(format_docs),
                    "question": RunnablePassthrough()
                }
                | self.prompt
                | self.llm
                | StrOutputParser()
            )
        
        # 方式2: 带对话历史的 Chain
        elif self.prompt_type == "conversational":
            self.chain = (
                {
                    "context": itemgetter("question") | RunnableLambda(retrieve_and_rerank) | RunnableLambda(format_docs),
                    "chat_history": itemgetter("chat_history") | RunnableLambda(format_chat_history),
                    "question": itemgetter("question")
                }
                | self.prompt
                | self.llm
                | StrOutputParser()
            )
        
        else:
            # 默认使用基础 QA Chain
            self.chain = (
                {
                    "context": RunnableLambda(retrieve_and_rerank) | RunnableLambda(format_docs),
                    "question": RunnablePassthrough()
                }
                | self.prompt
                | self.llm
                | StrOutputParser()
            )
    
    def invoke(self, query: str, **kwargs) -> str:
        """
        执行 RAG 查询
        
        参数:
            query: 用户问题
            **kwargs: 额外参数（如 chat_history）
            
        返回:
            生成的答案
        """
        try:
            if self.prompt_type == "conversational":
                # 需要提供 question 和 chat_history
                result = self.chain.invoke({
                    "question": query,
                    "chat_history": kwargs.get("chat_history", [])
                })
            else:
                # 直接传入问题
                result = self.chain.invoke(query)
            
            return result
            
        except Exception as e:
            logger.error(f"RAG 查询失败: {str(e)}", exc_info=True)
            raise
    
    async def ainvoke(self, query: str, **kwargs) -> str:
        """
        异步执行 RAG 查询
        
        参数:
            query: 用户问题
            **kwargs: 额外参数
            
        返回:
            生成的答案
        """
        try:
            if self.prompt_type == "conversational":
                result = await self.chain.ainvoke({
                    "question": query,
                    "chat_history": kwargs.get("chat_history", [])
                })
            else:
                result = await self.chain.ainvoke(query)
            
            return result
            
        except Exception as e:
            logger.error(f"异步 RAG 查询失败: {str(e)}", exc_info=True)
            raise
    
    def stream(self, query: str, **kwargs):
        """
        流式执行 RAG 查询
        
        参数:
            query: 用户问题
            **kwargs: 额外参数
            
        Returns:
            生成器，逐个返回答案片段
        """
        try:
            if self.prompt_type == "conversational":
                for chunk in self.chain.stream({
                    "question": query,
                    "chat_history": kwargs.get("chat_history", [])
                }):
                    yield chunk
            else:
                for chunk in self.chain.stream(query):
                    yield chunk
            

            
        except Exception as e:
            logger.error(f"流式 RAG 查询失败: {str(e)}", exc_info=True)
            raise
    
    async def astream(self, query: str, **kwargs):
        """
        异步流式执行 RAG 查询
        
        参数:
            query: 用户问题
            **kwargs: 额外参数
            
        Returns:
            异步生成器，逐个返回答案片段
        """
        try:
            if self.prompt_type == "conversational":
                async for chunk in self.chain.astream({
                    "question": query,
                    "chat_history": kwargs.get("chat_history", [])
                }):
                    yield chunk
            else:
                async for chunk in self.chain.astream(query):
                    yield chunk
            

            
        except Exception as e:
            logger.error(f"异步流式 RAG 查询失败: {str(e)}", exc_info=True)
            raise
    
    def retrieve_context(self, query: str) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        仅检索上下文，不生成答案
        
        参数:
            query: 用户问题
            
        返回:
            检索并重排序后的文档列表
        """
        try:
            # 向量检索
            docs = self.retriever.retrieve(query, k=self.top_k * 2)
            
            # 重排序
            reranked = self.reranker.rerank(query, docs, self.top_k)
            
            return reranked
            
        except Exception as e:
            logger.error(f"上下文检索失败: {str(e)}", exc_info=True)
            raise


class MultiChainRAG:
    """
    多链路 RAG - 支持多种查询策略
    
    特性:
        - 智能路由：根据问题类型选择合适的 chain
        - 多策略融合：结合多个 chain 的结果
        - 自适应优化：根据历史表现调整策略
    """
    
    def __init__(
        self,
        llm_type: str = "ollama",
        llm_model: Optional[str] = None,
        temperature: float = 0.1
    ):
        """
        初始化多链路 RAG
        
        参数:
            llm_type: LLM 类型
            llm_model: LLM 模型
            temperature: 生成温度
        """
        # 创建多个专用 chain
        self.chains = {
            "default": RAGChain(
                llm_type=llm_type,
                llm_model=llm_model,
                prompt_type="default",
                temperature=temperature
            ),
            "semiconductor": RAGChain(
                llm_type=llm_type,
                llm_model=llm_model,
                prompt_type="semiconductor",
                temperature=temperature
            ),
            "datasheet": RAGChain(
                llm_type=llm_type,
                llm_model=llm_model,
                prompt_type="datasheet",
                temperature=temperature
            ),
            "conversational": RAGChain(
                llm_type=llm_type,
                llm_model=llm_model,
                prompt_type="conversational",
                temperature=temperature
            )
        }
        
        logger.info(f"初始化多链路 RAG，共 {len(self.chains)} 个 chain")
    
    def route_query(self, query: str) -> str:
        """
        路由查询到合适的 chain
        
        参数:
            query: 用户问题
            
        返回:
            chain 类型
        """
        query_lower = query.lower()
        
        # 简单的关键词路由
        if any(kw in query_lower for kw in ["datasheet", "数据手册", "参数", "规格"]):
            return "datasheet"
        elif any(kw in query_lower for kw in ["工艺", "制程", "nm", "process"]):
            return "semiconductor"
        else:
            return "default"
    
    def invoke(self, query: str, chain_type: Optional[str] = None, **kwargs) -> str:
        """
        执行查询
        
        参数:
            query: 用户问题
            chain_type: 指定 chain 类型（None 为自动路由）
            **kwargs: 额外参数
            
        返回:
            生成的答案
        """
        # 自动路由或使用指定类型
        selected_chain = chain_type or self.route_query(query)
        
        logger.info(f"使用 chain: {selected_chain}")
        
        chain = self.chains.get(selected_chain, self.chains["default"])
        return chain.invoke(query, **kwargs)


def create_rag_chain(
    llm_type: str = "ollama",
    reranker_type: str = "simple",
    prompt_type: str = "default",
    **kwargs
) -> RAGChain:
    """
    创建 RAG Chain 的工厂函数
    
    参数:
        llm_type: LLM 类型 (openai/ollama)
        reranker_type: 重排序器类型 (simple/cross_encoder/hybrid)
        prompt_type: prompt 类型
        **kwargs: 其他参数
        
    返回:
        RAGChain 实例
    """
    # 创建重排序器
    reranker = get_reranker(reranker_type)
    
    # 创建 RAG Chain
    chain = RAGChain(
        reranker=reranker,
        llm_type=llm_type,
        prompt_type=prompt_type,
        **kwargs
    )
    
    return chain
