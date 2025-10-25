#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "智能动漫生成系统 - 环境准备脚本"
echo "========================================"
echo ""

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ $1 未安装"
        return 1
    else
        echo "✅ $1 已安装: $($1 --version | head -n 1)"
        return 0
    fi
}

echo "1. 检查系统依赖..."
echo "----------------------------"

DEPS_OK=true

if ! check_command python3; then
    echo "   请安装 Python 3.10+"
    DEPS_OK=false
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "   ⚠️  Python 版本需要 3.10+，当前版本: $PYTHON_VERSION"
    DEPS_OK=false
fi

if ! check_command node; then
    echo "   请安装 Node.js 16+"
    DEPS_OK=false
fi

if ! check_command npm; then
    echo "   请安装 npm"
    DEPS_OK=false
fi

if ! check_command redis-server; then
    echo "   ⚠️  Redis 未安装（可选，用于缓存）"
    echo "   安装方式："
    echo "     - macOS: brew install redis"
    echo "     - Ubuntu: sudo apt-get install redis-server"
    echo "     - 或使用 Docker: docker run -d -p 6379:6379 redis:7"
fi

if ! check_command docker; then
    echo "   ⚠️  Docker 未安装（可选，用于容器化部署）"
fi

echo ""

if [ "$DEPS_OK" = false ]; then
    echo "❌ 请先安装缺失的依赖"
    exit 1
fi

echo "2. 设置后端环境..."
echo "----------------------------"
cd backend

if [ ! -f ".env" ]; then
    echo "   创建 .env 配置文件..."
    cp .env.example .env
    echo "   ⚠️  请编辑 backend/.env 文件，填入你的 API 密钥"
else
    echo "   ✅ .env 文件已存在"
fi

if [ ! -d "venv" ]; then
    echo "   创建 Python 虚拟环境..."
    python3 -m venv venv
    echo "   ✅ 虚拟环境创建成功"
else
    echo "   ✅ 虚拟环境已存在"
fi

echo "   安装 Python 依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "   ✅ Python 依赖安装完成"
deactivate

cd ..

echo ""
echo "3. 设置前端环境..."
echo "----------------------------"
cd frontend

if [ ! -f ".env" ]; then
    echo "   创建 .env 配置文件..."
    cp .env.example .env
    echo "   ✅ .env 文件已创建"
else
    echo "   ✅ .env 文件已存在"
fi

if [ ! -d "node_modules" ]; then
    echo "   安装 Node.js 依赖..."
    npm install
    echo "   ✅ Node.js 依赖安装完成"
else
    echo "   ✅ node_modules 已存在，跳过安装"
    echo "   (如需重新安装，请运行: rm -rf node_modules && npm install)"
fi

cd ..

echo ""
echo "========================================"
echo "✅ 环境准备完成！"
echo "========================================"
echo ""
echo "后续步骤："
echo ""
echo "1. 配置 API 密钥："
echo "   - 编辑 backend/.env"
echo "   - 填入你的 OPENAI_API_KEY"
echo ""
echo "2. 启动 Redis (可选，用于缓存)："
echo "   redis-server"
echo ""
echo "3. 启动后端服务："
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python -m pytest  # 运行测试"
echo "   # 启动 FastAPI 服务 (待实现)"
echo ""
echo "4. 启动前端服务："
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "5. 使用 Docker (可选)："
echo "   docker-compose up -d"
echo ""
echo "更多信息请查看各模块的 README.md"
echo ""
