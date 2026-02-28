"""
文档加载器基类和接口定义模块

本模块定义了所有文档加载器必须实现的基类和接口，
确保不同格式的文档能够统一地被处理和管理。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
from enum import Enum


class DocumentType(str, Enum):
    """文档类型枚举"""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    IMAGE = "image"
    TABLE = "table"


@dataclass
class LoadedDocument:
    """
    加载后的文档数据结构
    
    属性:
        content: 文档内容文本
        document_type: 文档类型
        file_path: 文件路径
        file_name: 文件名
        page_count: 页数（PDF类文档）
        metadata: 元数据字典
        tables: 提取的表格列表
        images: 提取的图片列表
    """
    content: str
    document_type: DocumentType
    file_path: Path
    file_name: str
    page_count: int = 1
    metadata: Dict[str, Any] = None
    tables: List[Dict[str, Any]] = None
    images: List[Dict[str, Any]] = None

    def __post_init__(self):
        """初始化默认值"""
        if self.metadata is None:
            self.metadata = {}
        if self.tables is None:
            self.tables = []
        if self.images is None:
            self.images = []


class BaseDocumentLoader(ABC):
    """
    文档加载器基类
    
    所有文档加载器都必须继承此基类并实现 load() 方法。
    这确保了所有加载器有一致的接口。
    """

    def __init__(self, file_path: str):
        """
        初始化文档加载器
        
        参数:
            file_path: 文档文件路径
        """
        self.file_path = Path(file_path)
        self.file_name = self.file_path.name
        self._validate_file_exists()

    def _validate_file_exists(self) -> None:
        """验证文件是否存在"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"文件不存在: {self.file_path}")

    @abstractmethod
    def load(self) -> LoadedDocument:
        """
        加载文档
        
        必须在子类中实现此方法。
        
        返回:
            LoadedDocument: 包含加载内容的文档对象
            
        抛出:
            NotImplementedError: 如果子类未实现此方法
        """
        raise NotImplementedError("子类必须实现 load() 方法")

    def _extract_metadata(self) -> Dict[str, Any]:
        """
        提取文件元数据
        
        返回:
            Dict: 包含文件元数据的字典
        """
        return {
            "file_size": self.file_path.stat().st_size,
            "file_path": str(self.file_path),
            "file_name": self.file_name,
            "created_at": self.file_path.stat().st_ctime,
            "modified_at": self.file_path.stat().st_mtime,
        }
