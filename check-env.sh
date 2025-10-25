#!/bin/bash

set -e

echo "🔍 检查基础运行环境..."
echo ""

HAS_ERROR=0

check_command() {
    local cmd=$1
    local name=$2
    local version_flag=$3
    local required_version=$4
    
    if command -v "$cmd" &> /dev/null; then
        version=$($cmd $version_flag 2>&1 | head -n1)
        echo "✅ $name: $version"
        return 0
    else
        echo "❌ $name: 未安装"
        if [ -n "$required_version" ]; then
            echo "   建议版本: $required_version"
        fi
        HAS_ERROR=1
        return 1
    fi
}

check_python_version() {
    if command -v python3 &> /dev/null; then
        version=$(python3 --version 2>&1 | cut -d' ' -f2)
        major=$(echo $version | cut -d'.' -f1)
        minor=$(echo $version | cut -d'.' -f2)
        
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            echo "✅ Python: $version (满足要求 >= 3.10)"
            return 0
        else
            echo "❌ Python: $version (需要 >= 3.10)"
            HAS_ERROR=1
            return 1
        fi
    else
        echo "❌ Python: 未安装 (需要 >= 3.10)"
        HAS_ERROR=1
        return 1
    fi
}

check_node_version() {
    if command -v node &> /dev/null; then
        version=$(node --version 2>&1 | cut -d'v' -f2)
        major=$(echo $version | cut -d'.' -f1)
        
        if [ "$major" -ge 18 ]; then
            echo "✅ Node.js: v$version (满足要求 >= 18)"
            return 0
        else
            echo "❌ Node.js: v$version (需要 >= 18)"
            HAS_ERROR=1
            return 1
        fi
    else
        echo "❌ Node.js: 未安装 (需要 >= 18)"
        HAS_ERROR=1
        return 1
    fi
}

echo "📦 核心依赖检查:"
check_python_version
check_node_version
check_command "npm" "npm" "--version" ">= 8.0"
check_command "git" "Git" "--version" ""

echo ""
echo "🔧 可选服务检查:"
check_command "docker" "Docker" "--version" ">= 20.10" || echo "   提示: Docker 用于本地开发环境,可选"
check_command "docker-compose" "Docker Compose" "--version" ">= 2.0" || echo "   提示: Docker Compose 用于编排服务,可选"
check_command "redis-cli" "Redis CLI" "--version" "" || echo "   提示: Redis 用于缓存,可使用 Docker 启动"
check_command "psql" "PostgreSQL" "--version" "" || echo "   提示: PostgreSQL 用于数据存储,可使用 Docker 启动"

echo ""
echo "📄 环境文件检查:"

check_env_file() {
    local file=$1
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (未找到)"
        if [ -f "$file.example" ]; then
            echo "   提示: 请复制 $file.example 到 $file 并配置"
        fi
        HAS_ERROR=1
    fi
}

check_env_file "backend/.env"
check_env_file "frontend/.env"

echo ""
echo "📚 依赖包检查:"

if [ -d "backend/venv" ] || [ -d "backend/.venv" ]; then
    echo "✅ Python 虚拟环境已创建"
else
    echo "⚠️  Python 虚拟环境未创建"
    echo "   运行: cd backend && python3 -m venv venv"
fi

if [ -d "frontend/node_modules" ]; then
    echo "✅ Frontend 依赖已安装"
else
    echo "⚠️  Frontend 依赖未安装"
    echo "   运行: cd frontend && npm install"
fi

echo ""
if [ $HAS_ERROR -eq 0 ]; then
    echo "✅ 环境检查通过!"
    exit 0
else
    echo "❌ 环境检查发现问题,请根据上述提示修复"
    echo ""
    echo "💡 快速修复建议:"
    echo "   1. 运行 ./setup.sh 自动安装依赖"
    echo "   2. 参考 README.md 中的环境配置说明"
    exit 1
fi
