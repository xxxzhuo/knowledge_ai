"""
文本分块基类和接口定义模块

本模块定义了所有文本分块器必须实现的基类和接口，
确保不同分块策略能够统一地被处理和管理。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class ChunkType(str, Enum):
    """分块类型枚举"""
    PARAGRAPH = "paragraph"  # 段落
    SENTENCE = "sentence"    # 句子
    SECTION = "section"      # 部分
    TABLE = "table"          # 表格
    CODE = "code"            # 代码
    LIST = "list"            # 列表
    MIXED = "mixed"          # 混合


@dataclass
class Chunk:
    """
    文本分块数据结构
    
    属性:
        content: 分块文本内容
        chunk_index: 分块在文档中的序号
        chunk_type: 分块类型
        page_start: 起始页码
        page_end: 结束页码
        start_char: 在原文本中的起始字符位置
        end_char: 在原文本中的结束字符位置
        token_count: 分块的token数量（用于成本计算）
        metadata: 分块元数据
    """
    content: str
    chunk_index: int
    chunk_type: ChunkType
    page_start: int = 1
    page_end: int = 1
    start_char: int = 0
    end_char: int = 0
    token_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """初始化默认值"""
        if self.metadata is None:
            self.metadata = {}
        if self.token_count == 0:
            # 简单估计 token 数（中文平均3字1token）
            self.token_count = len(self.content) // 3 + len(self.content.split())


class BaseChunker(ABC):
    """
    文本分块器基类
    
    所有文本分块器都必须继承此基类并实现 chunk() 方法。
    这确保了所有分块器有一致的接口。
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separator: str = "\n",
    ):
        """
        初始化分块器
        
        参数:
            chunk_size: 目标分块大小（字符数）
            chunk_overlap: 分块之间的重叠大小（字符数）
            separator: 分块分隔符
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")

    @abstractmethod
    def chunk(self, text: str, metadata: Dict[str, Any] = None) -> List[Chunk]:
        """
        将文本分块
        
        必须在子类中实现此方法。
        
        参数:
            text: 要分块的文本
            metadata: 文本元数据（页码、来源等）
            
        返回:
            List[Chunk]: 分块列表
            
        抛出:
            NotImplementedError: 如果子类未实现此方法
        """
        raise NotImplementedError("子类必须实现 chunk() 方法")

    def _estimate_tokens(self, text: str) -> int:
        """
        估计文本的token数量
        
        使用简单的启发式方法：
        - 英文：每4个字符约1个token
        - 中文：每3个字符约1个token
        
        参数:
            text: 文本内容
            
        返回:
            int: 估计的token数量
        """
        # 简单的token计数估计
        # 中文：每3字符算1个token
        # 英文：每4字符+单词数算token
        char_count = len(text)
        word_count = len(text.split())

        # 粗略估计
        token_count = (char_count // 3) + (word_count // 4)
        return max(token_count, 1)

    def _extract_metadata(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        合并和提取分块元数据
        
        参数:
            text: 分块文本
            metadata: 原始元数据
            
        返回:
            Dict: 分块元数据
        """
        merged_metadata = metadata.copy() if metadata else {}

        # 添加分块级别的统计信息
        merged_metadata.update({
            "char_count": len(text),
            "word_count": len(text.split()),
            "line_count": len(text.split('\n')),
        })

        return merged_metadata

    @staticmethod
    def _split_text_simple(
        text: str,
        chunk_size: int,
        overlap: int = 0,
    ) -> List[str]:
        """
        使用简单分割策略分块文本
        
        参数:
            text: 输入文本
            chunk_size: 分块大小
            overlap: 重叠大小
            
        返回:
            List[str]: 分块列表
        """
        chunks = []
        step = chunk_size - overlap

        for i in range(0, len(text), step):
            chunk = text[i : i + chunk_size]
            if chunk:
                chunks.append(chunk)

        return chunks

    @staticmethod
    def _identify_chunk_type(text: str) -> ChunkType:
        """
        识别分块的类型
        
        参数:
            text: 分块文本
            
        返回:
            ChunkType: 分块类型
        """
        # 表格特征
        if '|' in text and '---' in text:
            return ChunkType.TABLE

        # 代码特征
        if '```' in text or 'def ' in text or 'function' in text:
            return ChunkType.CODE

        # 列表特征
        if text.strip().startswith(('- ', '* ', '• ', '1. ', '2. ')):
            return ChunkType.LIST

        # 判断是否为单个句子或段落
        sentence_count = len(text.split('。')) + len(text.split('!')) + len(text.split('?'))
        if sentence_count == 1:
            return ChunkType.SENTENCE

        # 默认为段落或混合
        return ChunkType.PARAGRAPH if '\n' not in text else ChunkType.MIXED
