"""
文档处理管道模块

整合文档加载器和分块器，提供完整的文档处理工作流。
从文件加载 → 提取内容 → 识别结构 → 分块处理 → 生成元数据
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

from app.loaders import (
    BaseDocumentLoader,
    PDFLoader,
    ImageLoader,
    TableExtractor,
    LoadedDocument,
    DocumentType,
)
from app.loaders.loaderall import PdfExtractor
from app.chunking import (
    Chunk,
    SemiconductorTextSplitter,
    TableAwareChunker,
)
from app.embeddings import get_embedding_service, EmbeddingService
from app.storage import MilvusStore

logger = logging.getLogger(__name__)


@dataclass
class ProcessedDocument:
    """
    处理后的文档对象
    
    属性:
        file_name: 文件名
        file_type: 文件类型
        total_chunks: 总分块数
        total_tokens: 总token数
        chunks: 分块列表
        tables: 表格列表
        images: 图片列表
        metadata: 文档元数据
    """
    file_name: str
    file_type: str
    total_chunks: int
    total_tokens: int
    chunks: List[Dict[str, Any]]
    tables: List[Dict[str, Any]] = None
    images: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """初始化默认值"""
        if self.tables is None:
            self.tables = []
        if self.images is None:
            self.images = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        返回:
            Dict: 字典表示
        """
        return asdict(self)


