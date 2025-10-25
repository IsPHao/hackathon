#!/bin/bash

echo "========================================"
echo "环境检查工具"
echo "========================================"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_version() {
    local name=$1
    local command=$2
    local min_version=$3
    local version=$4
    
    echo -n "检查 $name... "
    
    if ! command -v $command &> /dev/null; then
        echo -e "${RED}未安装${NC}"
        return 1
    fi
    
    if [ ! -z "$version" ]; then
        echo -e "${GREEN}✓${NC} (版本: $version)"
    else
        echo -e "${GREEN}✓${NC}"
    fi
    return 0
}

echo "系统依赖检查:"
echo "----------------------------"

ALL_OK=true

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    check_version "Python 3.10+" "python3" "3.10" "$PYTHON_VERSION"
else
    echo -e "Python 3.10+... ${RED}✗ 未安装${NC}"
    ALL_OK=false
fi

if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    check_version "Node.js 16+" "node" "16" "$NODE_VERSION"
else
    echo -e "Node.js 16+... ${RED}✗ 未安装${NC}"
    ALL_OK=false
fi

if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    check_version "npm" "npm" "" "$NPM_VERSION"
else
    echo -e "npm... ${RED}✗ 未安装${NC}"
    ALL_OK=false
fi

echo ""
echo "可选依赖检查:"
echo "----------------------------"

if command -v redis-server &> /dev/null; then
    REDIS_VERSION=$(redis-server --version | awk '{print $3}')
    check_version "Redis" "redis-server" "" "$REDIS_VERSION"
else
    echo -e "Redis... ${YELLOW}⚠ 未安装 (可选)${NC}"
fi

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    check_version "Docker" "docker" "" "$DOCKER_VERSION"
else
    echo -e "Docker... ${YELLOW}⚠ 未安装 (可选)${NC}"
fi

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | awk '{print $3}' | tr -d ',')
    check_version "Docker Compose" "docker-compose" "" "$COMPOSE_VERSION"
else
    echo -e "Docker Compose... ${YELLOW}⚠ 未安装 (可选)${NC}"
fi

echo ""
echo "项目配置检查:"
echo "----------------------------"

if [ -f "backend/.env" ]; then
    echo -e "backend/.env... ${GREEN}✓${NC}"
    
    if grep -q "your_openai_api_key_here" backend/.env; then
        echo -e "  ${YELLOW}⚠ 请配置 OPENAI_API_KEY${NC}"
    fi
else
    echo -e "backend/.env... ${RED}✗ 未找到${NC}"
    echo "  运行: cp backend/.env.example backend/.env"
    ALL_OK=false
fi

if [ -f "frontend/.env" ]; then
    echo -e "frontend/.env... ${GREEN}✓${NC}"
else
    echo -e "frontend/.env... ${YELLOW}⚠ 未找到 (可选)${NC}"
fi

if [ -d "backend/venv" ]; then
    echo -e "后端虚拟环境... ${GREEN}✓${NC}"
else
    echo -e "后端虚拟环境... ${RED}✗ 未创建${NC}"
    echo "  运行: cd backend && python3 -m venv venv"
    ALL_OK=false
fi

if [ -d "frontend/node_modules" ]; then
    echo -e "前端依赖... ${GREEN}✓${NC}"
else
    echo -e "前端依赖... ${RED}✗ 未安装${NC}"
    echo "  运行: cd frontend && npm install"
    ALL_OK=false
fi

echo ""
echo "Redis 服务检查:"
echo "----------------------------"

if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo -e "Redis 服务... ${GREEN}✓ 运行中${NC}"
    else
        echo -e "Redis 服务... ${YELLOW}⚠ 未运行${NC}"
        echo "  启动: redis-server"
        echo "  或使用 Docker: docker run -d -p 6379:6379 redis:7"
    fi
else
    echo -e "Redis 服务... ${YELLOW}⚠ Redis 未安装${NC}"
fi

echo ""
echo "========================================"
if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}✓ 环境检查通过！${NC}"
    echo ""
    echo "下一步:"
    echo "  1. 配置 backend/.env 中的 OPENAI_API_KEY"
    echo "  2. 运行 'make backend' 启动后端"
    echo "  3. 运行 'make frontend' 启动前端"
else
    echo -e "${RED}✗ 环境检查失败，请解决上述问题${NC}"
    echo ""
    echo "快速修复:"
    echo "  运行 './setup.sh' 自动配置环境"
fi
echo "========================================"
