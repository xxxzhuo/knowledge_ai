"""为开发加载测试数据。"""

import logging
from datetime import datetime, timedelta
from app.database import SessionLocal, engine, Base
from app.models import Document, Chunk

logger = logging.getLogger(__name__)


def seed_test_data():
    """使用测试数据填充数据库。"""
    
    # 初始化表
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 检查数据是否已存在
        existing = db.query(Document).first()
        if existing:
            logger.info("测试数据已存在，跳过加载")
            return
        
        # 创建示例文档
        sample_docs = [
            Document(
                file_name="Intel_i7_Datasheet.pdf",
                file_path="documents/Intel_i7_Datasheet.pdf",
                vendor="Intel",
                category="CPU",
                package="BGA",
                product_name="Intel Core i7",
                processed="completed",
                page_count=150,
                chunk_count=45,
                file_size=5242880
            ),
            Document(
                file_name="TSMC_7nm_Process.pdf",
                file_path="documents/TSMC_7nm_Process.pdf",
                vendor="TSMC",
                category="Process",
                package="N/A",
                product_name="7nm Process Technology",
                processed="completed",
                page_count=120,
                chunk_count=36,
                file_size=4194304
            ),
            Document(
                file_name="ARM_Cortex_M4.pdf",
                file_path="documents/ARM_Cortex_M4.pdf",
                vendor="ARM",
                category="MCU",
                package="QFP",
                product_name="ARM Cortex-M4",
                processed="pending",
                page_count=80,
                chunk_count=0,
                file_size=3145728
            ),
        ]
        
        for doc in sample_docs:
            db.add(doc)
        
        db.commit()
        
        # 为第一个文档创建示例分块
        doc_id = sample_docs[0].id
        for i in range(5):
            chunk = Chunk(
                doc_id=doc_id,
                chunk_text=f"Sample chunk {i+1} content. This is a technical specification...",
                chunk_index=i,
                page_start=i*30,
                page_end=(i+1)*30,
                content_type="text",
                embedding_model="text-embedding-3-large",
                embedding_dims=1536
            )
            db.add(chunk)
        
        db.commit()
        logger.info(f"已加载 {len(sample_docs)} 个测试文档")
        
    except Exception as e:
        logger.error(f"加载测试数据出错: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_test_data()
