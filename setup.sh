#!/bin/bash

set -e

echo "🚀 开始设置智能动漫生成系统开发环境..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "$SCRIPT_DIR/check-env.sh" ]; then
    echo "❌ 找不到 check-env.sh 脚本"
    exit 1
fi

echo "📋 步骤 1/5: 检查系统依赖..."
bash "$SCRIPT_DIR/check-env.sh" || {
    echo ""
    echo "⚠️  检测到缺失的系统依赖,请先安装:"
    echo "   - Python >= 3.10: https://www.python.org/downloads/"
    echo "   - Node.js >= 18: https://nodejs.org/"
    echo "   - Git: https://git-scm.com/"
    echo ""
    read -p "是否继续设置(忽略缺失依赖)? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
}

echo ""
echo "📋 步骤 2/5: 设置后端环境..."
cd "$SCRIPT_DIR/backend"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📝 复制 .env.example 到 .env..."
        cp .env.example .env
        echo "⚠️  请编辑 backend/.env 文件,配置必要的 API keys"
    else
        echo "⚠️  未找到 .env.example 文件"
    fi
else
    echo "✅ backend/.env 已存在"
fi

if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "🐍 创建 Python 虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ Python 虚拟环境已存在"
fi

echo "📦 激活虚拟环境并安装 Python 依赖..."
source venv/bin/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null || {
    echo "❌ 无法激活虚拟环境"
    exit 1
}

pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Python 依赖安装完成"

deactivate

echo ""
echo "📋 步骤 3/5: 设置前端环境..."
cd "$SCRIPT_DIR/frontend"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📝 复制 .env.example 到 .env..."
        cp .env.example .env
    else
        echo "⚠️  未找到 .env.example 文件"
    fi
else
    echo "✅ frontend/.env 已存在"
fi

if [ ! -d "node_modules" ]; then
    echo "📦 安装 Node.js 依赖..."
    npm install
    echo "✅ Node.js 依赖安装完成"
else
    echo "✅ Node.js 依赖已存在"
fi

cd "$SCRIPT_DIR"

echo ""
echo "📋 步骤 4/5: 创建必要的目录..."
mkdir -p data/uploads
mkdir -p data/outputs
mkdir -p logs
echo "✅ 目录创建完成"

echo ""
echo "📋 步骤 5/5: 验证安装..."
echo ""
bash "$SCRIPT_DIR/check-env.sh" || {
    echo ""
    echo "⚠️  环境检查未完全通过,但基础设置已完成"
}

echo ""
echo "✅ 环境设置完成!"
echo ""
echo "📚 后续步骤:"
echo "   1. 配置环境变量:"
echo "      - 编辑 backend/.env,设置 OPENAI_API_KEY 等"
echo "      - 编辑 frontend/.env,根据需要调整 API 地址"
echo ""
echo "   2. 启动开发服务 (需要先启动依赖服务):"
echo "      - 启动 Redis (可选): docker-compose up -d redis"
echo "      - 启动 PostgreSQL (可选): docker-compose up -d postgres"
echo "      - 后端: cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo "      - 前端: cd frontend && npm run dev"
echo ""
echo "   3. 使用 Docker 一键启动 (推荐):"
echo "      docker-compose up -d"
echo ""
