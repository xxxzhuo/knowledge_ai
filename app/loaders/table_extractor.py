"""
表格提取模块

使用 Camelot 库从PDF文档中实现高精度的表格检测和提取。
支持多种表格格式和复杂的表格结构识别。
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import camelot
except ImportError:
    camelot = None

import pandas as pd

logger = logging.getLogger(__name__)


class TableExtractor:
    """
    表格提取器
    
    从PDF中提取表格数据，支持：
        - 自动表格检测
        - 多种表格格式识别
        - 表格数据转为结构化格式
        - 表格位置和页面信息记录
    """

    def __init__(self, confidence_threshold: float = 50.0):
        """
        初始化表格提取器
        
        参数:
            confidence_threshold: 表格检测的置信度阈值 (0-100)
        """
        self.confidence_threshold = confidence_threshold
        if camelot is None:
            logger.warning("camelot 库未安装，表格提取功能不可用")

    def extract_tables_from_pdf(
        self,
        pdf_path: str,
        pages: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        从PDF文件提取所有表格
        
        参数:
            pdf_path: PDF文件路径
            pages: 要处理的页码范围 (例如 '1,3' 或 '1-5')
                  如果为None，则处理所有页面
        
        返回:
            List[Dict]: 包含所有提取表格的列表
            
        例子:
            tables = extractor.extract_tables_from_pdf(
                'document.pdf',
                pages='1-5'
            )
        """
        if camelot is None:
            logger.error("camelot 库未安装")
            return []

        try:
            logger.info(f"开始从PDF提取表格: {pdf_path}")

            tables = camelot.read_pdf(
                str(pdf_path),
                pages=pages or 'all',
                flavor='lattice',  # 使用 lattice 算法
            )

            extracted_tables = []

            for idx, table in enumerate(tables):
                table_data = {
                    "table_id": idx,
                    "page_number": table.page,
                    "accuracy": table.accuracy,
                    "rows": table.shape[0],
                    "columns": table.shape[1],
                    "data": table.df.to_dict(orient='records'),
                    "html": table.to_html(),
                    "csv": table.to_csv(),
                    "markdown": self._df_to_markdown(table.df),
                }
                extracted_tables.append(table_data)

            logger.info(f"成功提取 {len(extracted_tables)} 个表格")
            return extracted_tables

        except Exception as e:
            logger.error(f"表格提取失败: {str(e)}")
            return []

    def extract_tables_with_fallback(
        self,
        pdf_path: str,
        pages: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        使用多种方法提取表格（带回退策略）
        
        首先尝试使用 lattice 算法，如果失败则尝试 stream 算法。
        
        参数:
            pdf_path: PDF文件路径
            pages: 要处理的页码范围
        
        返回:
            List[Dict]: 提取的表格列表
        """
        if camelot is None:
            logger.error("camelot 库未安装")
            return []

        try:
            # 首先尝试 lattice 算法
            try:
                tables = camelot.read_pdf(
                    str(pdf_path),
                    pages=pages or 'all',
                    flavor='lattice',
                )
                if len(tables) > 0:
                    logger.info(f"使用 lattice 算法成功提取 {len(tables)} 个表格")
                    return self._format_tables(tables)
            except Exception as e:
                logger.debug(f"Lattice 算法失败: {str(e)}")

            # 回退到 stream 算法
            tables = camelot.read_pdf(
                str(pdf_path),
                pages=pages or 'all',
                flavor='stream',
            )
            logger.info(f"使用 stream 算法成功提取 {len(tables)} 个表格")
            return self._format_tables(tables)

        except Exception as e:
            logger.error(f"表格提取完全失败: {str(e)}")
            return []

    @staticmethod
    def _format_tables(tables) -> List[Dict[str, Any]]:
        """
        格式化 camelot 表格对象
        
        参数:
            tables: Camelot 表格对象列表
            
        返回:
            List[Dict]: 格式化后的表格数据
        """
        extracted_tables = []

        for idx, table in enumerate(tables):
            try:
                table_data = {
                    "table_id": idx,
                    "page_number": getattr(table, 'page', 'unknown'),
                    "accuracy": getattr(table, 'accuracy', 0.0),
                    "rows": table.shape[0],
                    "columns": table.shape[1],
                    "data": table.df.to_dict(orient='records'),
                    "html": table.to_html(),
                    "csv": table.to_csv(),
                }
                extracted_tables.append(table_data)
            except Exception as e:
                logger.warning(f"格式化表格 {idx} 失败: {str(e)}")

        return extracted_tables

    @staticmethod
    def _df_to_markdown(df: pd.DataFrame) -> str:
        """
        将 pandas DataFrame 转换为 Markdown 格式的表格
        
        参数:
            df: pandas DataFrame
            
        返回:
            str: Markdown 格式的表格
        """
        return df.to_markdown(index=False)

    def validate_table_quality(
        self,
        table_data: Dict[str, Any],
        min_accuracy: float = 50.0,
        min_rows: int = 1,
        min_columns: int = 1,
    ) -> bool:
        """
        验证表格质量是否满足要求
        
        参数:
            table_data: 表格数据字典
            min_accuracy: 最小精度阈值
            min_rows: 最小行数
            min_columns: 最小列数
            
        返回:
            bool: 表格是否满足质量要求
        """
        return (
            table_data.get("accuracy", 0) >= min_accuracy
            and table_data.get("rows", 0) >= min_rows
            and table_data.get("columns", 0) >= min_columns
        )
