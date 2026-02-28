"""测试配置和夹具。"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import Document, Chunk

# 使用 SQLite 临时数据库进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """创建测试数据库。"""
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    
    yield db_session
    
    db_session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """创建测试客户端。"""
    
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_document(db):
    """创建测试用文档。"""
    doc = Document(
        file_name="test_document.pdf",
        file_path="documents/test_document.pdf",
        vendor="Test Vendor",
        category="Test Category",
        processed="completed",
        page_count=100,
        chunk_count=10,
        file_size=1000000
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@pytest.fixture
def sample_chunk(db, sample_document):
    """创建测试用分块。"""
    chunk = Chunk(
        doc_id=sample_document.id,
        chunk_text="This is a sample chunk of text for testing purposes.",
        chunk_index=0,
        page_start=1,
        page_end=5,
        content_type="text"
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk
