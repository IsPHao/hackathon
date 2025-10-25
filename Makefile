.PHONY: help check setup install clean test dev build docker-up docker-down docker-logs

help:
	@echo "智能动漫生成系统 - 开发命令"
	@echo ""
	@echo "环境设置:"
	@echo "  make check       - 检查环境依赖"
	@echo "  make setup       - 自动设置开发环境"
	@echo "  make install     - 安装所有依赖"
	@echo ""
	@echo "开发命令:"
	@echo "  make dev         - 启动开发服务器(需要手动启动 Redis/PostgreSQL)"
	@echo "  make test        - 运行测试"
	@echo "  make lint        - 运行代码检查"
	@echo ""
	@echo "Docker 命令:"
	@echo "  make docker-up   - 启动所有 Docker 服务"
	@echo "  make docker-down - 停止所有 Docker 服务"
	@echo "  make docker-logs - 查看 Docker 日志"
	@echo "  make docker-ps   - 查看运行中的容器"
	@echo ""
	@echo "其他:"
	@echo "  make clean       - 清理临时文件"
	@echo "  make help        - 显示此帮助信息"

check:
	@bash check-env.sh

setup:
	@bash setup.sh

install:
	@echo "📦 安装后端依赖..."
	cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
	@echo "📦 安装前端依赖..."
	cd frontend && npm install
	@echo "✅ 依赖安装完成"

clean:
	@echo "🧹 清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf backend/.cache frontend/.cache
	rm -rf logs/*.log
	@echo "✅ 清理完成"

test:
	@echo "🧪 运行后端测试..."
	cd backend && source venv/bin/activate && pytest
	@echo "✅ 测试完成"

lint:
	@echo "🔍 运行后端代码检查..."
	cd backend && source venv/bin/activate && ruff check . || pylint src/ || echo "未安装 linter"
	@echo "🔍 运行前端代码检查..."
	cd frontend && npm run lint
	@echo "✅ 代码检查完成"

dev-backend:
	@echo "🚀 启动后端服务..."
	cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@echo "🚀 启动前端服务..."
	cd frontend && npm run dev

dev:
	@echo "⚠️  请确保已启动 Redis 和 PostgreSQL"
	@echo "   或使用 'make docker-up' 启动完整环境"
	@make -j2 dev-backend dev-frontend

build:
	@echo "🏗️  构建前端..."
	cd frontend && npm run build
	@echo "✅ 构建完成"

docker-up:
	@echo "🐳 启动 Docker 服务..."
	docker-compose up -d
	@echo "✅ Docker 服务已启动"
	@echo "   - 后端: http://localhost:8000"
	@echo "   - 前端: http://localhost:3000"
	@echo "   - PostgreSQL: localhost:5432"
	@echo "   - Redis: localhost:6379"

docker-down:
	@echo "🐳 停止 Docker 服务..."
	docker-compose down
	@echo "✅ Docker 服务已停止"

docker-logs:
	docker-compose logs -f

docker-ps:
	docker-compose ps

docker-rebuild:
	@echo "🐳 重新构建并启动 Docker 服务..."
	docker-compose up -d --build
	@echo "✅ Docker 服务已重新构建并启动"
