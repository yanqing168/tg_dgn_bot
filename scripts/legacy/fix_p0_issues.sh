#!/bin/bash
#
# 快速修复 P0 级别问题（代码审查发现）
# 执行时间：约 1 分钟
#

set -e

echo "=================================================="
echo "  快速修复 P0 问题（代码审查 Stage 1-2）"
echo "=================================================="
echo ""

cd "$(dirname "$0")/.."

echo "[1/4] 备份原始文件..."
mkdir -p .backups
cp src/database.py .backups/database.py.bak
cp migrations/versions/001_admin_tables.py .backups/001_admin_tables.py.bak
cp backend/api/services/premium_service.py .backups/premium_service.py.bak
echo "✅ 备份完成"
echo ""

echo "[2/4] 修复 SQLAlchemy 过时 API (src/database.py)..."
# 替换 declarative_base 导入
sed -i 's/from sqlalchemy.ext.declarative import declarative_base/from sqlalchemy.orm import declarative_base/' src/database.py
echo "✅ 已更新 SQLAlchemy API"
echo ""

echo "[3/4] 修复迁移脚本字段名 (migrations/versions/001_admin_tables.py)..."
# 替换字段名 unique_amount_suffix → unique_suffix
sed -i "s/'unique_amount_suffix'/'unique_suffix'/" migrations/versions/001_admin_tables.py
echo "✅ 已修正字段名"
echo ""

echo "[4/4] 修复状态比较大小写 (backend/api/services/premium_service.py)..."
# 替换小写 pending → 大写 PENDING
sed -i 's/!= "pending"/!= "PENDING"/' backend/api/services/premium_service.py
echo "✅ 已修正状态比较"
echo ""

echo "=================================================="
echo "  修复完成！验证步骤："
echo "=================================================="
echo ""
echo "1. 运行测试验证："
echo "   pytest backend/tests/backend/ -v"
echo ""
echo "2. 检查 SQLAlchemy 警告："
echo "   pytest backend/tests/backend/test_repositories.py -v 2>&1 | grep -i warning"
echo ""
echo "3. 测试数据库迁移（可选）："
echo "   alembic upgrade head"
echo "   alembic downgrade base"
echo ""
echo "4. 如需恢复："
echo "   cp .backups/*.bak <原路径>"
echo ""
