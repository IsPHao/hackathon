.PHONY: help setup install clean test lint backend frontend docker-up docker-down docker-logs

help:
	@echo "智能动漫生成系统 - 开发命令"
	@echo ""
	@echo "环境准备:"
	@echo "  make setup        - 初始化开发环境（首次运行）"
	@echo "  make install      - 安装所有依赖"
	@echo "  make clean        - 清理临时文件和缓存"
	@echo ""
	@echo "开发运行:"
	@echo "  make backend      - 启动后端开发服务器"
	@echo "  make frontend     - 启动前端开发服务器"
	@echo ""
	@echo "测试和检查:"
	@echo "  make test         - 运行所有测试"
	@echo "  make test-backend - 运行后端测试"
	@echo "  make lint         - 运行代码检查"
	@echo "  make lint-backend - 运行后端代码检查"
	@echo "  make lint-frontend- 运行前端代码检查"
	@echo ""
	@echo "Docker 相关:"
	@echo "  make docker-up    - 启动 Docker 服务"
	@echo "  make docker-down  - 停止 Docker 服务"
	@echo "  make docker-logs  - 查看 Docker 日志"
	@echo "  make docker-clean - 清理 Docker 资源"
	@echo ""

setup:
	@echo "初始化开发环境..."
	@chmod +x setup.sh
	@./setup.sh

install: install-backend install-frontend

install-backend:
	@echo "安装后端依赖..."
	@cd backend && python3 -m venv venv && \
		. venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r requirements.txt

install-frontend:
	@echo "安装前端依赖..."
	@cd frontend && npm install

clean:
	@echo "清理临时文件..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@cd frontend && rm -rf dist 2>/dev/null || true
	@echo "清理完成"

test: test-backend

test-backend:
	@echo "运行后端测试..."
	@cd backend && . venv/bin/activate && pytest

lint: lint-backend lint-frontend

lint-backend:
	@echo "检查后端代码..."
	@cd backend && . venv/bin/activate && python -m py_compile src/**/*.py

lint-frontend:
	@echo "检查前端代码..."
	@cd frontend && npm run lint

backend:
	@echo "启动后端服务..."
	@cd backend && . venv/bin/activate && \
		echo "⚠️  注意: 需要先实现 FastAPI 主应用" && \
		echo "示例命令: uvicorn src.main:app --reload --port 8000"

frontend:
	@echo "启动前端服务..."
	@cd frontend && npm run dev

docker-up:
	@echo "启动 Docker 服务..."
	@if [ ! -f .env ]; then \
		echo "创建 .env 文件..."; \
		cp .env.example .env; \
		echo "⚠️  请编辑 .env 文件，填入你的配置"; \
	fi
	@docker-compose up -d

docker-down:
	@echo "停止 Docker 服务..."
	@docker-compose down

docker-logs:
	@docker-compose logs -f

docker-clean:
	@echo "清理 Docker 资源..."
	@docker-compose down -v
	@docker system prune -f

redis-start:
	@echo "启动 Redis..."
	@redis-server --daemonize yes || echo "Redis 可能已在运行或未安装"

redis-stop:
	@echo "停止 Redis..."
	@redis-cli shutdown || echo "Redis 未运行"
