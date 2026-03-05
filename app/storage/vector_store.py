"""向量存储接口。"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union


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

    def get_by_ids(
        self,
        ids: List[str],
        return_data: bool = False,
        return_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        根据向量 ID (key) 从云端存储精确检索向量数据

        参数:
            ids: 向量 key 列表
            return_data: 是否返回向量数据 (float32 数组)
            return_metadata: 是否返回元数据

        返回:
            List[Dict]: 每个元素包含 key / data / metadata 等字段
        """
        raise NotImplementedError("当前向量存储后端不支持 get_by_ids")

    def list_vectors(
        self,
        max_results: int = 100,
        next_token: Optional[str] = None,
        return_data: bool = False,
        return_metadata: bool = True
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        分页列举云端向量数据

        参数:
            max_results: 单页最大数量 (1-1000)
            next_token: 分页令牌
            return_data: 是否返回向量数据
            return_metadata: 是否返回元数据

        返回:
            Tuple[List[Dict], Optional[str]]: (向量列表, 下一页token)
        """
        raise NotImplementedError("当前向量存储后端不支持 list_vectors")
