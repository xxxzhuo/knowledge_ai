"""
半导体行业定制分块器

特针对半导体工业文档（芯片规格、工艺标准等）的优化分块策略。
保留重要的上下文信息，如规格数据、设计参数等。
"""

import logging
import re
from typing import List, Dict, Any, Optional
from .base import BaseChunker, Chunk, ChunkType

logger = logging.getLogger(__name__)


class SemiconductorTextSplitter(BaseChunker):
    """
    半导体行业定制文本分块器
    
    特点：
        - 识别规格参数、技术指标等重要数据
        - 保留设计参数的上下文
        - 智能处理数值单位和技术术语
        - 优化半导体文档的分块效果
    
    示例:
        splitter = SemiconductorTextSplitter(
            chunk_size=1024,
            chunk_overlap=200,
        )
        chunks = splitter.chunk(text)
    """

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
        preserve_sections: bool = True,
        min_chunk_size: int = 100,
    ):
        """
        初始化半导体分块器
        
        参数:
            chunk_size: 目标分块大小（字符数）
            chunk_overlap: 分块重叠大小
            preserve_sections: 是否保留逻辑章节边界
            min_chunk_size: 最小分块大小（过小的分块会被删除）
        """
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator="\n\n",
        )
        self.preserve_sections = preserve_sections
        self.min_chunk_size = min_chunk_size

        # 半导体相关的关键词和模式
        self.tech_keywords = [
            "芯片", "晶体管", "工艺", "制造", "设计",
            "规格", "参数", "指标", "性能", "功率",
            "时序", "时钟", "频率", "电压", "电流",
            "驱动", "阻抗", "延迟", "抖动", "噪声",
        ]

        self.section_patterns = [
            r"^#+\s+", # 标题
            r"^第[一二三四五六七八九十百千]+[章节]",
            r"^\d+\.\s+", # 编号列表
        ]

    def chunk(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
    ) -> List[Chunk]:
        """
        将文本分块
        
        参数:
            text: 要分块的文本
            metadata: 文本元数据（页码、来源等）
            
        返回:
            List[Chunk]: 分块列表
        """
        if not text or not text.strip():
            logger.warning("输入文本为空")
            return []

        # 预处理文本
        text = self._preprocess_text(text)

        # 识别逻辑章节
        sections = self._identify_sections(text) if self.preserve_sections else None

        # 分块处理
        if sections:
            chunks = self._chunk_by_sections(text, sections, metadata)
        else:
            chunks = self._chunk_by_size(text, metadata)

        # 过滤过小的分块
        chunks = [c for c in chunks if len(c.content) >= self.min_chunk_size]

        logger.info(f"文本分块完成：共 {len(chunks)} 个分块")
        return chunks

    def _preprocess_text(self, text: str) -> str:
        """
        预处理文本
        
        - 清理多余空白
        - 统一行尾符号
        - 保留重要的格式
        
        参数:
            text: 原始文本
            
        返回:
            str: 预处理后的文本
        """
        # 统一行尾
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 移除多于空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 修复被破坏的单位和数值
        text = re.sub(r'(\d+)\s+(GHz|MHz|kHz|ms|us|ns|V|A|W|Ω)', r'\1\2', text)

        return text.strip()

    def _identify_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        识别文本中的逻辑章节
        
        参数:
            text: 文本内容
            
        返回:
            List[Dict]: 章节信息列表，包含起始位置和标题
        """
        sections = []

        lines = text.split('\n')
        current_pos = 0

        for line in lines:
            # 检查是否为章节标题
            for pattern in self.section_patterns:
                if re.match(pattern, line):
                    sections.append({
                        'title': line.strip(),
                        'start': current_pos,
                        'level': self._get_section_level(line),
                    })
                    break

            current_pos += len(line) + 1  # +1 为换行符

        # 添加结束位置
        for i in range(len(sections) - 1):
            sections[i]['end'] = sections[i + 1]['start']

        if sections:
            sections[-1]['end'] = len(text)

        return sections

    def _get_section_level(self, line: str) -> int:
        """
        获取章节级别
        
        参数:
            line: 章节标题行
            
        返回:
            int: 章节级别
        """
        if line.startswith('#'):
            return len(re.match(r'^#+', line).group())
        return 0

    def _chunk_by_sections(
        self,
        text: str,
        sections: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None,
    ) -> List[Chunk]:
        """
        按章节分块
        
        参数:
            text: 文本内容
            sections: 章节列表
            metadata: 元数据
            
        返回:
            List[Chunk]: 分块列表
        """
        chunks = []
        chunk_index = 0

        for section in sections:
            section_text = text[section['start']:section['end']].strip()

            if len(section_text) <= self.chunk_size:
                # 小于块大小，直接创建分块
                chunk = Chunk(
                    content=section_text,
                    chunk_index=chunk_index,
                    chunk_type=self._identify_chunk_type(section_text),
                    metadata=self._extract_metadata(section_text, metadata),
                )
                chunks.append(chunk)
                chunk_index += 1
            else:
                # 大于块大小，进一步分割
                sub_chunks = self._chunk_by_size(
                    section_text,
                    metadata,
                    start_index=chunk_index,
                )
                chunks.extend(sub_chunks)
                chunk_index += len(sub_chunks)

        return chunks

    def _chunk_by_size(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        start_index: int = 0,
    ) -> List[Chunk]:
        """
        按大小分块
        
        使用滑动窗口方法，同时保留重要的句子边界。
        
        参数:
            text: 文本内容
            metadata: 元数据
            start_index: 起始索引
            
        返回:
            List[Chunk]: 分块列表
        """
        chunks = []
        text = text.strip()

        if len(text) <= self.chunk_size:
            return [Chunk(
                content=text,
                chunk_index=start_index,
                chunk_type=self._identify_chunk_type(text),
                metadata=self._extract_metadata(text, metadata),
            )]

        # 添加起始位置信息到元数据
        if metadata is None:
            metadata = {}

        chunk_index = start_index
        start_pos = 0

        while start_pos < len(text):
            # 计算当前块的结束位置
            end_pos = start_pos + self.chunk_size

            if end_pos >= len(text):
                # 最后一个分块
                chunk_text = text[start_pos:].strip()
            else:
                # 查找最近的句子边界（。！？或者换行）
                end_pos = self._find_sentence_boundary(text, end_pos)
                chunk_text = text[start_pos:end_pos].strip()

            if chunk_text:
                chunk = Chunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    chunk_type=self._identify_chunk_type(chunk_text),
                    start_char=start_pos,
                    end_char=end_pos,
                    metadata=self._extract_metadata(chunk_text, metadata),
                )
                chunks.append(chunk)
                chunk_index += 1

                # 移动到下一个块（考虑重叠）
                start_pos = end_pos - self.chunk_overlap

            else:
                break

        return chunks

    def _find_sentence_boundary(self, text: str, pos: int) -> int:
        """
        在给定位置附近找到最近的句子边界
        
        参数:
            text: 文本
            pos: 目标位置
            
        返回:
            int: 句子边界位置
        """
        # 搜索范围：±10% 的块大小
        search_range = self.chunk_size // 10
        start = max(0, pos - search_range)
        end = min(len(text), pos + search_range)

        # 优先级：句子结尾 > 段落结尾 > 行尾
        for boundary_char in ['。', '！', '？', '.\n', '\n\n']:
            idx = text.rfind(boundary_char, start, end)
            if idx != -1:
                return idx + len(boundary_char)

        # 如果没找到，返回最近的空白符位置
        for i in range(end - 1, start - 1, -1):
            if text[i].isspace():
                return i

        # 如果都没有，返回目标位置
        return pos

    def _identify_chunk_type(self, text: str) -> ChunkType:
        """
        识别分块类型（包含半导体特定逻辑）
        
        参数:
            text: 分块文本
            
        返回:
            ChunkType: 分块类型
        """
        # 检查是否包含技术关键词（多数为技术内容）
        tech_keyword_count = sum(
            1 for keyword in self.tech_keywords
            if keyword in text
        )

        if tech_keyword_count > 2:
            return ChunkType.SECTION  # 技术规范部分

        # 其他情况下使用基类的识别逻辑
        return super()._identify_chunk_type(text)
