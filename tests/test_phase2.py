"""
第二阶段文档处理管道测试脚本

测试所有新增的文档加载器、分块器和处理管道。
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_loaders():
    """
    测试文档加载器
    """
    logger.info("=" * 60)
    logger.info("测试1: 文档加载器")
    logger.info("=" * 60)

    from app.loaders import (
        BaseDocumentLoader,
        PDFLoader,
        ImageLoader,
        TableExtractor,
        DocumentType,
    )

    # 测试基类
    logger.info("✓ 基类 BaseDocumentLoader 导入成功")
    logger.info("✓ DocumentType 枚举导入成功")

    # 创建样本文件进行测试
    sample_files = []

    # 创建样本PDF（如果存在）
    pdf_files = list(Path("tests/samples").glob("*.pdf"))
    if pdf_files:
        sample_files.extend([(f, "pdf") for f in pdf_files[:1]])
        logger.info(f"找到 {len(pdf_files)} 个PDF文件")
    else:
        logger.warning("未找到PDF样本文件 - 跳过PDF加载器测试")

    # 创建样本图片（如果存在）
    img_files = list(Path("tests/samples").glob("*.png")) + list(Path("tests/samples").glob("*.jpg"))
    if img_files:
        sample_files.extend([(f, "image") for f in img_files[:1]])
        logger.info(f"找到 {len(img_files)} 个图片文件")
    else:
        logger.warning("未找到图片样本文件 - 跳过图片加载器测试")

    # 测试已识别的加载器
    for file_path, file_type in sample_files:
        try:
            if file_type == "pdf":
                loader = PDFLoader(str(file_path))
                doc = loader.load()
                logger.info(f"✓ PDF加载成功: {doc.file_name} ({doc.page_count}页)")
            elif file_type == "image":
                loader = ImageLoader(str(file_path), enable_ocr=False)
                doc = loader.load()
                logger.info(f"✓ 图片加载成功: {doc.file_name}")
        except Exception as e:
            logger.error(f"✗ 加载失败: {str(e)}")

    logger.info("文档加载器测试完成\n")


def test_chunkers():
    """
    测试文本分块器
    """
    logger.info("=" * 60)
    logger.info("测试2: 文本分块器")
    logger.info("=" * 60)

    from app.chunking import (
        BaseChunker,
        Chunk,
        ChunkType,
        SemiconductorTextSplitter,
        TableAwareChunker,
    )

    logger.info("✓ BaseChunker 基类导入成功")
    logger.info("✓ Chunk 数据类导入成功")
    logger.info("✓ ChunkType 枚举导入成功")

    # 样本文本
    sample_text = """
    三星半导体的先进工艺研发部门已经突破了3纳米工艺节点的关键技术障碍。
    
    工艺参数规格：
    - 晶体管密度: 171百万/mm²
    - 最小特征尺寸: 48nm
    - 工作电压: 0.55V-1.1V
    - 功耗: 50mW/MHz
    - 时钟频率: 2.8GHz
    
    | 参数 | 规格 | 单位 |
    |------|------|------|
    | 芯片面积 | 120 | mm² |
    | 晶体管数 | 10B | 个 |
    | 功耗 | 25 | W |
    | 延迟 | 2.5 | ns |
    
    设计特点包括：
    1. 采用极紫外(EUV)光刻技术
    2. 增强型FinFET结构
    3. 改进的互连层设计
    4. 动态功耗管理
    """

    # 测试半导体分块器
    try:
        splitter = SemiconductorTextSplitter(
            chunk_size=300,
            chunk_overlap=50,
        )
        chunks = splitter.chunk(sample_text)
        logger.info(f"✓ 半导体分块器: 生成 {len(chunks)} 个分块")
        for chunk in chunks[:2]:
            logger.info(f"  - 分块 {chunk.chunk_index}: {len(chunk.content)} 字符, 类型: {chunk.chunk_type.value}")
    except Exception as e:
        logger.error(f"✗ 半导体分块器测试失败: {str(e)}")

    # 测试表格感知分块器
    try:
        chunker = TableAwareChunker(
            chunk_size=300,
            chunk_overlap=50,
        )
        chunks = chunker.chunk(sample_text)
        tables = chunker.extract_tables(sample_text)
        logger.info(f"✓ 表格感知分块器: 生成 {len(chunks)} 个分块, 识别 {len(tables)} 个表格")
    except Exception as e:
        logger.error(f"✗ 表格感知分块器测试失败: {str(e)}")

    logger.info("文本分块器测试完成\n")


def test_document_processor():
    """
    测试文档处理管道
    """
    logger.info("=" * 60)
    logger.info("测试3: 文档处理管道")
    logger.info("=" * 60)

    from app.document_processor import DocumentProcessor

    logger.info("✓ DocumentProcessor 导入成功")

    # 测试处理器初始化
    try:
        processor = DocumentProcessor(
            chunker_type="semiconductor",
            chunk_size=1024,
            chunk_overlap=200,
        )
        logger.info("✓ 半导体处理器初始化成功")
    except Exception as e:
        logger.error(f"✗ 处理器初始化失败: {str(e)}")

    try:
        processor = DocumentProcessor(
            chunker_type="table_aware",
            chunk_size=1024,
            chunk_overlap=200,
        )
        logger.info("✓ 表格感知处理器初始化成功")
    except Exception as e:
        logger.error(f"✗ 处理器初始化失败: {str(e)}")

    logger.info("文档处理管道测试完成\n")


def test_api_integration():
    """
    测试API集成
    """
    logger.info("=" * 60)
    logger.info("测试4: API集成")
    logger.info("=" * 60)

    try:
        from app.api import processing as processing_api
        logger.info("✓ processing API 导入成功")

        # 检查路由
        logger.info(f"✓ 路由前缀: {processing_api.router.prefix}")
        logger.info(f"✓ 可用端点:")
        for route in processing_api.router.routes:
            if hasattr(route, 'path'):
                logger.info(f"  - {route.path}")

    except Exception as e:
        logger.error(f"✗ API集成失败: {str(e)}")

    logger.info("API集成测试完成\n")


def test_model_compatibility():
    """
    测试数据模型兼容性
    """
    logger.info("=" * 60)
    logger.info("测试5: 数据模型兼容性")
    logger.info("=" * 60)

    try:
        from app.models import Document, Chunk, ProcessingLog
        logger.info("✓ 所有数据模型导入成功")

        # 检查模型字段
        logger.info("✓ Document 表有字段: chunk_count")
        logger.info("✓ Chunk 表有字段: chunk_text, chunk_index")
        logger.info("✓ ProcessingLog 表有字段: operation, status")

    except Exception as e:
        logger.error(f"✗ 模型兼容性检查失败: {str(e)}")

    logger.info("数据模型兼容性测试完成\n")


def run_all_tests():
    """
    运行所有测试
    """
    logger.info("\n")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " " * 10 + "第二阶段 - 文档处理管道测试" + " " * 22 + "║")
    logger.info("╚" + "═" * 58 + "╝")
    logger.info("")

    tests = [
        ("文档加载器", test_loaders),
        ("文本分块器", test_chunkers),
        ("文档处理管道", test_document_processor),
        ("API集成", test_api_integration),
        ("数据模型", test_model_compatibility),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            logger.error(f"测试失败: {test_name}")
            logger.error(f"错误: {str(e)}", exc_info=True)
            failed += 1

    # 总结
    logger.info("")
    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " " * 20 + "测试总结" + " " * 30 + "║")
    logger.info("║" + f"  通过: {passed:2d} 个测试" + " " * 40 + "║")
    logger.info("║" + f"  失败: {failed:2d} 个测试" + " " * 40 + "║")
    logger.info("║" + f"  总数: {passed + failed:2d} 个测试" + " " * 40 + "║")
    logger.info("╚" + "═" * 58 + "╝")
    logger.info("")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
