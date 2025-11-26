#!/usr/bin/env python3
"""
架构迁移启动脚本
自动创建新的DDD目录结构并准备迁移
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
import json

class ArchitectureMigration:
    """架构迁移管理器"""
    
    def __init__(self):
        self.base_path = Path(".")
        self.backup_path = Path("backups") / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def create_backup(self):
        """创建备份"""
        print("📦 创建备份...")
        
        # 需要备份的目录
        dirs_to_backup = ["src", "tests", "scripts"]
        
        for dir_name in dirs_to_backup:
            if (self.base_path / dir_name).exists():
                backup_dir = self.backup_path / dir_name
                shutil.copytree(
                    self.base_path / dir_name,
                    backup_dir,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc')
                )
                print(f"  ✅ 备份 {dir_name} -> {backup_dir}")
        
        # 备份重要文件
        files_to_backup = [
            "requirements.txt",
            ".env",
            "docker-compose.yml",
            "README.md"
        ]
        
        for file_name in files_to_backup:
            if (self.base_path / file_name).exists():
                backup_file = self.backup_path / file_name
                backup_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.base_path / file_name, backup_file)
                print(f"  ✅ 备份 {file_name}")
    
    def create_ddd_structure(self):
        """创建DDD目录结构"""
        print("\n🏗️ 创建DDD架构...")
        
        directories = [
            # Domain层
            "domain/entities",
            "domain/value_objects", 
            "domain/services",
            "domain/repositories",
            "domain/events",
            "domain/specifications",
            
            # Application层
            "application/commands",
            "application/queries",
            "application/dto",
            "application/services",
            "application/validators",
            
            # Infrastructure层
            "infrastructure/database/postgresql",
            "infrastructure/database/redis",
            "infrastructure/database/migrations",
            "infrastructure/messaging/rabbitmq",
            "infrastructure/monitoring",
            "infrastructure/external/telegram",
            "infrastructure/external/tron",
            "infrastructure/external/payment",
            
            # Presentation层
            "presentation/handlers/premium",
            "presentation/handlers/wallet",
            "presentation/handlers/energy",
            "presentation/handlers/admin",
            "presentation/middlewares",
            "presentation/routers",
            "presentation/validators",
            
            # Shared层
            "shared/exceptions",
            "shared/utils",
            "shared/constants",
            "shared/decorators",
            
            # Tests
            "tests/unit/domain",
            "tests/unit/application",
            "tests/integration",
            "tests/e2e",
            "tests/fixtures",
            "tests/mocks",
            
            # Documentation
            "docs/architecture",
            "docs/api",
            "docs/deployment",
            "docs/development",
            "docs/operations",
            
            # Configuration
            "config/environments",
            "config/k8s",
            "config/docker",
        ]
        
        for dir_path in directories:
            full_path = self.base_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            # 创建__init__.py
            init_file = full_path / "__init__.py"
            if not init_file.exists():
                init_file.write_text('"""\n{}\n"""\n'.format(
                    dir_path.replace('/', '.') + ' module'
                ))
            
            print(f"  ✅ 创建 {dir_path}")
    
    def create_base_files(self):
        """创建基础文件"""
        print("\n📄 创建基础文件...")
        
        # Domain实体基类
        base_entity = '''"""
领域实体基类
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid

@dataclass
class Entity:
    """实体基类"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    def __init__(self, id: Optional[str] = None):
        self.id = id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
'''
        (self.base_path / "domain/entities/base.py").write_text(base_entity)
        print("  ✅ 创建 domain/entities/base.py")
        
        # Repository接口
        repository_interface = '''"""
仓库接口定义
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Generic, TypeVar

T = TypeVar('T')

class Repository(ABC, Generic[T]):
    """仓库基础接口"""
    
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """根据ID获取"""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[T]:
        """获取所有"""
        pass
    
    @abstractmethod
    async def save(self, entity: T) -> T:
        """保存实体"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """删除实体"""
        pass
'''
        (self.base_path / "domain/repositories/base.py").write_text(repository_interface)
        print("  ✅ 创建 domain/repositories/base.py")
        
        # 应用服务基类
        app_service = '''"""
