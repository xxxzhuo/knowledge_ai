"""基于 OpenAI API 的 Embedding 服务实现。"""

import logging
from typing import List, Optional
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.embeddings.base import EmbeddingService
from app.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIEmbeddingService(EmbeddingService):
    """
    基于 OpenAI API 的 Embedding 服务实现
    """

    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None):
        """
        初始化 OpenAI Embedding 服务
        
        参数:
            model_name: Embedding 模型名称
            api_key: OpenAI API 密钥
        """
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self.api_key = api_key or settings.openai_api_key
        self.embedding_dimension = settings.vector_dimension
        
        # 配置 OpenAI 客户端
        openai.api_key = self.api_key
        
        logger.info(f"初始化 OpenAI Embedding 服务，模型: {self.model_name}")

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
            List[float]: 文本的向量表示
        """
        try:
            response = openai.embeddings.create(
                input=text,
                model=self.model_name
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI Embedding 失败: {str(e)}")
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
            List[List[float]]: 文本列表的向量表示
        """
        try:
            settings = get_settings()
            batch_size = settings.embedding_batch_size
            
            # 分批处理
            embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = openai.embeddings.create(
                    input=batch,
                    model=self.model_name
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            return embeddings
        except Exception as e:
            logger.error(f"OpenAI Embedding 批量处理失败: {str(e)}")
            raise

    def get_dimension(self) -> int:
        """
        获取 Embedding 向量的维度
        
        返回:
            int: 向量维度
        """
        return self.embedding_dimension

    def get_model_name(self) -> str:
        """
        获取使用的 Embedding 模型名称
        
        返回:
            str: 模型名称
        """
        return self.model_name
