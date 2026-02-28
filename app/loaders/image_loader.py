"""
图片加载器和处理模块

支持从PDF中提取图片，以及处理独立的图片文件。
包含OCR功能来识别图片中的文本内容。
"""

import logging
from typing import List, Dict, Any
from pathlib import Path
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

from .base import BaseDocumentLoader, LoadedDocument, DocumentType

logger = logging.getLogger(__name__)


class ImageLoader(BaseDocumentLoader):
    """
    图片文档加载器
    
    支持加载常见图片格式（JPG、PNG、GIF等）。
    可选集成OCR功能提取图片中的文本。
    """

    def __init__(
        self,
        file_path: str,
        enable_ocr: bool = False,
        ocr_lang: str = "ch",  # 中文
    ):
        """
        初始化图片加载器
        
        参数:
            file_path: 图片文件路径
            enable_ocr: 是否启用OCR文本识别
            ocr_lang: OCR识别的语言 ('ch' 中文, 'en' 英文)
        """
        super().__init__(file_path)
        self.enable_ocr = enable_ocr
        self.ocr_lang = ocr_lang
        self._validate_image()
        self.ocr_engine = None

        if self.enable_ocr:
            self._init_ocr()

    def _validate_image(self) -> None:
        """
        验证文件是否为有效的图片文件
        
        抛出:
            ValueError: 如果文件不是有效的图片格式
        """
        valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        if self.file_path.suffix.lower() not in valid_extensions:
            raise ValueError(
                f"不支持的图片格式: {self.file_path.suffix}. "
                f"支持的格式: {valid_extensions}"
            )

    def _init_ocr(self) -> None:
        """初始化OCR引擎"""
        if PaddleOCR is None:
            logger.warning("PaddleOCR 未安装，OCR功能不可用")
            self.enable_ocr = False
            return

        try:
            logger.info("初始化 PaddleOCR 引擎...")
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang=self.ocr_lang,
            )
            logger.info("PaddleOCR 引擎初始化成功")
        except Exception as e:
            logger.error(f"PaddleOCR 初始化失败: {str(e)}")
            self.enable_ocr = False

    def load(self) -> LoadedDocument:
        """
        加载图片文档
        
        返回:
            LoadedDocument: 包含图片内容的文档对象
        """
        try:
            if Image is None:
                raise ImportError("Pillow 库未安装")

            # 打开图片
            image = Image.open(str(self.file_path))

            # 获取图片元数据
            metadata = self._extract_image_metadata(image)

            # 提取文本（如果启用OCR）
            ocr_text = ""
            if self.enable_ocr and self.ocr_engine:
                ocr_text = self._ocr_image(image)

            # 合并内容
            content = ocr_text if ocr_text else "[图片文档，未提取到文本]"

            logger.info(f"成功加载图片: {self.file_name}")

            return LoadedDocument(
                content=content,
                document_type=DocumentType.IMAGE,
                file_path=self.file_path,
                file_name=self.file_name,
                metadata=metadata,
                images=[{
                    "file_name": self.file_name,
                    "size": image.size,
                    "format": image.format,
                    "mode": image.mode,
                }],
            )

        except Exception as e:
            logger.error(f"加载图片失败: {self.file_name}, 错误: {str(e)}")
            raise

    def _extract_image_metadata(self, image: 'Image.Image') -> Dict[str, Any]:
        """
        提取图片元数据
        
        参数:
            image: PIL Image对象
            
        返回:
            Dict: 图片元数据
        """
        metadata = self._extract_metadata()

        metadata.update({
            "image_format": image.format,
            "image_size": image.size,
            "image_width": image.width,
            "image_height": image.height,
            "image_mode": image.mode,
        })

        # 提取图片信息
        if hasattr(image, 'info'):
            metadata["image_info"] = str(image.info)

        return metadata

    def _ocr_image(self, image: 'Image.Image') -> str:
        """
        使用OCR识别图片中的文本
        
        参数:
            image: PIL Image对象
            
        返回:
            str: 识别的文本内容
        """
        if not self.ocr_engine:
            return ""

        try:
            logger.info(f"开始OCR识别: {self.file_name}")

            # PaddleOCR 接收 numpy array 或 file path
            result = self.ocr_engine.ocr(str(self.file_path), cls=True)

            # 提取文本
            ocr_text = self._parse_ocr_result(result)

            logger.info(f"OCR识别完成，识别 {len(ocr_text)} 个文本区域")
            return ocr_text

        except Exception as e:
            logger.error(f"OCR识别失败: {str(e)}")
            return ""

    @staticmethod
    def _parse_ocr_result(ocr_result: List) -> str:
        """
        解析 PaddleOCR 的识别结果
        
        参数:
            ocr_result: PaddleOCR 返回的识别结果
            
        返回:
            str: 合并后的文本
        """
        if not ocr_result:
            return ""

        texts = []
        for line in ocr_result:
            if line:
                for word_info in line:
                    if len(word_info) >= 2:
                        # word_info 格式: ([box], (text, confidence))
                        text = word_info[1][0]
                        confidence = word_info[1][1]
                        if confidence > 0.5:  # 置信度过滤
                            texts.append(text)

        return "\n".join(texts)


