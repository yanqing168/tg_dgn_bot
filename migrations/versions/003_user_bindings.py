"""
添加用户绑定表
用于存储 Telegram 用户名与 user_id 的映射关系
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers
revision = '003_user_bindings'
down_revision = '002_add_trx_exchange_expires_at'
branch_labels = None
depends_on = None


def upgrade():
    """创建 user_bindings 表"""
    op.create_table(
        'user_bindings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(32), nullable=True),
        sa.Column('nickname', sa.String(255), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.now),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.now),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index('idx_user_bindings_user_id', 'user_bindings', ['user_id'], unique=True)
    op.create_index('idx_user_bindings_username', 'user_bindings', ['username'], unique=True)
    
    # 创建 premium_orders 表（专门用于 Premium 订单）
    op.create_table(
        'premium_orders',
        sa.Column('order_id', sa.String(36), nullable=False),
        sa.Column('buyer_id', sa.BigInteger(), nullable=False),
        sa.Column('recipient_id', sa.BigInteger(), nullable=True),
        sa.Column('recipient_username', sa.String(32), nullable=True),
        sa.Column('recipient_type', sa.String(10), nullable=False),  # 'self' or 'other'
        sa.Column('premium_months', sa.Integer(), nullable=False),
        sa.Column('amount_usdt', sa.Float(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='PENDING'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.now),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('tx_hash', sa.String(100), nullable=True),
        sa.Column('delivery_result', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('order_id')
    )
    
    # 创建索引
    op.create_index('idx_premium_orders_buyer_status', 'premium_orders', ['buyer_id', 'status'])
    op.create_index('idx_premium_orders_recipient', 'premium_orders', ['recipient_id'])


def downgrade():
    """回滚迁移"""
    # 删除索引
    op.drop_index('idx_premium_orders_recipient', table_name='premium_orders')
    op.drop_index('idx_premium_orders_buyer_status', table_name='premium_orders')
    op.drop_index('idx_user_bindings_username', table_name='user_bindings')
    op.drop_index('idx_user_bindings_user_id', table_name='user_bindings')
    
    # 删除表
    op.drop_table('premium_orders')
    op.drop_table('user_bindings')
