#!/bin/bash
# 快速启动脚本

set -e

echo "🚀 Semiconductor Knowledge AI - 快速启动脚本"
echo "=============================================="
echo ""

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 检查Python版本
echo "📋 检查Python版本..."
python3 --version

# 创建虚拟环境
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

# 激活虚拟环境
echo "✨ 激活虚拟环境..."
source "$PROJECT_DIR/venv/bin/activate"

# 安装依赖 (可选，如果需要)
# echo "📥 安装依赖..."
# pip install --upgrade pip
# pip install -r "$PROJECT_DIR/requirements.txt"

# 复制环境文件
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚙️  复制环境配置..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "   ✓ .env 文件已创建，请根据需要修改配置"
fi

# 初始化数据库
echo "🗄️  初始化数据库..."
python "$PROJECT_DIR/scripts/init_db.py"

# 加载测试数据
echo "📊 加载测试数据..."
python "$PROJECT_DIR/scripts/seed_data.py"

echo ""
echo "✅ 启动准备完成！"
echo ""
echo "🎯 下一步操作："
echo ""
echo "   选项A - 启动API服务："
echo "   python main.py"
echo ""
echo "   选项B - 使用Docker Compose (推荐):"
echo "   cd docker && docker-compose up -d"
echo ""
echo "   查看API文档:"
echo "   http://localhost:8000/docs"
echo ""
