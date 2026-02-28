"""基于 Ollama 本地模型的 Embedding 服务实现。"""

import logging
from typing import List, Optional
import ollama
from tenacity import retry, stop_after_attempt, wait_exponential

from app.embeddings.base import EmbeddingService
from app.config import get_settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingService(EmbeddingService):
    """
    基于 Ollama 本地模型的 Embedding 服务实现
    
    使用 Ollama 提供的本地 embedding 模型（如 embeddinggemma）进行文本向量化。
    返回的向量是 L2 归一化（单位长度）的向量。
    """

    def __init__(
        self, 
        model_name: Optional[str] = None,
        host: Optional[str] = None
    ):
        """
        初始化 Ollama Embedding 服务
        
        参数:
            model_name: Ollama embedding 模型名称（默认: embeddinggemma）
            host: Ollama 服务地址（默认: http://localhost:11434）
        """
        settings = get_settings()
        self.model_name = model_name or getattr(settings, 'ollama_embedding_model', 'embeddinggemma')
        self.host = host or getattr(settings, 'ollama_host', 'http://localhost:11434')
        
        # 缓存向量维度（第一次调用时获取）
        self._dimension = None
        
        logger.info(f"初始化 Ollama Embedding 服务，模型: {self.model_name}, 地址: {self.host}")

    def _get_embedding_dimension(self) -> int:
        """
        获取 embedding 向量维度
        
        通过执行一次实际的 embedding 操作来获取向量维度
        
        返回:
            int: 向量维度
        """
        if self._dimension is None:
            try:
                # 使用一个简单的文本来测试并获取维度
                test_response = ollama.embed(
                    model=self.model_name,
                    input='test'
                )
                self._dimension = len(test_response['embeddings'][0])
                logger.info(f"Ollama Embedding 向量维度: {self._dimension}")
            except Exception as e:
                logger.error(f"获取 Ollama Embedding 维度失败: {str(e)}")
                # 如果失败，返回默认维度（embeddinggemma 是 768）
                self._dimension = 768
        
        return self._dimension

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def embed_text(self, text: str) -> List[float]:
        """
        对单个文本进行向量化
        
        参数:
            text: 要向量化的文本
            
        返回:
            List[float]: 文本的向量表示（L2 归一化）
        """
        try:
            if not text or not text.strip():
                logger.warning("尝试向量化空文本，返回零向量")
                return [0.0] * self.get_dimension()
            
            response = ollama.embed(
                model=self.model_name,
                input=text
            )
            
            # Ollama 返回格式: {'embeddings': [[...]], ...}
            embedding = response['embeddings'][0]
            
            logger.debug(f"成功向量化文本，长度: {len(text)}, 向量维度: {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Ollama Embedding 失败: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        对多个文本进行批量向量化
        
        参数:
            texts: 要向量化的文本列表
            
        返回:
            List[List[float]]: 文本列表的向量表示（L2 归一化）
        """
        try:
            if not texts:
                logger.warning("尝试向量化空文本列表")
                return []
            
            # 过滤空文本
            filtered_texts = [text if text and text.strip() else " " for text in texts]
            
            # Ollama 支持批量处理
            response = ollama.embed(
                model=self.model_name,
                input=filtered_texts
            )
            
            # Ollama 返回格式: {'embeddings': [[...], [...], ...], ...}
            embeddings = response['embeddings']
            
            logger.info(f"成功批量向量化 {len(texts)} 个文本")
            return embeddings
            
        except Exception as e:
            logger.error(f"Ollama Embedding 批量处理失败: {str(e)}")
            raise

    def get_dimension(self) -> int:
        """
        获取 Embedding 向量的维度
        
        返回:
            int: 向量维度
        """
        return self._get_embedding_dimension()

    def get_model_name(self) -> str:
        """
        获取使用的 Embedding 模型名称
        
        返回:
            str: 模型名称
        """
        return self.model_name

    def health_check(self) -> bool:
        """
        检查 Ollama 服务是否可用
        
        返回:
            bool: 服务是否可用
        """
        try:
            # 尝试执行一个简单的 embedding 操作
            result = ollama.embed(
                model=self.model_name,
                input='health check'
            )
            return 'embeddings' in result and len(result['embeddings']) > 0
        except Exception as e:
            logger.error(f"Ollama 健康检查失败: {str(e)}")
            return False

    def __repr__(self) -> str:
        """字符串表示"""
        return f"OllamaEmbeddingService(model={self.model_name}, host={self.host})"
