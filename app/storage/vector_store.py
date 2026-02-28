"""向量存储接口。"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple


class VectorStore(ABC):
    """
    向量存储的基类接口
    
    所有向量存储实现都必须继承此基类并实现相应方法。
    """

    @abstractmethod
    def add_embeddings(
        self,
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        添加向量到存储
        
        参数:
            embeddings: 向量列表
            texts: 文本列表
            metadatas: 元数据列表
            
        返回:
            List[str]: 插入的向量 ID 列表
        """
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[float, str, Dict[str, Any]]]:
        """
        搜索相似向量
        
        参数:
            query_embedding: 查询向量
            k: 返回的结果数量
            filter: 过滤条件
            
        返回:
            List[Tuple[float, str, Dict[str, Any]]]: (相似度, 文本, 元数据) 的列表
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> bool:
        """
        删除向量
        
        参数:
            ids: 要删除的向量 ID 列表
            
        返回:
            bool: 是否删除成功
        """
        pass

    @abstractmethod
    def clear(self) -> bool:
        """
        清空所有向量
        
        返回:
            bool: 是否清空成功
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        获取向量数量
        
        返回:
            int: 向量数量
        """
        pass
