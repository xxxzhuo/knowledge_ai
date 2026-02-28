"""API 端点测试。"""

import pytest


class TestHealth:
    """健康检查端点测试。"""
    
    def test_health_check(self, client):
        """测试健康检查端点。"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data
    
    def test_status_endpoint(self, client):
        """测试状态端点。"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data


class TestDocuments:
    """文档管理端点测试。"""
    
    def test_list_documents_empty(self, client):
        """测试空列表情况。"""
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
    
    def test_create_document(self, client):
        """测试创建新文档。"""
        response = client.post(
            "/api/v1/documents",
            json={
                "file_name": "test.pdf",
                "vendor": "Intel",
                "category": "CPU"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["file_name"] == "test.pdf"
        assert data["vendor"] == "Intel"
        assert data["processed"] == "pending"
    
    def test_create_duplicate_document(self, client, sample_document):
        """测试重复文档创建失败。"""
        response = client.post(
            "/api/v1/documents",
            json={
                "file_name": sample_document.file_name,
                "vendor": "Intel"
            }
        )
        assert response.status_code == 400
    
    def test_get_document(self, client, sample_document):
        """测试获取指定文档。"""
        response = client.get(f"/api/v1/documents/{sample_document.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_document.id
        assert data["file_name"] == sample_document.file_name
    
    def test_get_nonexistent_document(self, client):
        """测试获取不存在的文档。"""
        response = client.get("/api/v1/documents/nonexistent")
        assert response.status_code == 404
    
    def test_update_document(self, client, sample_document):
        """测试更新文档。"""
        response = client.put(
            f"/api/v1/documents/{sample_document.id}",
            json={
                "vendor": "Updated Vendor"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vendor"] == "Updated Vendor"
    
    def test_delete_document(self, client, sample_document):
        """测试删除文档。"""
        response = client.delete(f"/api/v1/documents/{sample_document.id}")
        assert response.status_code == 200
        
        # 确认文档已删除
        get_response = client.get(f"/api/v1/documents/{sample_document.id}")
        assert get_response.status_code == 404
    
    def test_list_documents_with_filters(self, client, sample_document):
        """测试带过滤条件的列表查询。"""
        response = client.get(
            "/api/v1/documents",
            params={"vendor": sample_document.vendor}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["vendor"] == sample_document.vendor


class TestDocumentChunks:
    """文档分块端点测试。"""
    
    def test_get_document_chunks(self, client, sample_document, sample_chunk):
        """测试获取文档分块。"""
        response = client.get(f"/api/v1/documents/{sample_document.id}/chunks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["doc_id"] == sample_document.id
    
    def test_get_chunks_nonexistent_document(self, client):
        """测试获取不存在文档的分块。"""
        response = client.get("/api/v1/documents/nonexistent/chunks")
        assert response.status_code == 404


class TestRAG:
    """RAG 查询端点测试。"""
    
    def test_query_endpoint(self, client):
        """测试 RAG 查询端点。"""
        response = client.post(
            "/api/v1/query",
            json={
                "question": "What is the clock frequency?",
                "top_k": 5,
                "use_rerank": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "question" in data
        assert "answer" in data
        assert "retrieved_chunks" in data
        assert "confidence_score" in data
    
    def test_batch_query(self, client):
        """测试批量查询端点。"""
        response = client.post(
            "/api/v1/query/batch",
            json=[
                {"question": "Question 1?"},
                {"question": "Question 2?"}
            ]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