class DocumentProcessor:
    """
    文档处理管道
    
    流程：
        1. 加载文档 (使用相应的加载器)
        2. 提取内容 (文本、表格、图片)
        3. 识别文档结构
        4. 分块处理
        5. 生成元数据
    """

    def __init__(
        self,
        chunker_type: str = "semiconductor",
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
        enable_ocr: bool = False,
        extract_tables: bool = True,
        extract_images: bool = False,
        enable_embedding: bool = False,
    ):
        """
        初始化文档处理器
        
        参数:
            chunker_type: 分块器类型 ('semiconductor' 或 'table_aware')
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            enable_ocr: 是否启用图片OCR
            extract_tables: 是否提取表格
            extract_images: 是否提取图片
            enable_embedding: 是否启用向量化
        """
        self.chunker_type = chunker_type
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_ocr = enable_ocr
        self.extract_tables = extract_tables
        self.extract_images = extract_images
        self.enable_embedding = enable_embedding

        # 初始化分块器
        if chunker_type == "semiconductor":
            self.chunker = SemiconductorTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        else:
            self.chunker = TableAwareChunker(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                preserve_tables=extract_tables,
            )

        # 初始化表格提取器
        if extract_tables:
            self.table_extractor = TableExtractor()
        else:
            self.table_extractor = None

        # 初始化 Embedding 服务和向量存储
        if enable_embedding:
            self.embedding_service = get_embedding_service()
            self.vector_store = MilvusStore()
        else:
            self.embedding_service = None
            self.vector_store = None

    def process(self, file_path: str) -> ProcessedDocument:
        """
        处理文档
        
        参数:
            file_path: 文件路径
            
        返回:
            ProcessedDocument: 处理后的文档对象
            
        抛出:
            ValueError: 如果文件格式不支持
        """
        file_path = Path(file_path)

        # 第1步：加载文档
        logger.info(f"开始处理文档: {file_path.name}")
        loaded_doc = self._load_document(file_path)

        # 第2步：提取表格和图片
        tables = self._extract_tables(file_path) if self.extract_tables else []
        images = self._extract_images(file_path) if self.extract_images else []

        # 第3步：对内容进行分块
        metadata = self._prepare_metadata(loaded_doc)
        chunks = self.chunker.chunk(loaded_doc.content, metadata)

        # 第4步：计算统计信息
        total_tokens = sum(chunk.token_count for chunk in chunks)

        # 第5步：将分块转换为字典格式
        chunks_data = [self._chunk_to_dict(idx, chunk) for idx, chunk in enumerate(chunks)]

        # 第6步：向量化处理（如果启用）
        if self.enable_embedding and self.embedding_service and self.vector_store:
            logger.info(f"开始对 {len(chunks_data)} 个分块进行向量化")
            
            # 提取分块内容
            chunk_texts = [chunk['content'] for chunk in chunks_data]
            
            # 批量向量化
            embeddings = self.embedding_service.embed_documents(chunk_texts)
            
            # 准备元数据
            metadatas = []
            for i, chunk in enumerate(chunks_data):
                metadata = {
                    "file_name": loaded_doc.file_name,
                    "file_path": str(loaded_doc.file_path),
                    "chunk_index": chunk['chunk_index'],
                    "page_start": chunk['page_start'],
                    "page_end": chunk['page_end'],
                    "token_count": chunk['token_count'],
                    **chunk['metadata']
                }
                metadatas.append(metadata)
            
            # 存储向量
            vector_ids = self.vector_store.add_embeddings(embeddings, chunk_texts, metadatas)
            
            # 将向量 ID 添加到分块数据中
            for i, vector_id in enumerate(vector_ids):
                chunks_data[i]['vector_id'] = vector_id
            
            logger.info("向量化处理完成")

        logger.info(
            f"文档处理完成: {file_path.name} "
            f"({len(chunks_data)} 个分块, {total_tokens} 个tokens)"
        )

        return ProcessedDocument(
            file_name=loaded_doc.file_name,
            file_type=loaded_doc.document_type.value,
            total_chunks=len(chunks_data),
            total_tokens=total_tokens,
            chunks=chunks_data,
            tables=tables,
            images=images,
            metadata=metadata,
        )

    def _load_document(self, file_path: Path) -> LoadedDocument:
        """
        根据文件类型选择合适的加载器
        
        参数:
            file_path: 文件路径
            
        返回:
            LoadedDocument: 加载的文档
        """
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            # 使用 PdfExtractor 提取 PDF 内容
            extractor = PdfExtractor()
            # 提取资产（文本、图片、表格）
            assets = extractor.extract_assets(str(file_path))
            
            # 构建完整文本内容
            full_content = []
            for text_item in assets.get("text", {}).get("items", []):
                page_num = text_item.get("page")
                text_path = text_item.get("file")
                if text_path:
                    try:
                        with open(text_path, "r", encoding="utf-8") as f:
                            page_text = f.read()
                        full_content.append(f"[页面 {page_num}]\n{page_text}")
                    except Exception as e:
                        logger.warning(f"读取页面 {page_num} 文本失败: {str(e)}")
                        full_content.append(f"[页面 {page_num}]\n[提取失败]")
            
            # 提取元数据
            metadata = extractor.extract_metadata(doc_path=str(file_path)) or {}
            
            # 构建 LoadedDocument 对象
            return LoadedDocument(
                content="\n\n---\n\n".join(full_content),
                document_type=DocumentType.PDF,
                file_path=file_path,
                file_name=file_path.name,
                page_count=assets.get("page_count", 0),
                metadata=metadata,
            )
        elif suffix in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
            loader = ImageLoader(
                str(file_path),
                enable_ocr=self.enable_ocr,
            )
            return loader.load()
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")

    def _extract_tables(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        提取文档中的表格
        
        参数:
            file_path: 文件路径
            
        返回:
            List[Dict]: 表格列表
        """
        if file_path.suffix.lower() != ".pdf":
            return []

        try:
            # 使用 PdfExtractor 提取表格
            extractor = PdfExtractor()
            assets = extractor.extract_assets(str(file_path))
            
            # 转换表格格式以保持兼容性
            tables = []
            for table_item in assets.get("datasheet", {}).get("items", []):
                table = {
                    "page": table_item.get("page"),
                    "table_index": table_item.get("table_index"),
                    "rows": table_item.get("rows"),
                    "data": table_item.get("data"),
                    "csv_file": table_item.get("csv_file"),
                }
                tables.append(table)
            
            logger.info(f"提取到 {len(tables)} 个表格")
            return tables
        except Exception as e:
            logger.warning(f"表格提取失败: {str(e)}")
            return []

    def _extract_images(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        提取文档中的图片
        
        参数:
            file_path: 文件路径
            
        返回:
            List[Dict]: 图片列表
        """
        if file_path.suffix.lower() != ".pdf":
            return []

        try:
            # 使用 PdfExtractor 提取图片
            extractor = PdfExtractor()
            assets = extractor.extract_assets(str(file_path))
            
            # 转换图片格式以保持兼容性
            images = []
            for image_item in assets.get("images", {}).get("items", []):
                image = {
                    "page": image_item.get("page"),
                    "file": image_item.get("file"),
                }
                images.append(image)
            
            logger.info(f"提取到 {len(images)} 个图片")
            return images
        except Exception as e:
            logger.warning(f"图片提取失败: {str(e)}")
            return []

    def _prepare_metadata(self, loaded_doc: LoadedDocument) -> Dict[str, Any]:
        """
        准备分块的元数据
        
        参数:
            loaded_doc: 已加载的文档
            
        返回:
            Dict: 元数据
        """
        return {
            "file_name": loaded_doc.file_name,
            "file_path": str(loaded_doc.file_path),
            "file_type": loaded_doc.document_type.value,
            "page_count": loaded_doc.page_count,
            **loaded_doc.metadata,
        }

    @staticmethod
    def _chunk_to_dict(idx: int, chunk: Chunk) -> Dict[str, Any]:
        """
        将分块对象转换为字典格式
        
        参数:
            idx: 分块索引
            chunk: 分块对象
            
        返回:
            Dict: 分块字典
        """
        return {
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "chunk_type": chunk.chunk_type.value,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "token_count": chunk.token_count,
            "char_count": len(chunk.content),
            "metadata": chunk.metadata,
        }

    def batch_process(
        self,
        file_paths: List[str],
        continue_on_error: bool = True,
    ) -> List[ProcessedDocument]:
        """
        批量处理多个文档
        
        参数:
            file_paths: 文件路径列表
            continue_on_error: 出错时是否继续处理其他文件
            
        返回:
            List[ProcessedDocument]: 处理结果列表
        """
        results = []

        for file_path in file_paths:
            try:
                result = self.process(file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
                if not continue_on_error:
                    raise

        logger.info(f"批量处理完成: 成功 {len(results)} 个, 失败 {len(file_paths) - len(results)} 个")
        return results
