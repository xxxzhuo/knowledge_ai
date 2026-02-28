"""
PDF文档加载器模块

使用 PyPDF 库提取PDF文档中的文本内容、元数据和页面信息。
支持多页PDF文档的完整处理，包括页面级别的内容分离。
"""

import logging
from typing import List, Dict, Any
from pypdf import PdfReader
from pathlib import Path

from .base import BaseDocumentLoader, LoadedDocument, DocumentType

logger = logging.getLogger(__name__)


class PDFLoader(BaseDocumentLoader):
    """
    PDF文档加载器
    
    使用PyPDF库加载PDF文件，提取文本、页面信息和元数据。
    支持:
        - 多页PDF处理
        - 页面级别的内容分离
        - PDF元数据提取
        - 页面顺序保留
    """

    def __init__(self, file_path: str, extract_metadata: bool = True):
        """
        初始化PDF加载器
        
        参数:
            file_path: PDF文件路径
            extract_metadata: 是否提取PDF元数据 (默认: True)
        """
        super().__init__(file_path)
        self.extract_metadata = extract_metadata
        self._validate_pdf()

    def _validate_pdf(self) -> None:
        """
        验证文件是否为有效的PDF文件
        
        抛出:
            ValueError: 如果文件不是有效的PDF
        """
        if self.file_path.suffix.lower() != ".pdf":
            raise ValueError(f"文件必须是PDF格式: {self.file_path}")

    def load(self) -> LoadedDocument:
        """
        加载PDF文档并提取内容
        
        返回:
            LoadedDocument: 包含PDF内容的文档对象
            
        抛出:
            Exception: 如果PDF处理失败
        """
        try:
            reader = PdfReader(str(self.file_path))
            page_count = len(reader.pages)

            # 提取所有页面的文本
            full_content = self._extract_text_from_pages(reader)

            # 提取PDF元数据
            metadata = self._extract_pdf_metadata(reader)

            logger.info(f"成功加载PDF文件: {self.file_name}, 页数: {page_count}")

            return LoadedDocument(
                content=full_content,
                document_type=DocumentType.PDF,
                file_path=self.file_path,
                file_name=self.file_name,
                page_count=page_count,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"加载PDF文件失败: {self.file_name}, 错误: {str(e)}")
            raise

    def _extract_text_from_pages(self, reader: PdfReader) -> str:
        """
        从PDF的所有页面提取文本
        
        参数:
            reader: PdfReader实例
            
        返回:
            str: 所有页面的文本内容（使用分页符分隔）
        """
        pages_content = []

        for page_num, page in enumerate(reader.pages, 1):
            try:
                page_text = page.extract_text()
                # 添加页面标记
                page_text = f"[页面 {page_num}]\n{page_text}"
                pages_content.append(page_text)
            except Exception as e:
                logger.warning(f"页面 {page_num} 文本提取失败: {str(e)}")
                pages_content.append(f"[页面 {page_num}]\n[提取失败]")

        # 使用分页符连接所有页面
        return "\n\n---\n\n".join(pages_content)

    def _extract_pdf_metadata(self, reader: PdfReader) -> Dict[str, Any]:
        """
        提取PDF文件的元数据
        
        参数:
            reader: PdfReader实例
            
        返回:
            Dict: 包含PDF元数据的字典
        """
        metadata = self._extract_metadata()

        # 提取PDF特定的元数据
        pdf_info = reader.metadata
        if pdf_info:
            metadata.update({
                "author": pdf_info.get("/Author", ""),
                "creator": pdf_info.get("/Creator", ""),
                "producer": pdf_info.get("/Producer", ""),
                "subject": pdf_info.get("/Subject", ""),
                "title": pdf_info.get("/Title", ""),
                "creation_date": str(pdf_info.get("/CreationDate", "")),
            })

        return metadata

    def get_pages_content(self) -> List[Dict[str, Any]]:
        """
        获取PDF各页面的内容和页码信息
        
        这在需要对不同页面进行差异化处理时很有用。
        
        返回:
            List[Dict]: 页面内容列表，每个元素包含页号和内容
        """
        try:
            reader = PdfReader(str(self.file_path))
            pages_data = []

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    page_text = page.extract_text()
                    pages_data.append({
                        "page_number": page_num,
                        "content": page_text,
                        "char_count": len(page_text),
                    })
                except Exception as e:
                    logger.warning(f"页面 {page_num} 处理失败: {str(e)}")
                    pages_data.append({
                        "page_number": page_num,
                        "content": "",
                        "error": str(e),
                    })

            return pages_data

        except Exception as e:
            logger.error(f"获取页面内容失败: {str(e)}")
            raise
