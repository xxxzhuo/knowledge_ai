"""
表格感知分块器模块

智能识别和处理文本中的表格，保持表格的完整性和结构。
将表格和普通文本分别处理，优化了对结构化信息的保留。
"""

import logging
import re
from typing import List, Dict, Any, Tuple
from .base import BaseChunker, Chunk, ChunkType

logger = logging.getLogger(__name__)


class TableAwareChunker(BaseChunker):
    """
    表格感知分块器
    
    特点：
        - 识别 Markdown 表格、HTML表格、固定宽度表格
        - 保持表格的完整性（不在中间分割表格）
        - 单独处理表格内容
        - 保留表格与周围文本的关系
    
    支持的表格格式：
        - Markdown 表格 (|...|...|)
        - HTML 表格 (<table>...</table>)
        - 纯文本表格
    """

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
        preserve_tables: bool = True,
        min_table_rows: int = 2,
    ):
        """
        初始化表格感知分块器
        
        参数:
            chunk_size: 目标分块大小
            chunk_overlap: 分块重叠大小
            preserve_tables: 是否完整保留表格
            min_table_rows: 最小表格行数（用于识别表格）
        """
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator="\n\n",
        )
        self.preserve_tables = preserve_tables
        self.min_table_rows = min_table_rows

    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
    ) -> List[Chunk]:
        """
        分块处理，特别处理表格
        
        参数:
            text: 文本内容
            metadata: 元数据
            
        返回:
            List[Chunk]: 分块列表
        """
        if not text or not text.strip():
            logger.warning("输入文本为空")
            return []

        # 识别和分离表格
        segments = self._identify_table_segments(text)

        chunks = []
        chunk_index = 0

        for segment in segments:
            if segment['type'] == 'table':
                # 表格直接作为一个分块
                chunk = Chunk(
                    content=segment['content'],
                    chunk_index=chunk_index,
                    chunk_type=ChunkType.TABLE,
                    metadata=self._extract_metadata(
                        segment['content'],
                        {
                            **(metadata or {}),
                            'is_table': True,
                            'table_type': segment.get('table_type'),
                        }
                    ),
                )
                chunks.append(chunk)
                chunk_index += 1

            else:
                # 普通文本按大小分块
                segment_text = segment['content'].strip()
                if segment_text:
                    text_chunks = self._chunk_text(
                        segment_text,
                        metadata,
                        chunk_index,
                    )
                    chunks.extend(text_chunks)
                    chunk_index += len(text_chunks)

        logger.info(f"分块完成：共 {len(chunks)} 个分块")
        return chunks

    def _identify_table_segments(self, text: str) -> List[Dict[str, Any]]:
        """
        识别文本中的表格段落和普通文本段落
        
        参数:
            text: 文本内容
            
        返回:
            List[Dict]: 段落列表，包含类型和内容
        """
        segments = []
        remaining_text = text
        current_pos = 0

        # 识别 Markdown 表格
        markdown_pattern = r'\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n)*'
        html_pattern = r'<table[^>]*>.*?</table>'

        while remaining_text:
            # 尝试匹配 Markdown 表格
            match = re.search(markdown_pattern, remaining_text, re.IGNORECASE | re.DOTALL)

            if not match:
                # 尝试匹配 HTML 表格
                match = re.search(html_pattern, remaining_text, re.IGNORECASE | re.DOTALL)
                table_type = 'html' if match else None
            else:
                table_type = 'markdown'

            if match:
                # 添加表格前的文本
                if match.start() > 0:
                    pre_text = remaining_text[:match.start()].strip()
                    if pre_text:
                        segments.append({
                            'type': 'text',
                            'content': pre_text,
                        })

                # 添加表格
                table_text = match.group()
                segments.append({
                    'type': 'table',
                    'content': table_text,
                    'table_type': table_type,
                })

                # 继续处理剩余文本
                remaining_text = remaining_text[match.end():]
                current_pos += match.end()

            else:
                # 没有更多表格
                if remaining_text.strip():
                    segments.append({
                        'type': 'text',
                        'content': remaining_text.strip(),
                    })
                break

        return segments

    def _chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        start_index: int = 0,
    ) -> List[Chunk]:
        """
        分块处理文本
        
        参数:
            text: 文本内容
            metadata: 元数据
            start_index: 起始索引
            
        返回:
            List[Chunk]: 分块列表
        """
        chunks = []

        if len(text) <= self.chunk_size:
            return [Chunk(
                content=text,
                chunk_index=start_index,
                chunk_type=self._identify_chunk_type(text),
                metadata=self._extract_metadata(text, metadata),
            )]

        # 按句子或段落分块
        segments = self._split_into_segments(text)
        current_chunk = ""
        chunk_index = start_index

        for segment in segments:
            if len(current_chunk) + len(segment) <= self.chunk_size:
                current_chunk += segment
            else:
                # 保存当前分块
                if current_chunk.strip():
                    chunk = Chunk(
                        content=current_chunk.strip(),
                        chunk_index=chunk_index,
                        chunk_type=self._identify_chunk_type(current_chunk),
                        metadata=self._extract_metadata(current_chunk, metadata),
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                # 开始新的分块（考虑重叠）
                current_chunk = segment[-self.chunk_overlap:] if len(segment) > self.chunk_overlap else segment

        # 处理最后一个分块
        if current_chunk.strip():
            chunk = Chunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                chunk_type=self._identify_chunk_type(current_chunk),
                metadata=self._extract_metadata(current_chunk, metadata),
            )
            chunks.append(chunk)

        return chunks

    def _split_into_segments(self, text: str) -> List[str]:
        """
        将文本分割成段落或句子
        
        参数:
            text: 文本内容
            
        返回:
            List[str]: 分割后的段落列表
        """
        # 首先按段落分割（双换行）
        paragraphs = text.split('\n\n')

        segments = []
        for para in paragraphs:
            if len(para) > self.chunk_size:
                # 段落过长，按句子分割
                sentences = self._split_sentences(para)
                segments.extend(sentences)
            else:
                # 段落可接受
                segments.append(para + '\n\n')

        return segments

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """
        将文本分割成句子
        
        参数:
            text: 文本内容
            
        返回:
            List[str]: 句子列表
        """
        # 使用中文句号、英文句号等作为句子分隔符
        sentences = re.split(r'([。！？.!?\n])', text)

        result = []
        for i in range(0, len(sentences), 2):
            if i < len(sentences) - 1:
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]

            if sentence.strip():
                result.append(sentence)

        return result

    def extract_tables(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取所有表格
        
        参数:
            text: 文本内容
            
        返回:
            List[Dict]: 表格列表
        """
        segments = self._identify_table_segments(text)
        tables = [s for s in segments if s['type'] == 'table']

        for idx, table in enumerate(tables):
            table['table_id'] = idx
            table['content_preview'] = table['content'][:200] + '...'

        return tables

    def merge_small_chunks(
        self,
        chunks: List[Chunk],
        min_size: int = 50,
    ) -> List[Chunk]:
        """
        合并过小的分块
        
        参数:
            chunks: 分块列表
            min_size: 最小分块大小
            
        返回:
            List[Chunk]: 合并后的分块列表
        """
        merged = []
        buffer = None

        for chunk in chunks:
            if len(chunk.content) < min_size:
                # 当前分块过小，保存到缓冲区
                if buffer is None:
                    buffer = chunk
                else:
                    # 合并两个分块
                    buffer.content += '\n\n' + chunk.content
                    buffer.chunk_type = ChunkType.MIXED

            else:
                # 当前分块足够大
                if buffer:
                    # 先合并缓冲区的分块
                    buffer.content += '\n\n' + chunk.content
                    merged.append(buffer)
                    buffer = None
                else:
                    merged.append(chunk)

        # 处理剩余的缓冲区
        if buffer:
            merged.append(buffer)

        # 重新编号
        for idx, chunk in enumerate(merged):
            chunk.chunk_index = idx

        return merged