应用服务基类
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class ApplicationService:
    """应用服务基类"""
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行服务"""
        raise NotImplementedError
    
    def validate(self, **kwargs):
        """验证输入"""
        pass
'''
        (self.base_path / "application/services/base.py").write_text(app_service)
        print("  ✅ 创建 application/services/base.py")
        
    def create_docker_files(self):
        """创建Docker相关文件"""
        print("\n🐳 创建Docker配置...")
        
        # Docker Compose
        docker_compose = '''version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: tg_bot_postgres
    environment:
      POSTGRES_DB: tg_bot
      POSTGRES_USER: bot_user
      POSTGRES_PASSWORD: ${DB_PASSWORD:-password}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bot_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: tg_bot_redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  bot:
    build: .
    container_name: tg_bot
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - DATABASE_URL=postgresql+asyncpg://bot_user:${DB_PASSWORD:-password}@postgres:5432/tg_bot
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
'''
        (self.base_path / "docker-compose.prod.yml").write_text(docker_compose)
        print("  ✅ 创建 docker-compose.prod.yml")
        
        # Dockerfile
        dockerfile = '''FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    gcc \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# 运行
CMD ["python", "-m", "presentation.main"]
'''
        (self.base_path / "Dockerfile.prod").write_text(dockerfile)
        print("  ✅ 创建 Dockerfile.prod")
        
    def create_migration_plan(self):
        """创建迁移计划"""
        print("\n📋 生成迁移计划...")
        
        plan = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "phases": [
                {
                    "phase": 1,
                    "name": "准备阶段",
                    "tasks": [
                        "备份现有代码",
                        "创建新目录结构",
                        "安装新依赖"
                    ],
                    "status": "completed"
                },
                {
                    "phase": 2,
                    "name": "核心迁移",
                    "tasks": [
                        "迁移User实体",
                        "迁移Order实体",
                        "迁移Payment服务"
                    ],
                    "status": "pending"
                },
                {
                    "phase": 3,
                    "name": "基础设施",
                    "tasks": [
                        "配置PostgreSQL",
                        "配置Redis",
                        "设置监控"
                    ],
                    "status": "pending"
                },
                {
                    "phase": 4,
                    "name": "测试验证",
                    "tasks": [
                        "单元测试",
                        "集成测试",
                        "性能测试"
                    ],
                    "status": "pending"
                }
            ],
            "modules_to_migrate": {
                "src/premium": "domain/entities/premium + application/commands/premium",
                "src/wallet": "domain/entities/wallet + application/services/wallet",
                "src/energy": "domain/services/energy + infrastructure/external/energy",
                "src/database.py": "infrastructure/database/postgresql",
                "src/bot.py": "presentation/main.py"
            }
        }
        
        plan_file = self.base_path / "migration_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2, ensure_ascii=False))
        print(f"  ✅ 生成迁移计划: {plan_file}")
        
    def generate_requirements(self):
        """生成新的requirements.txt"""
        print("\n📦 更新依赖...")
        
        requirements = '''# Core
python-telegram-bot==20.7
python-dotenv==1.0.0

# Database
sqlalchemy==2.0.23
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.0
redis==5.0.1

# Web Framework
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.2
pydantic-settings==2.1.0

# Monitoring
prometheus-client==0.19.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0

# Utils
httpx==0.25.2
aiofiles==23.2.1
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
black==23.12.0
flake8==6.1.0
mypy==1.7.1
pre-commit==3.5.0

# Production
gunicorn==21.2.0
supervisor==4.2.5
'''
        (self.base_path / "requirements.prod.txt").write_text(requirements)
        print("  ✅ 创建 requirements.prod.txt")
        
    def create_makefile(self):
        """创建Makefile"""
        print("\n🔧 创建Makefile...")
        
        makefile = '''# Makefile for TG Bot

.PHONY: help install test run docker clean

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make run        - Run bot locally"
	@echo "  make docker     - Build and run with Docker"
	@echo "  make clean      - Clean cache files"

install:
	pip install -r requirements.prod.txt

test:
	pytest tests/ -v --cov=domain --cov=application

run:
	python -m presentation.main

docker:
	docker-compose -f docker-compose.prod.yml up --build

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov

migrate:
	alembic upgrade head

format:
	black .
	isort .

lint:
	flake8 .
	mypy .

security:
	bandit -r domain/ application/ infrastructure/ presentation/
	safety check
'''
        (self.base_path / "Makefile").write_text(makefile)
        print("  ✅ 创建 Makefile")
        
    def run(self):
        """执行迁移"""
        print("="*60)
        print("🚀 开始架构迁移")
        print("="*60)
        
        # 1. 创建备份
        self.create_backup()
        
        # 2. 创建DDD结构
        self.create_ddd_structure()
        
        # 3. 创建基础文件
        self.create_base_files()
        
        # 4. 创建Docker文件
        self.create_docker_files()
        
        # 5. 生成迁移计划
        self.create_migration_plan()
        
        # 6. 更新依赖
        self.generate_requirements()
        
        # 7. 创建Makefile
        self.create_makefile()
        
        print("\n"+"="*60)
        print("✅ 架构迁移准备完成！")
        print("="*60)
        
        print("\n下一步操作：")
        print("1. 查看 migration_plan.json 了解迁移计划")
        print("2. 开始迁移核心模块到新架构")
        print("3. 运行测试验证迁移结果")
        print("4. 使用 docker-compose.prod.yml 部署")
        
        print("\n快速命令：")
        print("  make install  - 安装依赖")
        print("  make test     - 运行测试")
        print("  make docker   - Docker部署")
        

if __name__ == "__main__":
    migration = ArchitectureMigration()
    migration.run()
