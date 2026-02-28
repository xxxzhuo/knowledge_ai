#!/bin/bash
# Docker 启动和初始化脚本

set -e  # 任何错误退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$SCRIPT_DIR/docker"

print_message "$BLUE" "=========================================="
print_message "$BLUE" "Knowledge AI Docker 管理脚本"
print_message "$BLUE" "=========================================="

# 检查 docker-compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    print_message "$RED" "✗ docker-compose 未安装"
    exit 1
fi

print_message "$GREEN" "✓ docker-compose 已安装"

# 确定命令
COMMAND=${1:-"help"}

case "$COMMAND" in
    start)
        print_message "$BLUE" "\n启动所有服务..."
        print_message "$BLUE" "=========================================="
        
        cd "$DOCKER_DIR"
        
        # 启动所有服务
        docker-compose up -d
        
        print_message "$GREEN" "✓ 所有服务已启动"
        print_message "$BLUE" "\n等待服务启动完成..."
        sleep 10
        
        # 检查服务健康状态
        print_message "$BLUE" "检查服务健康状态..."
        print_message "$BLUE" "=========================================="
        
        # 检查 PostgreSQL
        if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
            print_message "$GREEN" "✓ PostgreSQL 已就绪"
        else
            print_message "$YELLOW" "⚠ PostgreSQL 还在启动..."
        fi
        
        # 检查 Milvus
        if curl -s http://localhost:9091/healthz > /dev/null 2>&1; then
            print_message "$GREEN" "✓ Milvus 已就绪"
        else
            print_message "$YELLOW" "⚠ Milvus 还在启动..."
        fi
        
        # 检查 MinIO
        if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
            print_message "$GREEN" "✓ MinIO 已就绪"
        else
            print_message "$YELLOW" "⚠ MinIO 还在启动..."
        fi
        
        print_message "$GREEN" "\n✓ 启动完成！"
        print_message "$BLUE" "\n服务地址："
        print_message "$BLUE" "  - API: http://localhost:8000"
        print_message "$BLUE" "  - PostgreSQL: localhost:5432"
        print_message "$BLUE" "  - Milvus: localhost:19530"
        print_message "$BLUE" "  - MinIO: http://localhost:9000 (用户: minioadmin/minioadmin)"
        print_message "$BLUE" "  - Prometheus: http://localhost:9090"
        ;;
    
    stop)
        print_message "$BLUE" "\n停止所有服务..."
        print_message "$BLUE" "=========================================="
        
        cd "$DOCKER_DIR"
        docker-compose down
        
        print_message "$GREEN" "✓ 所有服务已停止"
        ;;
    
    restart)
        print_message "$BLUE" "\n重启所有服务..."
        print_message "$BLUE" "=========================================="
        
        cd "$DOCKER_DIR"
        docker-compose restart
        
        print_message "$GREEN" "✓ 所有服务已重启"
        sleep 5
        ;;
    
    logs)
        print_message "$BLUE" "\n显示服务日志..."
        print_message "$BLUE" "=========================================="
        
        cd "$DOCKER_DIR"
        docker-compose logs -f ${2:-}
        ;;
    
    init-milvus)
        print_message "$BLUE" "\n初始化 Milvus..."
        print_message "$BLUE" "=========================================="
        
        # 等待 Milvus 启动
        print_message "$YELLOW" "等待 Milvus 服务就绪..."
        max_retries=30
        retry_count=0
        
        while ! curl -s http://localhost:9091/healthz > /dev/null 2>&1; do
            if [ $retry_count -ge $max_retries ]; then
                print_message "$RED" "✗ Milvus 启动超时"
                exit 1
            fi
            sleep 2
            retry_count=$((retry_count + 1))
        done
        
        print_message "$GREEN" "✓ Milvus 已启动"
        
        # 运行初始化脚本
        cd "$SCRIPT_DIR"
        python3 scripts/init_milvus.py
        ;;
    
    test)
        print_message "$BLUE" "\n测试向量存储功能..."
        print_message "$BLUE" "=========================================="
        
        cd "$SCRIPT_DIR"
        python3 scripts/test_vector_store_integration.py
        ;;
    
    full-init)
        print_message "$BLUE" "\n执行完整初始化..."
        print_message "$BLUE" "=========================================="
        
        # 1. 启动服务
        print_message "$BLUE" "\n第 1 步: 启动所有服务..."
        "$0" start
        
        # 2. 初始化数据库
        print_message "$BLUE" "\n第 2 步: 初始化 PostgreSQL 数据库..."
        cd "$SCRIPT_DIR"
        python3 scripts/init_db.py
        
        # 3. 初始化 Milvus
        print_message "$BLUE" "\n第 3 步: 初始化 Milvus 向量库..."
        "$0" init-milvus
        
        # 4. 测试功能
        print_message "$BLUE" "\n第 4 步: 测试向量存储功能..."
        "$0" test
        
        print_message "$GREEN" "\n✓ 完整初始化完成！"
        ;;
    
    status)
        print_message "$BLUE" "\n检查服务状态..."
        print_message "$BLUE" "=========================================="
        
        cd "$DOCKER_DIR"
        docker-compose ps
        
        # 额外的健康检查
        print_message "$BLUE" "\n详细健康检查:"
        
        # PostgreSQL
        echo -n "PostgreSQL: "
        if curl -s http://localhost:5432 > /dev/null 2>&1 || \
           docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
            print_message "$GREEN" "✓ 运行中"
        else
            print_message "$RED" "✗ 离线"
        fi
        
        # Milvus
        echo -n "Milvus: "
        if curl -s http://localhost:9091/healthz > /dev/null 2>&1; then
            print_message "$GREEN" "✓ 运行中"
        else
            print_message "$RED" "✗ 离线"
        fi
        
        # MinIO
        echo -n "MinIO: "
        if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
            print_message "$GREEN" "✓ 运行中"
        else
            print_message "$RED" "✗ 离线"
        fi
        
        # API
        echo -n "API: "
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_message "$GREEN" "✓ 运行中"
        else
            print_message "$RED" "✗ 离线"
        fi
        
        # Prometheus
        echo -n "Prometheus: "
        if curl -s http://localhost:9090 > /dev/null 2>&1; then
            print_message "$GREEN" "✓ 运行中"
        else
            print_message "$RED" "✗ 离线"
        fi
        ;;
    
    clean)
        print_message "$YELLOW" "\n清理所有数据和容器..."
        print_message "$YELLOW" "=========================================="
        
        read -p "确认要删除所有数据吗? (y/N): " confirm
        if [ "$confirm" = "y" ]; then
            cd "$DOCKER_DIR"
            docker-compose down -v
            print_message "$GREEN" "✓ 清理完成"
        else
            print_message "$YELLOW" "操作已取消"
        fi
        ;;
    
    shell)
        print_message "$BLUE" "\n连接到 API 容器 Shell..."
        
        cd "$DOCKER_DIR"
        docker-compose exec api bash
        ;;
    
    *)
        print_message "$BLUE" "使用说明:"
        echo ""
        echo "  ./docker_manage.sh <command> [options]"
        echo ""
        echo "可用命令:"
        echo "  start           - 启动所有服务"
        echo "  stop            - 停止所有服务"
        echo "  restart         - 重启所有服务"
        echo "  logs [service]  - 显示服务日志"
        echo "  status          - 检查服务状态"
        echo "  init-milvus     - 初始化 Milvus 向量库"
        echo "  test            - 测试向量存储功能"
        echo "  full-init       - 执行完整初始化"
        echo "  clean           - 清理所有数据"
        echo "  shell           - 连接到 API 容器"
        echo "  help            - 显示此帮助信息"
        echo ""
        echo "示例:"
        echo "  ./docker_manage.sh start          # 启动服务"
        echo "  ./docker_manage.sh full-init      # 完整初始化"
        echo "  ./docker_manage.sh logs api       # 查看 API 日志"
        echo "  ./docker_manage.sh status         # 检查状态"
        ;;
esac
