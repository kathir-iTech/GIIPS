"""feat: add public_attention_flag, notification grouping, referrals, report_schedules

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-30 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to existing tables
    op.add_column('incidents', sa.Column('public_attention_flag', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('notifications', sa.Column('group_id', sa.String(), nullable=True))
    op.add_column('notifications', sa.Column('group_count', sa.Integer(), nullable=False, server_default='1'))
    op.create_index(op.f('ix_notifications_group_id'), 'notifications', ['group_id'], unique=False)

    # Create new tables
    op.create_table('referrals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('referrer_user_id', sa.String(), nullable=False, index=True),
        sa.Column('referred_email', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_referrals_id'), 'referrals', ['id'], unique=False)

    op.create_table('report_schedules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('exec_user_id', sa.String(), nullable=False, index=True),
        sa.Column('report_type', sa.String(), nullable=False),
        sa.Column('frequency', sa.String(), nullable=False),
        sa.Column('last_generated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_schedules_id'), 'report_schedules', ['id'], unique=False)
    op.create_index(op.f('ix_report_schedules_exec_user_id'), 'report_schedules', ['exec_user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('report_schedules')
    op.drop_table('referrals')
    op.drop_index(op.f('ix_notifications_group_id'), table_name='notifications')
    op.drop_column('notifications', 'group_count')
    op.drop_column('notifications', 'group_id')
    op.drop_column('incidents', 'public_attention_flag')
