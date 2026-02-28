"""数据库迁移工具。"""

import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, Base

logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库表。"""
    logger.info("创建数据库表...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表创建成功")


def drop_database():
    """删除所有数据库表。"""
    logger.warning("删除所有数据库表...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("所有数据库表已删除")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        drop_database()
    else:
        init_database()