class PDFImageExtractor:
    """
    从PDF中提取图片的工具类
    
    支持：
        - 从PDF页面提取所有图片
        - 保存提取的图片到文件
        - 对提取的图片执行OCR
    """

    def __init__(self, enable_ocr: bool = False):
        """
        初始化PDF图片提取器
        
        参数:
            enable_ocr: 是否对提取的图片执行OCR
        """
        self.enable_ocr = enable_ocr
        self.ocr_engine = None

        if enable_ocr and PaddleOCR:
            try:
                self.ocr_engine = PaddleOCR(use_angle_cls=True, lang="ch")
            except Exception as e:
                logger.warning(f"OCR初始化失败: {str(e)}")

    def extract_images_from_pdf(
        self,
        pdf_path: str,
        output_dir: str = None,
    ) -> List[Dict[str, Any]]:
        """
        从PDF文件提取所有图片
        
        参数:
            pdf_path: PDF文件路径
            output_dir: 图片输出目录（如果为None则不保存）
            
        返回:
            List[Dict]: 提取的图片信息列表
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            logger.error("pypdf 库未安装")
            return []

        try:
            if Image is None:
                raise ImportError("Pillow 库未安装")

            reader = PdfReader(str(pdf_path))
            images_data = []
            image_count = 0

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    # 获取页面中的对象
                    if "/XObject" in page["/Resources"]:
                        xobj = page["/Resources"]["/XObject"].get_object()

                        for obj_name in xobj:
                            try:
                                obj = xobj[obj_name].get_object()
                                if obj["/Subtype"] == "/Image":
                                    image_count += 1
                                    img_data = self._extract_image_object(
                                        obj,
                                        page_num,
                                        image_count,
                                        output_dir,
                                    )
                                    if img_data:
                                        images_data.append(img_data)
                            except Exception as e:
                                logger.debug(f"提取对象失败: {str(e)}")

                except Exception as e:
                    logger.debug(f"页面 {page_num} 图片提取失败: {str(e)}")

            logger.info(f"从PDF提取 {len(images_data)} 个图片")
            return images_data

        except Exception as e:
            logger.error(f"PDF图片提取失败: {str(e)}")
            return []

    def _extract_image_object(
        self,
        obj,
        page_num: int,
        image_id: int,
        output_dir: str = None,
    ) -> Dict[str, Any]:
        """
        提取单个图片对象
        
        参数:
            obj: PDF图片对象
            page_num: 页码
            image_id: 图片编号
            output_dir: 输出目录
            
        返回:
            Dict: 图片信息
        """
        try:
            from PIL import Image
            import io

            # 解码图片数据
            if obj["/Filter"] == "/FlateDecode":
                data = obj._get_data()
                size = (obj["/Width"], obj["/Height"])
                image = Image.frombytes("RGB", size, data)
            else:
                # 其他格式可能需要特殊处理
                return None

            # 保存到文件（如果指定）
            file_name = None
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                file_name = f"page_{page_num}_image_{image_id}.png"
                image.save(str(output_path / file_name))

            img_data = {
                "page_number": page_num,
                "image_id": image_id,
                "file_name": file_name,
                "size": image.size,
            }

            # 如果启用OCR，识别文本
            if self.enable_ocr and self.ocr_engine:
                img_data["ocr_text"] = self._ocr_pil_image(image)

            return img_data

        except Exception as e:
            logger.error(f"提取图片对象失败: {str(e)}")
            return None

    def _ocr_pil_image(self, image: 'Image.Image') -> str:
        """
        对PIL图片执行OCR
        
        参数:
            image: PIL Image对象
            
        返回:
            str: OCR识别的文本
        """
        try:
            import numpy as np

            # 转换为 numpy array
            img_array = np.array(image)
            result = self.ocr_engine.ocr(img_array, cls=True)

            texts = []
            for line in result:
                if line:
                    for word_info in line:
                        if len(word_info) >= 2:
                            text = word_info[1][0]
                            texts.append(text)

            return "\n".join(texts)

        except Exception as e:
            logger.error(f"图片OCR失败: {str(e)}")
            return ""
