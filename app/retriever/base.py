"""检索器基类接口。"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple


class Retriever(ABC):
    """
    检索器的基类接口
    
    所有检索器实现都必须继承此基类并实现相应方法。
    """

    @abstractmethod
    def retrieve(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        根据查询文本检索相关文档
        
        参数:
            query: 查询文本
            k: 返回的结果数量
            filter: 过滤条件
            
        返回:
            List[Tuple[float, str, Dict[str, Any]]]: (相似度, 文本, 元数据) 的列表
        """
        pass

    @abstractmethod
    def retrieve_with_embedding(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        根据查询向量检索相关文档
        
        参数:
            query_embedding: 查询向量
            k: 返回的结果数量
            filter: 过滤条件
            
        返回:
            List[Tuple[float, str, Dict[str, Any]]]: (相似度, 文本, 元数据) 的列表
        """
        pass
