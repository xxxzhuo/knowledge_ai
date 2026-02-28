"""Embedding 服务基类接口。"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class EmbeddingService(ABC):
    """
    Embedding 服务的基类接口
    
    所有 Embedding 服务实现都必须继承此基类并实现相应方法。
    """

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """
        对单个文本进行向量化
        
        参数:
            text: 要向量化的文本
            
        返回:
            List[float]: 文本的向量表示
        """
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        对多个文本进行批量向量化
        
        参数:
            texts: 要向量化的文本列表
            
        返回:
            List[List[float]]: 文本列表的向量表示
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        获取 Embedding 向量的维度
        
        返回:
            int: 向量维度
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        获取使用的 Embedding 模型名称
        
        返回:
            str: 模型名称
        """
        pass
