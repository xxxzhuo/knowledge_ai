#!/bin/bash
# 项目完整性检查脚本

echo "🔍 项目完整性检查"
echo "===================="
echo ""

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/../" && pwd )"

# 定义检查列表
check_file() {
    if [ -f "$1" ]; then
        echo "✅ $2"
        return 0
    else
        echo "❌ $2"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo "✅ $2"
        return 0
    else
        echo "❌ $2"
        return 1
    fi
}

# 检查文件
echo "📄 配置文件:"
check_file "$PROJECT_DIR/requirements.txt" "requirements.txt"
check_file "$PROJECT_DIR/.env.example" ".env.example"
check_file "$PROJECT_DIR/.gitignore" ".gitignore"

echo ""
echo "📂 目录结构:"
check_dir "$PROJECT_DIR/app" "app/"
check_dir "$PROJECT_DIR/app/api" "app/api/"
check_dir "$PROJECT_DIR/app/agent" "app/agent/"
check_dir "$PROJECT_DIR/app/rag" "app/rag/"
check_dir "$PROJECT_DIR/docker" "docker/"
check_dir "$PROJECT_DIR/scripts" "scripts/"
check_dir "$PROJECT_DIR/tests" "tests/"

echo ""
echo "🐍 应用文件:"
check_file "$PROJECT_DIR/app/main.py" "app/main.py (FastAPI应用)"
check_file "$PROJECT_DIR/app/config.py" "app/config.py (配置管理)"
check_file "$PROJECT_DIR/app/database.py" "app/database.py (数据库)"
check_file "$PROJECT_DIR/app/models.py" "app/models.py (ORM模型)"
check_file "$PROJECT_DIR/app/schemas.py" "app/schemas.py (Pydantic schemas)"
check_file "$PROJECT_DIR/main.py" "main.py (启动入口)"

echo ""
echo "🌐 API模块:"
check_file "$PROJECT_DIR/app/api/health.py" "api/health.py"
check_file "$PROJECT_DIR/app/api/documents.py" "api/documents.py"
check_file "$PROJECT_DIR/app/api/rag.py" "api/rag.py"

echo ""
echo "🐳 Docker:"
check_file "$PROJECT_DIR/docker/Dockerfile" "docker/Dockerfile"
check_file "$PROJECT_DIR/docker/docker-compose.yml" "docker/docker-compose.yml"
check_file "$PROJECT_DIR/docker/prometheus.yml" "docker/prometheus.yml"

echo ""
echo "🧪 测试:"
check_file "$PROJECT_DIR/tests/conftest.py" "tests/conftest.py"
check_file "$PROJECT_DIR/tests/test_api.py" "tests/test_api.py"

echo ""
echo "📖 文档:"
check_file "$PROJECT_DIR/README.md" "README.md"
check_file "$PROJECT_DIR/PHASE1_SUMMARY.md" "PHASE1_SUMMARY.md"

echo ""
echo "📋 工具脚本:"
check_file "$PROJECT_DIR/scripts/init_db.py" "scripts/init_db.py"
check_file "$PROJECT_DIR/scripts/seed_data.py" "scripts/seed_data.py"
check_file "$PROJECT_DIR/scripts/quickstart.sh" "scripts/quickstart.sh"

echo ""
echo "===================="
echo "✅ 检查完成！"
