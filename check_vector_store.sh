#!/bin/bash
# 向量库检查脚本

echo "=========================================="
echo "向量库设计和功能完善性检查"
echo "=========================================="
echo ""

# 检查文件是否存在
echo "检查文件完整性..."
echo "---------"

files_to_check=(
    "knowledge_ai/app/storage/milvus_store.py"
    "knowledge_ai/app/retriever/vector_retriever.py"
    "knowledge_ai/app/api/rag.py"
    "knowledge_ai/app/api/health.py"
    "knowledge_ai/tests/test_vector_store.py"
    "VECTOR_STORE_IMPROVEMENTS.md"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (未找到)"
    fi
done

echo ""
echo "=========================================="
echo "检查改进项"
echo "=========================================="
echo ""

# 1. 连接重试机制
echo "1. 连接重试机制"
echo "---------"
if grep -q "_connect_with_retry" knowledge_ai/app/storage/milvus_store.py; then
    echo "✓ 实现了 _connect_with_retry() 方法"
else
    echo "✗ 未找到 _connect_with_retry() 方法"
fi

if grep -q "max_retries" knowledge_ai/app/storage/milvus_store.py; then
    echo "✓ 支持可配置的重试次数"
else
    echo "✗ 未支持可配置的重试次数"
fi

# 2. 连接检查
echo ""
echo "2. 连接健康检查"
echo "---------"
if grep -q "_check_connection" knowledge_ai/app/storage/milvus_store.py; then
    echo "✓ 实现了连接检查机制"
else
    echo "✗ 未实现连接检查机制"
fi

if grep -q "is_healthy" knowledge_ai/app/storage/milvus_store.py; then
    echo "✓ 实现了 is_healthy() 方法"
else
    echo "✗ 未实现 is_healthy() 方法"
fi

# 3. 输入验证
echo ""
echo "3. 输入参数验证"
echo "---------"
if grep -q "raise ValueError" knowledge_ai/app/storage/milvus_store.py; then
    echo "✓ 实现了参数验证"
else
    echo "✗ 未实现参数验证"
fi

# 4. 安全性改进
echo ""
echo "4. 安全性改进"
echo "---------"
if grep -q "isinstance(id_val, str)" knowledge_ai/app/storage/milvus_store.py; then
    echo "✓ 验证了ID类型"
else
    echo "✗ 未验证ID类型"
fi

# 5. 异常处理
echo ""
echo "5. 异常处理"
echo "---------"
if grep -q "MilvusException" knowledge_ai/app/storage/milvus_store.py; then
    echo "✓ 处理了 MilvusException"
else
    echo "✗ 未处理 MilvusException"
fi

# 6. 依赖注入
echo ""
echo "6. 依赖注入"
echo "---------"
if grep -q "get_vector_retriever" knowledge_ai/app/api/rag.py; then
    echo "✓ 实现了依赖注入"
else
    echo "✗ 未实现依赖注入"
fi

# 7. 健康检查API
echo ""
echo "7. 健康检查API"
echo "---------"
if grep -q "check_vector_store" knowledge_ai/app/api/health.py; then
    echo "✓ 实现了向量库健康检查"
else
    echo "✗ 未实现向量库健康检查"
fi

if grep -q "health/vector-store" knowledge_ai/app/api/health.py; then
    echo "✓ 实现了向量库详细信息端点"
else
    echo "✗ 未实现向量库详细信息端点"
fi

# 8. 单元测试
echo ""
echo "8. 单元测试"
echo "---------"
if grep -q "class TestMilvusStore" knowledge_ai/tests/test_vector_store.py; then
    echo "✓ 实现了 Milvus 向量库测试"
else
    echo "✗ 未实现 Milvus 向量库测试"
fi

if grep -q "class TestVectorRetriever" knowledge_ai/tests/test_vector_store.py; then
    echo "✓ 实现了检索器测试"
else
    echo "✗ 未实现检索器测试"
fi

if grep -q "class TestVectorStorePerformance" knowledge_ai/tests/test_vector_store.py; then
    echo "✓ 实现了性能测试"
else
    echo "✗ 未实现性能测试"
fi

echo ""
echo "=========================================="
echo "统计信息"
echo "=========================================="
echo ""

echo "修改的文件数量："
git diff --name-only 2>/dev/null | wc -l || echo "无法获取"

echo ""
echo "新增的测试用例数量："
grep -c "def test_" knowledge_ai/tests/test_vector_store.py 2>/dev/null || echo "无法获取"

echo ""
echo "=========================================="
echo "检查完成"
echo "=========================================="
