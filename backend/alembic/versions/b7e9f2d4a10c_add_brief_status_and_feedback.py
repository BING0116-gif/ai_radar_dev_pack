"""add brief status, approval flag and feedback table

Revision ID: b7e9f2d4a10c
Revises: ca0d6e3b015f
Create Date: 2026-09-18 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e9f2d4a10c'
down_revision: Union[str, Sequence[str], None] = 'ca0d6e3b015f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 简报发布状态：published | pending | rejected
    op.add_column('briefs', sa.Column('status', sa.String(length=16),
                                      server_default='published', nullable=False))
    # 订阅：是否启用"生成后需人工审批再发布"
    op.add_column('subscriptions', sa.Column('require_approval', sa.Boolean(),
                                             server_default=sa.false(), nullable=False))
    # 单条新闻反馈（个性化信号）
    op.create_table(
        'feedbacks',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('item_key', sa.String(length=256), nullable=False, index=True),
        sa.Column('item_title', sa.String(length=200), nullable=False, server_default=''),
        sa.Column('verdict', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'item_key', name='uq_feedback_user_item'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('feedbacks')
    op.drop_column('subscriptions', 'require_approval')
    op.drop_column('briefs', 'status')