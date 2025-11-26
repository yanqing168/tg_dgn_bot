#!/bin/bash
# Streamlit 管理界面启动脚本

set -e

# ============================================================================
# 环境变量加载
# ============================================================================

if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found"
fi

# ============================================================================
# 配置检查
# ============================================================================

echo "Checking configuration..."

# 检查必需的环境变量
if [ -z "$API_BASE_URL" ]; then
    echo "Error: API_BASE_URL is not set"
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo "Error: API_KEY is not set"
    exit 1
fi

echo "API Base URL: $API_BASE_URL"
echo "API Key: ${API_KEY:0:8}..."

# ============================================================================
# 安装依赖（可选）
# ============================================================================

if [ "${INSTALL_DEPS:-false}" = "true" ]; then
    echo "Installing dependencies..."
    pip install -q streamlit plotly pandas python-dotenv httpx tenacity structlog
fi

# ============================================================================
# 启动 Streamlit 应用
# ============================================================================

echo "Starting Streamlit admin interface..."

# 获取配置（默认值）
ADMIN_HOST="${ADMIN_HOST:-0.0.0.0}"
ADMIN_PORT="${ADMIN_PORT:-8501}"

# 启动 Streamlit
exec streamlit run backend/admin/app.py \
    --server.port "$ADMIN_PORT" \
    --server.address "$ADMIN_HOST" \
    --server.headless true \
    --browser.gatherUsageStats false
